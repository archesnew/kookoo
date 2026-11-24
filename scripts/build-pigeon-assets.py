#!/usr/bin/env python3
"""
scripts/build-pigeon-assets.py

Генератор послойных ассетов персонажа для Telegram Mini App KOO KOO.
Обрабатывает исходники из raw-assets/ и создаёт 15 прозрачных WebP-слоёв (512x512):
  1. public/assets/pigeon/body-base.webp (базовое тело без фона, с чистым просветом между ног,
     без тени под когтями [alpha = 0] и с качественным de-fringing для тёмного фона #100919).
  2. public/assets/pigeon/neck-{uncommon|rare|epic|legendary|mythic}.webp (5 шт.,
     цельная маска шеи/оперения без проплешин и дыр, с мягким растушёвыванием по краю).
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
    Удаляет внешний белый фон, белый просвет между ног и тень на полу ниже кончиков пальцев/когтей.
    Лапы, пальцы, когти, пузо, перья и глаза сохраняются целыми без обрезания.
    Выполняет профессиональный de-fringing для отображения на тёмном фоне #100919.
    Возвращает RGBA-изображение (2048x2048) и булеву маску силуэта птицы fg_clean.
    """
    rgb = base_img.convert("RGB")
    arr = np.array(rgb, dtype=np.float32)
    h, w, _ = arr.shape

    dist_from_white = np.sqrt(np.sum((255.0 - arr) ** 2, axis=-1))
    channel_diff = arr.max(axis=-1) - arr.min(axis=-1)
    bright = arr.mean(axis=-1)

    # 1. Точное определение пикселей лап и когтей для защиты от удаления:
    # Темные кончики когтей (bright < 142) или оранжевые пальцы лап
    is_foot_pixel = (np.arange(h)[:, None] >= 1650) & (
        ((channel_diff > 22) & (arr[:, :, 0] > arr[:, :, 2] + 20)) |
        (bright < 142)
    )

    # Находим самую нижнюю точку когтя/пальца в каждой колонке x
    bottom_claw_y = np.zeros(w, dtype=int)
    for x in range(740, 1470):
        col_feet = np.where(is_foot_pixel[:, x])[0]
        if len(col_feet) > 0:
            bottom_claw_y[x] = col_feet.max()

    # 2. Формирование маски тени на полу (жестко обнуляется alpha = 0):
    is_floor_shadow = np.zeros((h, w), dtype=bool)
    # Ниже самой низкой точки когтей птицы (y >= 1847) теней и деталей нет
    is_floor_shadow[1847:, :] = True
    y_grid, x_grid = np.ogrid[:h, :w]
    # Тень слева и справа от лап (y >= 1680)
    is_floor_shadow |= (y_grid >= 1680) & ((x_grid < 750) | (x_grid > 1465))

    # Тень строго ниже кончиков когтей в каждой колонке
    for x in range(750, 1465):
        if bottom_claw_y[x] > 0:
            is_floor_shadow[bottom_claw_y[x] + 1:, x] = True
        else:
            is_floor_shadow[1680:, x] = True

    # 3. Белый фон (снаружи и в замкнутом просвете между ног)
    is_white = (dist_from_white < 12.0)
    bg_candidates = is_white | is_floor_shadow
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(bg_candidates.astype(np.uint8))

    outer_bg_label = labels[0, 0]
    is_bg = (labels == outer_bg_label) | is_floor_shadow

    # Удаляем замкнутый просвет между ног (отверстие под пузом)
    for i in range(1, num):
        if i == outer_bg_label:
            continue
        area = stats[i, cv2.CC_STAT_AREA]
        cx, cy = centroids[i]
        if area > 100 and 1580 < cy < 1780 and 920 < cx < 1240:
            is_bg |= (labels == i)

    # 4. Основной силуэт птицы (без изолированного мелкого шума)
    fg_binary = ~is_bg
    num_fg, labels_fg, stats_fg, centroids_fg = cv2.connectedComponentsWithStats(fg_binary.astype(np.uint8))
    main_fg_label = np.argmax(stats_fg[1:, cv2.CC_STAT_AREA]) + 1
    fg_clean = (labels_fg == main_fg_label)

    # 5. Вычисление альфа-канала с сохранением бережного контура птицы
    t = np.clip((dist_from_white - 6.0) / (32.0 - 6.0), 0.0, 1.0)
    alpha = t * t * (3.0 - 2.0 * t)
    alpha[~fg_clean] = 0.0
    # Жёстко обнуляем тень на полу ниже лап и когтей
    alpha[is_floor_shadow] = 0.0

    # Сглаживание субпиксельного антиалиасинга по контуру
    alpha_smooth = cv2.GaussianBlur(alpha, (3, 3), 0.75)
    alpha_smooth[~fg_clean] = 0.0
    alpha_smooth[is_floor_shadow] = 0.0

    # 6. De-fringing (устранение белого ореола для тёмного фона #100919)
    alpha_safe = np.maximum(alpha_smooth[:, :, None], 0.08)
    unblended = (arr - 255.0 * (1.0 - alpha_smooth[:, :, None])) / alpha_safe
    unblended = np.clip(unblended, 0.0, 255.0)

    # Inpaint цвета тела птицы в полупрозрачные пиксели (alpha < 0.65)
    mask_inpaint = ((alpha_smooth > 0.0) & (alpha_smooth < 0.65)).astype(np.uint8) * 255
    inpainted = cv2.inpaint(arr.astype(np.uint8), mask_inpaint, 3, cv2.INPAINT_TELEA).astype(np.float32)

    blend_factor = np.clip((alpha_smooth[:, :, None] - 0.08) / (0.65 - 0.08), 0.0, 1.0)
    final_rgb = blend_factor * unblended + (1.0 - blend_factor) * inpainted
    final_rgb = np.clip(final_rgb, 0.0, 255.0)

    rgba = np.dstack([final_rgb.astype(np.uint8), (alpha_smooth * 255.0).astype(np.uint8)])
    base_rgba = Image.fromarray(rgba, "RGBA")
    return base_rgba, fg_clean


