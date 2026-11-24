#!/usr/bin/env python3
"""
scripts/build-pigeon-assets.py

Генератор послойных ассетов персонажа для Telegram Mini App KOO KOO.
Обрабатывает исходники из raw-assets/ и создаёт 15 прозрачных WebP-слоёв (512x512):
  1. public/assets/pigeon/body-base.webp
  2. public/assets/pigeon/neck-{uncommon|rare|epic|legendary|mythic}.webp (5 шт.)
  3. public/assets/pigeon/eyes-{sparkle|crazy|cyber|boss|sleepy|anime|berserk|rich|reaper}.webp (9 шт.)

Зависимости: Pillow, numpy
Запуск: py scripts/build-pigeon-assets.py
"""

import os
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
    import numpy as np
except ImportError:
    print("Необходимы библиотеки Pillow и numpy.")
    print("Установите их командой: pip install pillow numpy")
    sys.exit(1)

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "raw-assets"
OUT_DIR = ROOT_DIR / "public" / "assets" / "pigeon"

# Синхронизация с параллельной директорией KOO KOO, если она существует
ALT_OUT_DIR = Path(r"C:\Users\Chessie\Documents\KOO KOO\public\assets\pigeon")

TARGET_SIZE = (512, 512)

NECK_MAPPING = {
    "neck-green.jpg": "neck-uncommon.webp",
    "neck-blue.jpg": "neck-rare.webp",
    "neck-purple.jpg": "neck-epic.webp",
    "neck-gold.jpg": "neck-legendary.webp",
    "neck-rainbow.jpg": "neck-mythic.webp",
}

EYES_MAPPING = {
    "eyes-sparkle.jpg": "eyes-sparkle.webp",
    "eyes-crazy.jpg": "eyes-crazy.webp",
    "eyes-cyber.jpg": "eyes-cyber.webp",
    "eyes-boss.jpg": "eyes-boss.webp",
    "eyes-sleepy.jpg": "eyes-sleepy.webp",
    "eyes-anime.jpg": "eyes-anime.webp",
    "eyes-berserk.jpg": "eyes-berserk.webp",
    "eyes-rich.jpg": "eyes-rich.webp",
    "eyes-reaper.jpg": "eyes-reaper.webp",
}


def extract_base_body(base_img: Image.Image) -> tuple[Image.Image, np.ndarray]:
    """
    Удаляет внешний белый фон и остаточную наземную тень у base.jpg с де-фринжингом
    (устранением белого ореола) и мягким сглаживанием краёв без подрезки пальцев/когтей.
    Возвращает RGBA изображение и булеву маску внешнего фона.
    """
    rgb = base_img.convert("RGB")
    arr = np.array(rgb, dtype=np.float32)

    dist_from_white = np.sqrt(np.sum((255.0 - arr) ** 2, axis=-1))
    channel_diff = arr.max(axis=-1) - arr.min(axis=-1)
    bright = arr.mean(axis=-1)

    # Кандидаты на внешний фон:
    # 1. По всему кадру: пиксели близкие к чистому белому (dist < 38)
    # 2. В нижней зоне (y > 1750): нейтральная светло-серая тень под ногами
    #    (bright > 155, channel_diff < 30), не затрагивая тёмные/насыщенные когти и обувь
    is_bg_candidate = (dist_from_white < 38)
    bottom_shadow = (np.arange(arr.shape[0])[:, None] > 1750) & (bright > 155) & (channel_diff < 30)
    is_bg_candidate = is_bg_candidate | bottom_shadow

    # Заливка из 4 углов, чтобы найти внешний фон и не трогать белые элементы внутри подошв
    bg_img = Image.fromarray((is_bg_candidate.astype(np.uint8) * 255)).copy()
    for seed in [(0, 0), (0, bg_img.height - 1), (bg_img.width - 1, 0), (bg_img.width - 1, bg_img.height - 1)]:
        ImageDraw.floodfill(bg_img, seed, 128)

    outer_bg = (np.array(bg_img) == 128)
    fg_mask = Image.fromarray(((~outer_bg).astype(np.uint8) * 255))

    # Микро-эрозия (MinFilter 3) отсекает краевой 1-пиксельный JPEG-шум белого фона,
    # затем GaussianBlur(1.0) даёт плавный субпиксельный антиалиасинг
    smooth_mask = fg_mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    alpha = np.array(smooth_mask, dtype=np.float32) / 255.0
    alpha[alpha < 0.03] = 0.0

    # Математический де-фринжинг: восстанавливаем истинный цвет контура без подмешанного белого фона
    # C_obs = alpha * C_fg + (1 - alpha) * 255  ==>  C_fg = (C_obs - 255 * (1 - alpha)) / alpha
    alpha_3d = np.maximum(alpha[:, :, None], 0.05)
    fg_rgb = (arr - 255.0 * (1.0 - alpha[:, :, None])) / alpha_3d
    fg_rgb = np.clip(fg_rgb, 0.0, 255.0)

    rgba = np.dstack([fg_rgb.astype(np.uint8), (alpha * 255.0).astype(np.uint8)])
    base_rgba = Image.fromarray(rgba, "RGBA")
    return base_rgba, outer_bg


