#!/usr/bin/env python3
"""
scripts/build-pigeon-assets.py

Генератор послойных ассетов персонажа для Telegram Mini App KOO KOO.
Обрабатывает исходники из raw-assets/ и создаёт 15 прозрачных WebP-слоёв (512x512):
  1. public/assets/pigeon/body-base.webp (базовое тело без фона с чистым просветом между ног и де-фринжингом)
  2. public/assets/pigeon/neck-{uncommon|rare|epic|legendary|mythic}.webp (5 шт., мягкий градиент наложения)
  3. public/assets/pigeon/eyes-{sparkle|crazy|cyber|boss|sleepy|anime|berserk|rich|reaper}.webp (9 шт.)

Зависимости: Pillow, numpy, opencv-python (cv2)
Запуск: py scripts/build-pigeon-assets.py
"""

import os
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
    import cv2
except ImportError as e:
    print(f"Необходимы библиотеки Pillow, numpy и opencv-python ({e}).")
    print("Установите их командой: pip install pillow numpy opencv-python")
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
    Удаляет внешний белый фон, наземную тень и белый просвет между ног,
    сохраняя все пальцы/когти, пузо, глаза и мелкие перья по бокам силуэта.
    Применяет de-fringing (устранение белого канта для тёмного фона #100919).
    Возвращает RGBA-изображение (2048x2048) и булеву маску силуэта птицы fg_clean.
    """
    rgb = base_img.convert("RGB")
    arr = np.array(rgb, dtype=np.float32)
    h, w, _ = arr.shape

    dist_from_white = np.sqrt(np.sum((255.0 - arr) ** 2, axis=-1))
    channel_diff = arr.max(axis=-1) - arr.min(axis=-1)
    bright = arr.mean(axis=-1)

    # 1. Поиск пикселей фона
    # Чистый белый фон (снаружи и в просветах)
    is_white = (dist_from_white < 12.0)

    # Наземная тень в нижней трети (y >= 1680)
    is_ground_shadow = np.zeros((h, w), dtype=bool)
    is_ground_shadow[1847:, :] = True  # ниже когтей птицы деталей нет вообще
    y_grid, x_grid = np.ogrid[:h, :w]
    # Тень слева от лап (x < 740, y >= 1680)
    is_ground_shadow |= (y_grid >= 1680) & (x_grid < 740) & (bright > 160) & (channel_diff < 22)
    # Тень справа от лап (x > 1460, y >= 1680)
    is_ground_shadow |= (y_grid >= 1680) & (x_grid > 1460) & (bright > 160) & (channel_diff < 22)
    # Тонкая тень под самыми кончиками когтей (y >= 1835)
    is_ground_shadow |= (y_grid >= 1835) & (bright > 185) & (channel_diff < 20)

    bg_candidates = is_white | is_ground_shadow
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(bg_candidates.astype(np.uint8))

    outer_bg_label = labels[0, 0]
    is_bg = (labels == outer_bg_label) | (y_grid >= 1847)

    # 2. Определение замкнутых просветов фона (в частности отверстия между ног под пузом)
    for i in range(1, num):
        if i == outer_bg_label:
            continue
        area = stats[i, cv2.CC_STAT_AREA]
        cx, cy = centroids[i]
        # Просвет между ног: y ~ [1580, 1780], x ~ [920, 1240]
        if area > 100 and 1580 < cy < 1780 and 920 < cx < 1240:
            is_bg |= (labels == i)

    # Предварительная маска птицы
    fg_binary = ~is_bg

    # Очистка изолированных мелких шумов в фоне (берём главное тело птицы)
    num_fg, labels_fg, stats_fg, centroids_fg = cv2.connectedComponentsWithStats(fg_binary.astype(np.uint8))
    main_fg_label = np.argmax(stats_fg[1:, cv2.CC_STAT_AREA]) + 1
    fg_clean = (labels_fg == main_fg_label)

    # 3. Субпиксельная альфа-маска с антиалиасингом контура (без подрезки краёв силуэта!)
    # Внутри птицы при dist_from_white >= 32.0 альфа строго 1.0 (полная непрозрачность)
    # На границе плавный переход 6.0 .. 32.0
    t = np.clip((dist_from_white - 6.0) / (32.0 - 6.0), 0.0, 1.0)
    alpha = t * t * (3.0 - 2.0 * t)
    alpha[~fg_clean] = 0.0

    # Мягкий фильтр для сглаживания субпиксельного антиалиасинга по контуру
    alpha_smooth = cv2.GaussianBlur(alpha, (3, 3), 0.75)
    alpha_smooth[~fg_clean] = 0.0

    # 4. Профессиональный de-fringing (устранение белого ореола)
    # Формула восстановления цвета без подмешанного белого фона:
    # C_unblend = (C_obs - 255 * (1 - alpha)) / alpha
    alpha_safe = np.maximum(alpha_smooth[:, :, None], 0.08)
    unblended = (arr - 255.0 * (1.0 - alpha_smooth[:, :, None])) / alpha_safe
    unblended = np.clip(unblended, 0.0, 255.0)

    # Для крайних полупрозрачных пикселей (alpha < 0.65) подмешиваем цвет соседнего
    # непрозрачного тела птицы (color inpainting), гарантируя отсутствие белых пикселей
    mask_inpaint = ((alpha_smooth > 0.0) & (alpha_smooth < 0.65)).astype(np.uint8) * 255
    inpainted = cv2.inpaint(arr.astype(np.uint8), mask_inpaint, 3, cv2.INPAINT_TELEA).astype(np.float32)

    blend_factor = np.clip((alpha_smooth[:, :, None] - 0.08) / (0.65 - 0.08), 0.0, 1.0)
    final_rgb = blend_factor * unblended + (1.0 - blend_factor) * inpainted
    final_rgb = np.clip(final_rgb, 0.0, 255.0)

    rgba = np.dstack([final_rgb.astype(np.uint8), (alpha_smooth * 255.0).astype(np.uint8)])
    base_rgba = Image.fromarray(rgba, "RGBA")
    return base_rgba, fg_clean


def extract_neck_layer(
    variant_img: Image.Image,
    base_arr: np.ndarray,
    fg_clean: np.ndarray,
) -> Image.Image:
    """
    Вычисляет маску наложения шеи с мягким растушёвыванием на границе с базовым телом.
    Устраняет ступеньки/рубленые края, сохраняя сочную фактуру цветных перьев.
    """
    var_rgb = variant_img.convert("RGB")
    var_arr = np.array(var_rgb, dtype=np.float32)

    # Максимальная разница по каналам
    diff = np.abs(var_arr - base_arr).max(axis=-1)

    # Мягкое пороговое значение:
    # diff <= 10.0 -> шум сжатия JPEG (alpha = 0)
    # diff >= 35.0 -> явное изменение цвета перьев (alpha = 1)
    diff_min, diff_max = 10.0, 35.0
    t = np.clip((diff - diff_min) / (diff_max - diff_min), 0.0, 1.0)
    smooth_diff = t * t * (3.0 - 2.0 * t)

    # Плавное пространственное окно (без резких прямоугольных срезов)
    h, w = diff.shape
    y_coords = np.arange(h)[:, None]
    x_coords = np.arange(w)[None, :]

    # Плавный переход сверху (y ~ 450..530) и снизу у куртки (y ~ 1080..1180)
    y_top = np.clip((y_coords - 450) / 80.0, 0.0, 1.0)
    y_bot = np.clip((1180 - y_coords) / 100.0, 0.0, 1.0)
    y_w = y_top * y_bot
    y_w = y_w * y_w * (3.0 - 2.0 * y_w)

    # Плавный переход слева и справа
    x_left = np.clip((x_coords - 720) / 90.0, 0.0, 1.0)
    x_right = np.clip((1500 - x_coords) / 90.0, 0.0, 1.0)
    x_w = x_left * x_right
    x_w = x_w * x_w * (3.0 - 2.0 * x_w)

    alpha_raw = smooth_diff * y_w * x_w

    # Мягкая растушёвка (Gaussian blur sigma=8.5, ядро 35x35) для идеального слияния с телом
    alpha_smooth = cv2.GaussianBlur(alpha_raw, (35, 35), 8.5)
    # Ограничиваем контуром птицы и отсекаем микро-шум
    alpha_smooth[~fg_clean] = 0.0
    alpha_smooth[alpha_smooth < 0.01] = 0.0

    rgba = np.dstack([var_arr.astype(np.uint8), (alpha_smooth * 255.0).astype(np.uint8)])
    return Image.fromarray(rgba, "RGBA")


def extract_eyes_layer(
    variant_img: Image.Image,
    base_arr: np.ndarray,
    fg_clean: np.ndarray,
) -> Image.Image:
    """
    Вычисляет маску наложения глаз/бровей с мягкими границами наложения.
    """
    var_rgb = variant_img.convert("RGB")
    var_arr = np.array(var_rgb, dtype=np.float32)

    diff = np.abs(var_arr - base_arr).max(axis=-1)

    diff_min, diff_max = 12.0, 32.0
    t = np.clip((diff - diff_min) / (diff_max - diff_min), 0.0, 1.0)
    smooth_diff = t * t * (3.0 - 2.0 * t)

    h, w = diff.shape
    y_coords = np.arange(h)[:, None]
    x_coords = np.arange(w)[None, :]

    # Зона глаз/бровей: y ~ [240, 750], x ~ [780, 1500]
    y_top = np.clip((y_coords - 240) / 60.0, 0.0, 1.0)
    y_bot = np.clip((750 - y_coords) / 60.0, 0.0, 1.0)
    y_w = y_top * y_bot
    y_w = y_w * y_w * (3.0 - 2.0 * y_w)

    x_left = np.clip((x_coords - 780) / 60.0, 0.0, 1.0)
    x_right = np.clip((1500 - x_coords) / 60.0, 0.0, 1.0)
    x_w = x_left * x_right
    x_w = x_w * x_w * (3.0 - 2.0 * x_w)

    alpha_raw = smooth_diff * y_w * x_w
    alpha_smooth = cv2.GaussianBlur(alpha_raw, (9, 9), 2.0)
    alpha_smooth[~fg_clean] = 0.0
    alpha_smooth[alpha_smooth < 0.015] = 0.0

    rgba = np.dstack([var_arr.astype(np.uint8), (alpha_smooth * 255.0).astype(np.uint8)])
    return Image.fromarray(rgba, "RGBA")


def save_webp(img: Image.Image, out_path: Path):
    """
    Ресайзит до целевого размера 512x512 с высококачественным фильтром LANCZOS и сохраняет в WebP.
    """
    resized = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    resized.save(out_path, "WEBP", quality=92, method=6)


def main():
    print(f"=== Сборка ассетов персонажа KOO KOO (улучшенный маттинг и де-фринжинг) ===")
    print(f"Исходники: {RAW_DIR}")
    print(f"Вывод:     {OUT_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base_path = RAW_DIR / "base.jpg"
    if not base_path.exists():
        print(f"ОШИБКА: Файл base.jpg не найден в {RAW_DIR}")
        sys.exit(1)

    print("\n[1/3] Обработка базового тела body-base.webp...")
    base_raw = Image.open(base_path)
    base_rgba, fg_clean = extract_base_body(base_raw)
    base_out = OUT_DIR / "body-base.webp"
    save_webp(base_rgba, base_out)
    print(f"  ✓ Сохранено: {base_out.name} ({TARGET_SIZE[0]}x{TARGET_SIZE[1]})")

    base_arr = np.array(base_raw.convert("RGB"), dtype=np.float32)

    print("\n[2/3] Обработка 5 слоёв шеи (neck) с мягким растушёвыванием...")
    for src_name, dst_name in NECK_MAPPING.items():
        src_path = RAW_DIR / src_name
        if not src_path.exists():
            print(f"  ⚠ Пропуск: {src_name} не найден")
            continue
        neck_raw = Image.open(src_path)
        neck_layer = extract_neck_layer(neck_raw, base_arr, fg_clean)
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
        eyes_layer = extract_eyes_layer(eyes_raw, base_arr, fg_clean)
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