def build_solid_neck_mask(
    all_neck_paths: list[Path],
    base_arr: np.ndarray,
    fg_clean: np.ndarray,
) -> np.ndarray:
    """
    Создаёт цельную маску шеи/оперения голубя без проплешин и дыр внутри перьев.
    Находит объединённую зону оперения шеи, морфологически заполняет внутренности
    и формирует мягкий плавный градиент (растушёвку) по границе маски.
    """
    h, w, _ = base_arr.shape
    diff_maps = []
    for p in all_neck_paths:
        if p.exists():
            n_arr = np.array(Image.open(p).convert("RGB"), dtype=np.float32)
            diff = np.abs(n_arr - base_arr).max(axis=-1)
            diff_maps.append(diff)

    if diff_maps:
        max_diff = np.maximum.reduce(diff_maps)
    else:
        max_diff = np.zeros((h, w), dtype=np.float32)

    # Зона шеи: y ~ [520, 1150], x ~ [740, 1480]
    neck_roi = (
        (np.arange(h)[:, None] >= 520) &
        (np.arange(h)[:, None] <= 1150) &
        (np.arange(w)[None, :] >= 740) &
        (np.arange(w)[None, :] <= 1480)
    )

    raw_neck_blob = (max_diff > 20) & neck_roi

    # Морфологическое закрытие (заполнение всех дыр и просветов внутри перьев)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))
    closed = cv2.morphologyEx(raw_neck_blob.astype(np.uint8), cv2.MORPH_CLOSE, kernel)

    # Находим внешний цельный контур шеи
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    solid_mask = np.zeros_like(closed, dtype=np.uint8)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        cv2.drawContours(solid_mask, [largest], -1, 1, thickness=cv2.FILLED)

    # Мягкое растушёвывание края (перо) через distanceTransform
    # Внутри ядра оперения (дистанция > 16 px) alpha = 1.0 (чистый 100% цвет исходника)
    # На границе оперения мягкий кубический спад (smoothstep) в 0.0
    dist_inside = cv2.distanceTransform(solid_mask, cv2.DIST_L2, 5)
    feather_radius = 16.0
    t = np.clip(dist_inside / feather_radius, 0.0, 1.0)
    feather = t * t * (3.0 - 2.0 * t)

    # Ограничиваем контуром птицы
    feather[~fg_clean] = 0.0
    feather[feather < 0.01] = 0.0
    return feather


def extract_neck_layer(
    variant_img: Image.Image,
    neck_mask: np.ndarray,
) -> Image.Image:
    """
    Применяет цельную маску шеи к исходнику neck-*.jpg, беря чистый цвет и фактуру перьев
    без дыр и с мягким переходом на границах наложения.
    """
    var_rgb = variant_img.convert("RGB")
    var_arr = np.array(var_rgb, dtype=np.uint8)
    alpha = (neck_mask * 255.0).astype(np.uint8)

    rgba = np.dstack([var_arr, alpha])
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
    print(f"=== Сборка ассетов персонажа KOO KOO (цельная шея, чистый пол, де-фринжинг) ===")
    print(f"Исходники: {RAW_DIR}")
    print(f"Вывод:     {OUT_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base_path = RAW_DIR / "base.jpg"
    if not base_path.exists():
        print(f"ОШИБКА: Файл base.jpg не найден в {RAW_DIR}")
        sys.exit(1)

    print("\n[1/3] Обработка базового тела body-base.webp (отсечение тени пола + де-фринжинг)...")
    base_raw = Image.open(base_path)
    base_rgba, fg_clean = extract_base_body(base_raw)
    base_out = OUT_DIR / "body-base.webp"
    save_webp(base_rgba, base_out)
    print(f"  ✓ Сохранено: {base_out.name} ({TARGET_SIZE[0]}x{TARGET_SIZE[1]})")

    base_arr = np.array(base_raw.convert("RGB"), dtype=np.float32)

    print("\n[2/3] Формирование цельной маски шеи и сборка 5 слоёв (neck)...")
    neck_paths = [RAW_DIR / name for name in NECK_MAPPING.keys()]
    neck_mask = build_solid_neck_mask(neck_paths, base_arr, fg_clean)
    print(f"  ✓ Цельная маска шеи создана: площадь покрытия {int(np.sum(neck_mask > 0.5))} пикселей")

    for src_name, dst_name in NECK_MAPPING.items():
        src_path = RAW_DIR / src_name
        if not src_path.exists():
            print(f"  ⚠ Пропуск: {src_name} не найден")
            continue
        neck_raw = Image.open(src_path)
        neck_layer = extract_neck_layer(neck_raw, neck_mask)
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