def extract_diff_layer(
    variant_img: Image.Image,
    base_arr: np.ndarray,
    outer_bg: np.ndarray,
    roi_y: tuple[int, int],
    roi_x: tuple[int, int] = (300, 1600),
    diff_threshold: float = 22.0,
) -> Image.Image:
    """
    Вычисляет diff-маску между вариантом и base.jpg, применяет порог шума,
    морфологическое сглаживание и удаление изолированных артефактов JPEG,
    оставляя только полезный слой (шея или глаза/брови).
    """
    var_rgb = variant_img.convert("RGB")
    var_arr = np.array(var_rgb, dtype=np.float32)

    # Максимальная разница по каналам
    diff = np.abs(var_arr - base_arr).max(axis=-1)

    # Ограничение по зоне интереса (ROI), чтобы отсечь краевые артефакты обуви/куртки
    roi_mask = np.zeros_like(diff, dtype=bool)
    y_start, y_end = roi_y
    x_start, x_end = roi_x
    roi_mask[y_start:y_end, x_start:x_end] = True

    # Бинарная маска изменений внутри ROI
    raw_mask = (diff > diff_threshold) & roi_mask & (~outer_bg)
    mask_img = Image.fromarray((raw_mask.astype(np.uint8) * 255))

    # Морфологическое открытие: MinFilter(3) удаляет 1-2 пиксельный шум сжатия JPEG,
    # затем MaxFilter(7) восстанавливает и слегка расширяет контур для бесшовного наложения,
    # затем GaussianBlur(1.4) даёт мягкий полупрозрачный край без лесенок.
    cleaned = (
        mask_img.filter(ImageFilter.MinFilter(3))
        .filter(ImageFilter.MaxFilter(7))
        .filter(ImageFilter.GaussianBlur(1.4))
    )

    alpha = np.array(cleaned, dtype=np.float32) / 255.0
    # Обнуляем вне ROI
    alpha[:y_start, :] = 0.0
    alpha[y_end:, :] = 0.0
    alpha[:, :x_start] = 0.0
    alpha[:, x_end:] = 0.0

    rgba = np.dstack([var_arr.astype(np.uint8), (alpha * 255.0).astype(np.uint8)])
    return Image.fromarray(rgba, "RGBA")


def save_webp(img: Image.Image, out_path: Path):
    """
    Ресайзит до целевого размера 512x512 с фильтром LANCZOS и сохраняет в WebP.
    """
    resized = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    resized.save(out_path, "WEBP", quality=92, method=6)


def main():
    print(f"=== Сборка ассетов персонажа KOO KOO ===")
    print(f"Исходники: {RAW_DIR}")
    print(f"Вывод:     {OUT_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base_path = RAW_DIR / "base.jpg"
    if not base_path.exists():
        print(f"ОШИБКА: Файл base.jpg не найден в {RAW_DIR}")
        sys.exit(1)

    print("\n[1/3] Обработка базового тела body-base.webp...")
    base_raw = Image.open(base_path)
    base_rgba, outer_bg = extract_base_body(base_raw)
    base_out = OUT_DIR / "body-base.webp"
    save_webp(base_rgba, base_out)
    print(f"  ✓ Сохранено: {base_out.name} ({TARGET_SIZE[0]}x{TARGET_SIZE[1]})")

    base_arr = np.array(base_raw.convert("RGB"), dtype=np.float32)

    print("\n[2/3] Обработка 5 слоёв шеи (neck)...")
    for src_name, dst_name in NECK_MAPPING.items():
        src_path = RAW_DIR / src_name
        if not src_path.exists():
            print(f"  ⚠ Пропуск: {src_name} не найден")
            continue
        neck_raw = Image.open(src_path)
        # Зона шеи: y ~ [450, 1250], x ~ [300, 1600]
        neck_layer = extract_diff_layer(
            neck_raw, base_arr, outer_bg, roi_y=(450, 1250), roi_x=(300, 1600), diff_threshold=20.0
        )
        dst_path = OUT_DIR / dst_name
        save_webp(neck_layer, dst_path)
        print(f"  ✓ {src_name} -> {dst_name}")

    print("\n[3/3] Обработка 9 слоёв глаз (eyes)...")
    for src_name, dst_name in EYES_MAPPING.items():
        src_path = RAW_DIR / src_name
        if not src_path.exists():
            print(f"  ⚠ Пропуск: {src_name} не найден")
            continue
        eyes_raw = Image.open(src_path)
        # Зона глаз/бровей: y ~ [250, 750], x ~ [300, 1600]
        eyes_layer = extract_diff_layer(
            eyes_raw, base_arr, outer_bg, roi_y=(250, 750), roi_x=(300, 1600), diff_threshold=20.0
        )
        dst_path = OUT_DIR / dst_name
        save_webp(eyes_layer, dst_path)
        print(f"  ✓ {src_name} -> {dst_name}")

    # Синхронизация с параллельной директорией при наличии
    if ALT_OUT_DIR.parent.parent.exists():
        try:
            ALT_OUT_DIR.mkdir(parents=True, exist_ok=True)
            for f in OUT_DIR.glob("*.webp"):
                shutil.copy2(f, ALT_OUT_DIR / f.name)
            print(f"\n✓ Успешно синхронизировано в {ALT_OUT_DIR}")
        except Exception as e:
            print(f"  (Предупреждение: синхронизация в ALT_OUT_DIR не удалась: {e})")

    total_files = len(list(OUT_DIR.glob("*.webp")))
    print(f"\nГотово! Всего сгенерировано файлов: {total_files}/15 в {OUT_DIR}")


if __name__ == "__main__":
    main()
