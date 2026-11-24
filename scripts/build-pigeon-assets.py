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
    Удаляет внешний белый фон, белый просвет между ног и любую тень на полу.
    Ноги, пальцы и темные кончики когтей сохраняются целыми без обрезания.
    Выполняет профессиональный de-fringing (расширение цвета изнутри силуэта наружу),
    гарантируя полное отсутствие белых ореолов, полос и пятен на тёмном фоне #100919.
    """
    rgb = base_img.convert("RGB")
    arr = np.array(rgb, dtype=np.float32)
    h, w, _ = arr.shape

    dist_from_white = np.sqrt(np.sum((255.0 - arr) ** 2, axis=-1))

    # 1. Точное и строгое выделение ног и когтей в нижней части птицы (y >= 1650):
    # Ноги и пальцы голубя строго оранжевые: R высокое, R > B + 35, G > 30.
    y_grid, x_grid = np.ogrid[:h, :w]
    is_lower = (y_grid >= 1650)
    is_orange_toe = is_lower & (arr[:, :, 0] > 130) & (arr[:, :, 0] - arr[:, :, 2] > 35) & (arr[:, :, 1] > 30)

    # Темные кончики когтей (находятся в пределах 35 px от оранжевых пальцев):
    # Когти имеют низкую яркость (mean < 110) и темный оттенок, отличный от фона
    kernel_claws = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 35))
    dilated_orange = cv2.dilate(is_orange_toe.astype(np.uint8), kernel_claws).astype(bool)
    is_dark_claw = is_lower & dilated_orange & (arr.mean(axis=-1) < 110)

    # Истинная маска лап (только оранжевые пальцы + прилегающие темные когти)
    is_foot = is_orange_toe | is_dark_claw

    # Тень на полу: ВСЕ пиксели ниже 1650, не являющиеся лапами или когтями,
    # гарантированно отсекаются в alpha = 0! Никаких белых плашек или теней студии!
    is_floor_shadow = is_lower & (~is_foot)

    # 2. Выделение внешнего белого фона
    is_bg_candidate = (dist_from_white < 14.0) | is_floor_shadow
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(is_bg_candidate.astype(np.uint8))
    outer_bg_label = labels[0, 0]
    is_outer_bg = (labels == outer_bg_label) | is_floor_shadow

    # Очистка замкнутого просвета между ног (под брюшком)
    for i in range(1, num):
        if i == outer_bg_label:
            continue
        area = stats[i, cv2.CC_STAT_AREA]
        cx, cy = centroids[i]
        if area > 80 and 1540 < cy < 1720 and 900 < cx < 1250:
            is_outer_bg |= (labels == i)

    # 3. Чистый силуэт птицы (главный связный компонент)
    bird_fg = (~is_outer_bg) & (~is_floor_shadow)
    num_fg, labels_fg, stats_fg, _ = cv2.connectedComponentsWithStats(bird_fg.astype(np.uint8))
    main_fg_label = np.argmax(stats_fg[1:, cv2.CC_STAT_AREA]) + 1
    fg_clean = (labels_fg == main_fg_label)

    # 4. Расчет альфа-канала с мягким антиалиасингом по контуру перьев
    alpha = np.zeros((h, w), dtype=np.float32)
    # Лапы и когти solid (1.0)
    alpha[is_foot & fg_clean] = 1.0
    # Верхняя часть тела: плавный переход на антиалиасных границах
    upper = fg_clean & (~is_lower)
    t = np.clip((dist_from_white - 7.0) / (25.0 - 7.0), 0.0, 1.0)
    alpha[upper] = t[upper]

    # Сглаживание краев альфы
    alpha_smooth = cv2.GaussianBlur(alpha, (3, 3), 0.5)
    alpha_smooth[~fg_clean] = 0.0
    alpha_smooth[is_floor_shadow] = 0.0
    # Очистка ультра-слабого шума (alpha < 0.06 обнуляется)
    alpha_smooth[alpha_smooth < 0.06] = 0.0

    # 5. Истинный де-фринжинг (De-fringing) без белого ореола:
    # Ядро птицы, где альфа близка к 1.0:
    core_bird = (alpha_smooth > 0.92)
    # Маска для inpainting: расширяем истинные цвета перьев и лап птицы наружу на край,
    # чтобы полупрозрачные пиксели края имели цвет самого голубя, а не белого фона студии.
    inpaint_mask = (~core_bird).astype(np.uint8) * 255
    arr_uint8 = np.clip(arr, 0, 255).astype(np.uint8)
    inpainted = cv2.inpaint(arr_uint8, inpaint_mask, 8, cv2.INPAINT_TELEA).astype(np.float32)

    # Формируем итоговые RGB-каналы:
    # Для всех краевых пикселей (0 < alpha <= 0.92) используем цвет inpainted (чистый цвет птицы)
    final_rgb = arr.copy()
    edge_mask = (alpha_smooth > 0.0) & (alpha_smooth <= 0.92)
    final_rgb[edge_mask] = inpainted[edge_mask]

    # Ниже 1650 на лапах убираем любые белые/светло-серые блики стола:
    lower_white_fringe = is_lower & (alpha_smooth > 0.0) & (final_rgb.mean(axis=-1) > 140) & (final_rgb.max(axis=-1) - final_rgb.min(axis=-1) < 40)
    alpha_smooth[lower_white_fringe] = 0.0

    final_rgb = np.clip(final_rgb, 0.0, 255.0).astype(np.uint8)
    final_alpha = (alpha_smooth * 255.0).astype(np.uint8)
    final_rgb[final_alpha == 0] = [0, 0, 0]

    rgba = np.dstack([final_rgb, final_alpha])
    return Image.fromarray(rgba, "RGBA"), fg_clean


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


def extract_eyelids_and_pupils(eyes_img: Image.Image) -> tuple[Image.Image, Image.Image]:
    """
    Разделяет слой взгляда на веки/кожу (eyelids) и зрачки/белки (eyes) для Варианта Б (динамическое тонирование).
    - eyelids: участки кожи/век голубя (нейтральные серые тона для умножения на цвет скина).
    - eyes: белки (sclera), зрачки и световые эффекты (остаются без тонирования).
    """
    arr = np.array(eyes_img)
    vis = arr[:, :, 3] > 20
    diff = arr[:, :, :3].max(axis=-1) - arr[:, :, :3].min(axis=-1)
    means = arr[:, :, :3].mean(axis=-1)

    is_eyelid = vis & (means >= 60) & (means <= 175) & (diff < 35)
    is_eyeball = vis & (~is_eyelid)

    # Веки
    arr_lids = arr.copy()
    arr_lids[~is_eyelid, 3] = 0
    img_lids = Image.fromarray(arr_lids, "RGBA")

    # Зрачки и белки
    arr_eyes = arr.copy()
    arr_eyes[~is_eyeball, 3] = 0
    img_eyes = Image.fromarray(arr_eyes, "RGBA")

    return img_lids, img_eyes


def save_webp(img: Image.Image, out_path: Path):
    """
    Ресайзит до целевого размера 512x512 с высококачественным фильтром LANCZOS и сохраняет в WebP.
    Гарантирует 100% чистый альфа-канал и отсечение любых паразитных белых пикселей фона.
    """
    resized = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    arr = np.array(resized)

    # Очистка ультра-слабых субпикселей шума
    arr[arr[:, :, 3] < 15, 3] = 0

    # На уровне пола (нижние 20% изображения) отсекаем любые остаточные светлые нейтральные пиксели стола
    is_bottom = np.arange(TARGET_SIZE[1])[:, None] > 410
    means = arr[:, :, :3].mean(axis=-1)
    diffs = arr[:, :, :3].max(axis=-1) - arr[:, :, :3].min(axis=-1)
    bottom_table_reflection = is_bottom & (means > 140) & (diffs < 35)
    arr[bottom_table_reflection, 3] = 0

    # Обнуляем RGB для прозрачных пикселей, чтобы WebP не интерполировал цвет фона
    arr[arr[:, :, 3] == 0, :3] = 0

    clean_img = Image.fromarray(arr, "RGBA")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clean_img.save(out_path, "WEBP", quality=95, method=6)


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

        # Вариант Б: разделение на веки (eyelids) и зрачки/белки (eyes)
        eyelids_img, pupils_img = extract_eyelids_and_pupils(eyes_layer)
        trait_key = dst_name.replace("eyes-", "").replace(".webp", "")
        save_webp(eyelids_img, OUT_DIR / f"eyelids-{trait_key}.webp")
        save_webp(eyelids_img, OUT_DIR / f"eyelids_{trait_key}.webp")
        save_webp(pupils_img, OUT_DIR / f"eyes_{trait_key}.webp")
        print(f"  ✓ {src_name} -> {dst_name} + eyelids_{trait_key}.webp + eyes_{trait_key}.webp")

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
