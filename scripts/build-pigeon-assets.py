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
    Гарантирует 100% чистый альфа-канал и отсечение любых паразитных пикселей шума.
    """
    resized = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    arr = np.array(resized)

    # Очистка ультра-слабых субпикселей шума
    arr[arr[:, :, 3] < 15, 3] = 0

    # Обнуляем RGB для прозрачных пикселей, чтобы WebP не интерполировал цвет фона
    arr[arr[:, :, 3] == 0, :3] = 0

    clean_img = Image.fromarray(arr, "RGBA")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    str_path = str(out_path)
    for attempt in range(5):
        try:
            clean_img.save(str_path, "WEBP", quality=95, method=4)
            break
        except Exception:
            if attempt == 4:
                raise
            import time
            time.sleep(0.15)


def build_skins_assets(bb_mask: np.ndarray):
    """
    Автоматически нарезает 3 листа skins (skins1.jpg, skins2.jpg, skins3.jpg) в сетке 2x3
    на 18 отдельных вариантов (512x512):
    - удаляет белый фон и тень на полу с чистым alpha-каналом и де-фринжингом краёв;
    - выравнивает каждый окрас по координатам эталонного базового голубя;
    - сохраняет в public/assets/pigeon/skins/skin-01.webp … skin-18.webp.
    """
    skins_dir = RAW_DIR / "skins"
    if not skins_dir.exists():
        alt_skins = Path(r"C:\Users\Chessie\Documents\KOO KOO\raw assets\skins")
        if alt_skins.exists():
            skins_dir = alt_skins

    sheet_names = ["skins1.jpg", "skins2.jpg", "skins3.jpg"]
    out_skins_dir = OUT_DIR / "skins"
    out_skins_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[4/5] Нарезка и выравнивание 18 окрасов (skins) из {skins_dir}...")
    skin_idx = 1
    for s_name in sheet_names:
        sheet_path = skins_dir / s_name
        if not sheet_path.exists():
            print(f"  ⚠ Пропуск: {s_name} не найден")
            continue
        sheet = cv2.imread(str(sheet_path))
        for idx in range(6):
            r = idx // 3
            c = idx % 3
            cell_bgr = sheet[r*896:(r+1)*896, c*800:(c+1)*800]
            cell = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2RGB)

            # Выделение силуэта птицы через внешний floodFill (не пробивает дыры в белых перьях!)
            bright_c = cell.mean(axis=2)
            diff_wb_c = cell.max(axis=2) - cell.min(axis=2)
            is_white_c = ((bright_c > 251) & (diff_wb_c < 6)).astype(np.uint8) * 255
            is_white_c[845:, :] = 255
            flood_c = np.zeros((898, 802), dtype=np.uint8)
            for pt in [(0, 0), (799, 0), (0, 895), (799, 895)]:
                cv2.floodFill(is_white_c, flood_c, pt, 128)
            cell_fg = (is_white_c != 128)
            cell_fg[850:, :] = False
            # Заливка любых внутренних отверстий и выбор главного компонента
            cell_fg = fill_mask_holes(cell_fg)
            nl_c, lab_c, st_c, _ = cv2.connectedComponentsWithStats(cell_fg.astype(np.uint8))
            if nl_c > 1:
                main_c = np.argmax(st_c[1:, cv2.CC_STAT_AREA]) + 1
                cell_fg = (lab_c == main_c)
            cell_fg_u8 = cell_fg.astype(np.uint8)

            y, x = np.where(cell_fg)
            ymin, ymax, xmin, xmax = y.min(), y.max(), x.min(), x.max()
            crop_rgb = cell[ymin:ymax, xmin:xmax]
            crop_fg = cell_fg_u8[ymin:ymax, xmin:xmax]

            # Масштабирование до высоты базового голубя (392 px)
            scale = 392.0 / (ymax - ymin)
            res_rgb = cv2.resize(crop_rgb, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
            res_fg = cv2.resize(crop_fg, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)

            # Быстрое сопоставление силуэта для идеального совпадения координат
            match_res = cv2.matchTemplate(bb_mask, res_fg, cv2.TM_CCORR_NORMED)
            _, _, _, max_loc = cv2.minMaxLoc(match_res)
            px, py = max_loc
            th, tw = res_fg.shape

            canvas_rgb = np.zeros((512, 512, 3), dtype=np.float32)
            canvas_alpha = np.zeros((512, 512), dtype=np.float32)

            canvas_rgb[py:py+th, px:px+tw] = res_rgb

            # Расчёт альфа-канала: внутри силуэта альфа = 1.0, по внешней границе мягкий антиалиасинг
            fg_bool = np.zeros((512, 512), dtype=bool)
            fg_bool[py:py+th, px:px+tw] = (res_fg > 0)

            # Отсечение тени на полу под лапами (y >= 428): оставляем только лапы/когти по контуру эталона
            y_grid_s = np.arange(512)[:, None]
            bright_s = canvas_rgb.mean(axis=-1)
            diff_wb_s = canvas_rgb.max(axis=-1) - canvas_rgb.min(axis=-1)
            bb_tight = cv2.dilate(bb_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) > 0
            is_floor_shadow = (y_grid_s >= 428) & (~bb_tight)
            is_floor_shadow |= (y_grid_s >= 428) & (diff_wb_s < 26) & (bright_s > 155) & (bb_mask == 0)
            fg_bool[is_floor_shadow] = False

            dist_out = cv2.distanceTransform(fg_bool.astype(np.uint8), cv2.DIST_L2, 3)
            dist_white = np.sqrt(np.sum((255.0 - canvas_rgb) ** 2, axis=-1))
            t_edge = np.clip((dist_white - 8.0) / (25.0 - 8.0), 0.0, 1.0)

            # Внутри ядра (dist_out > 2.5) альфа строго 1.0 даже для чисто-белых перьев!
            alpha_raw = np.where(fg_bool, np.where(dist_out > 2.5, 1.0, t_edge), 0.0)
            canvas_alpha = cv2.GaussianBlur(alpha_raw.astype(np.float32), (3, 3), 0.5)
            canvas_alpha[~fg_bool] = 0.0
            canvas_alpha[canvas_alpha < 0.08] = 0.0

            # Де-фринжинг: впечатывание истинных цветов оперения на полупрозрачные края
            inpaint_mask = ((canvas_alpha > 0) & (canvas_alpha <= 0.90)).astype(np.uint8) * 255
            inpainted = cv2.inpaint(np.clip(canvas_rgb, 0, 255).astype(np.uint8), inpaint_mask, 5, cv2.INPAINT_TELEA)

            edge = (canvas_alpha > 0) & (canvas_alpha <= 0.90)
            final_rgb = canvas_rgb.copy()
            final_rgb[edge] = inpainted[edge]

            final_alpha = (canvas_alpha * 255.0).astype(np.uint8)
            final_rgb[final_alpha == 0] = [0, 0, 0]
            final_rgb = np.clip(final_rgb, 0, 255).astype(np.uint8)

            rgba = np.dstack([final_rgb, final_alpha])
            skin_img = Image.fromarray(rgba, "RGBA")

            out_file = out_skins_dir / f"skin-{skin_idx:02d}.webp"
            save_webp(skin_img, out_file)
            # Также сохраняем дубликат прямо в OUT_DIR для обратной совместимости
            save_webp(skin_img, OUT_DIR / f"skin-{skin_idx:02d}.webp")
            if ALT_OUT_DIR.exists():
                (ALT_OUT_DIR / "skins").mkdir(parents=True, exist_ok=True)
                save_webp(skin_img, ALT_OUT_DIR / "skins" / f"skin-{skin_idx:02d}.webp")
                save_webp(skin_img, ALT_OUT_DIR / f"skin-{skin_idx:02d}.webp")
            print(f"  ✓ Скин #{skin_idx:02d}: сохранён в {out_file.name} (512x512, пикселей: {int(np.sum(final_alpha > 20))})")
            skin_idx += 1


def fill_mask_holes(mask: np.ndarray) -> np.ndarray:
    """Заполняет внутренние дыры в бинарной маске через floodFill инверсии."""
    inv = (~mask).astype(np.uint8) * 255
    h, w = mask.shape
    flood = np.zeros((h + 2, w + 2), dtype=np.uint8)
    cv2.floodFill(inv, flood, (0, 0), 0)
    return mask | (inv > 0)


def build_shoes_assets(bb_arr: np.ndarray, base_512: np.ndarray):
    """
    Автоматически нарезает 3 листа shoes (shoes1.jpg, shoes2.jpg, shoes3.jpg) в сетке 2x3
    на 18 отдельных пар обуви (512x512):
    - выравнивает кадр по голове базового голубя;
    - сохраняет полную высоту обуви (подошва до y=508, воротник до y=395);
    - убирает белый фон и тень пола без срезания белых элементов кед/подошвы (fill_mask_holes);
    - сохраняет в public/assets/pigeon/shoes/shoes-01.webp … shoes-18.webp.
    """
    shoes_dir = RAW_DIR / "shoes"
    if not shoes_dir.exists():
        alt_shoes = Path(r"C:\Users\Chessie\Documents\KOO KOO\raw assets\shoes")
        if alt_shoes.exists():
            shoes_dir = alt_shoes

    sheet_names = ["shoes1.jpg", "shoes2.jpg", "shoes3.jpg"]
    out_shoes_dir = OUT_DIR / "shoes"
    out_shoes_dir.mkdir(parents=True, exist_ok=True)

    head_ref = base_512[75:225, 200:375]
    head_ref_gray = cv2.cvtColor(head_ref, cv2.COLOR_BGR2GRAY)

    print(f"\n[5/7] Нарезка, выравнивание и изоляция 18 пар обуви (shoes) из {shoes_dir}...")
    shoe_idx = 1
    for s_name in sheet_names:
        sheet_path = shoes_dir / s_name
        if not sheet_path.exists():
            print(f"  ⚠ Пропуск: {s_name} не найден")
            continue
        sheet = cv2.imread(str(sheet_path))
        cw = sheet.shape[1] // 3
        ch = sheet.shape[0] // 2
        for idx in range(6):
            r = idx // 3
            c = idx % 3
            cell = sheet[r*ch:(r+1)*ch, c*cw:(c+1)*cw]

            # Поиск масштаба и смещения головы базового голубя
            best_val, best_s, best_loc = -1, 0.53, (0, 0)
            for s in np.linspace(0.49, 0.55, 13):
                c_res = cv2.resize(cell, (0, 0), fx=s, fy=s)
                res = cv2.matchTemplate(cv2.cvtColor(c_res, cv2.COLOR_BGR2GRAY), head_ref_gray, cv2.TM_CCOEFF_NORMED)
                _, mv, _, ml = cv2.minMaxLoc(res)
                if mv > best_val:
                    best_val, best_s, best_loc = mv, s, ml

            tx = 200 - best_loc[0]
            ty = 75 - best_loc[1]

            c_scaled = cv2.resize(cell, (0, 0), fx=best_s, fy=best_s)
            sh, sw = c_scaled.shape[:2]
            aligned = np.full((512, 512, 3), 255, dtype=np.uint8)

            x1, y1 = max(0, tx), max(0, ty)
            x2, y2 = min(512, tx + sw), min(512, ty + sh)
            sx1, sy1 = max(0, -tx), max(0, -ty)
            sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)
            aligned[y1:y2, x1:x2] = c_scaled[sy1:sy2, sx1:sx2]

            # Выделение зоны обуви с полной подошвой и воротником без дыр
            y_grid, x_grid = np.indices((512, 512))
            bright = np.mean(aligned, axis=2)
            diff_wb = np.max(aligned, axis=2) - np.min(aligned, axis=2)

            diff_base = np.max(np.abs(aligned.astype(int) - base_512.astype(int)), axis=2)
            is_base_claw = (y_grid > 410) & (base_512[:, :, 0] > 100) & (base_512[:, :, 0] - base_512[:, :, 2] > 20)

            is_shoe_cand = (diff_base > 20) | is_base_claw
            is_shoe_region = (y_grid >= 385) & (y_grid <= 508) & (x_grid >= 150) & (x_grid <= 415)

            is_bg = (bright > 245) & (diff_wb < 14)
            # Тень пола: нейтральный серый/белый градиент под подошвой (y > 445 слева или y > 460 везде)
            is_floor = ((y_grid > 445) & (diff_wb <= 16) & (bright > 170) & (diff_base < 40)) | ((y_grid > 460) & (diff_wb <= 16) & (bright > 175))

            raw_shoe = is_shoe_region & is_shoe_cand & ~is_bg & ~is_floor

            # Убираем тонкие тени пола, соединённые с внешним фоном внизу
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(raw_shoe.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
            solid = fill_mask_holes(closed > 0)

            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(solid.astype(np.uint8))
            clean_shoe = np.zeros_like(solid)
            for lbl in range(1, num_labels):
                if stats[lbl, cv2.CC_STAT_AREA] > 300:
                    clean_shoe[labels == lbl] = True

            alpha = (clean_shoe.astype(np.float32) * 255.0)
            alpha = cv2.GaussianBlur(alpha, (3, 3), 0.5)
            alpha[alpha < 25] = 0

            # Де-фринжинг краёв обуви + перевод BGR -> RGB
            aligned_rgb = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
            edge = (alpha > 0) & (alpha <= 200)
            inpaint_mask = edge.astype(np.uint8) * 255
            inpainted = cv2.inpaint(aligned_rgb, inpaint_mask, 3, cv2.INPAINT_TELEA)

            final_rgb = aligned_rgb.copy()
            final_rgb[edge] = inpainted[edge]

            final_alpha = alpha.astype(np.uint8)
            final_rgb[final_alpha == 0] = [0, 0, 0]

            rgba = np.dstack([final_rgb, final_alpha])
            shoe_img = Image.fromarray(rgba, "RGBA")

            out_file = out_shoes_dir / f"shoes-{shoe_idx:02d}.webp"
            save_webp(shoe_img, out_file)
            save_webp(shoe_img, OUT_DIR / f"shoes-{shoe_idx:02d}.webp")
            if ALT_OUT_DIR.exists():
                (ALT_OUT_DIR / "shoes").mkdir(parents=True, exist_ok=True)
                save_webp(shoe_img, ALT_OUT_DIR / "shoes" / f"shoes-{shoe_idx:02d}.webp")
                save_webp(shoe_img, ALT_OUT_DIR / f"shoes-{shoe_idx:02d}.webp")
            print(f"  ✓ Обувь #{shoe_idx:02d}: сохранена в {out_file.name} (512x512, пикселей: {int(np.sum(final_alpha > 20))})")
            shoe_idx += 1


def build_clothes_assets(base_512: np.ndarray):
    """
    Автоматически нарезает листы clothes (clothes1.jpg, clothes2.png, clothes3.png) в сетке 2x3
    на 18 отдельных нарядов одежды (512x512):
    - выравнивает кадр по голове базового голубя;
    - изолирует одежду торса и крыльев;
    - убирает белый фон, тень пола и лапы;
    - сохраняет в public/assets/pigeon/clothes/clothes-01.webp … clothes-18.webp.
    """
    clothes_dir = RAW_DIR / "clothes"
    if not clothes_dir.exists():
        alt_clothes = Path(r"C:\Users\Chessie\Documents\KOO KOO\raw assets\clothes")
        if alt_clothes.exists():
            clothes_dir = alt_clothes

    sheet_names = ["clothes1.jpg", "clothes2.png", "clothes3.png"]
    out_clothes_dir = OUT_DIR / "clothes"
    out_clothes_dir.mkdir(parents=True, exist_ok=True)

    head_ref = base_512[75:225, 200:375]
    head_ref_gray = cv2.cvtColor(head_ref, cv2.COLOR_BGR2GRAY)

    print(f"\n[6/7] Нарезка, выравнивание и изоляция 18 нарядов одежды (clothes) из {clothes_dir}...")
    cloth_idx = 1
    for s_name in sheet_names:
        sheet_path = clothes_dir / s_name
        if not sheet_path.exists():
            print(f"  ⚠ Пропуск: {s_name} не найден")
            continue
        sheet = cv2.imread(str(sheet_path))
        cw = sheet.shape[1] // 3
        ch = sheet.shape[0] // 2

        for idx in range(6):
            r = idx // 3
            c = idx % 3
            cell = sheet[r*ch:(r+1)*ch, c*cw:(c+1)*cw]

            # Поиск масштаба и смещения головы
            best_val, best_s, best_loc = -1, 0.53, (0, 0)
            scales = np.linspace(0.48, 0.56, 17) if cw > 600 else np.linspace(0.80, 1.10, 19)
            for s in scales:
                c_res = cv2.resize(cell, (0, 0), fx=s, fy=s)
                res = cv2.matchTemplate(cv2.cvtColor(c_res, cv2.COLOR_BGR2GRAY), head_ref_gray, cv2.TM_CCOEFF_NORMED)
                _, mv, _, ml = cv2.minMaxLoc(res)
                if mv > best_val:
                    best_val, best_s, best_loc = mv, s, ml

            tx = 200 - best_loc[0]
            ty = 75 - best_loc[1]

            c_scaled = cv2.resize(cell, (0, 0), fx=best_s, fy=best_s)
            sh, sw = c_scaled.shape[:2]
            aligned = np.full((512, 512, 3), 255, dtype=np.uint8)

            x1, y1 = max(0, tx), max(0, ty)
            x2, y2 = min(512, tx + sw), min(512, ty + sh)
            sx1, sy1 = max(0, -tx), max(0, -ty)
            sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)
            aligned[y1:y2, x1:x2] = c_scaled[sy1:sy2, sx1:sx2]

            bright = np.mean(aligned, axis=2)
            diff_wb = np.max(aligned, axis=2) - np.min(aligned, axis=2)

            # Внешний белый фон через floodFill из углов (не вырезает белые принты/худи внутри одежды)
            is_white_cand = (bright > 235) & (diff_wb < 18)
            inv = is_white_cand.astype(np.uint8) * 255
            flood = np.zeros((514, 514), dtype=np.uint8)
            for pt in [(0, 0), (511, 0), (0, 511), (511, 511)]:
                cv2.floodFill(inv, flood, pt, 0)
            is_exterior_bg = (inv == 0) & is_white_cand

            y_grid, x_grid = np.indices((512, 512))
            # Вычитание базового голубя (хвост слева, голая шея, лапы внизу и тень пола)
            diff_base = np.max(np.abs(aligned.astype(int) - base_512.astype(int)), axis=2)

            is_head = (y_grid < 175)
            is_floor = (y_grid >= 438)
            is_cloth_zone = (y_grid >= 170) & (y_grid <= 438) & (x_grid >= 145) & (x_grid <= 430)

            # Выделяем только пиксели одежды, отличающиеся от базового голубя
            is_garment_diff = (diff_base > 26)
            kernel_cl = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            garment_closed = cv2.morphologyEx((is_garment_diff & is_cloth_zone & ~is_exterior_bg).astype(np.uint8), cv2.MORPH_CLOSE, kernel_cl) > 0
            garment_solid = fill_mask_holes(garment_closed)

            # Строгое отсечение голого хвоста (x < 178), если там нет ткани (diff_base < 35), и оранжевых лап внизу
            is_tail_feather = (x_grid < 178) & (diff_base < 35)
            is_orange_claw = (y_grid > 395) & (aligned[:, :, 2] > 155) & (aligned[:, :, 2] - aligned[:, :, 0] > 45)
            is_leg_gap = (y_grid > 405) & (diff_base < 36)

            cloth_cand = garment_solid & is_cloth_zone & ~is_exterior_bg & ~is_head & ~is_floor & ~is_tail_feather & ~is_orange_claw & ~is_leg_gap

            num_l, labels, stats, centroids = cv2.connectedComponentsWithStats(cloth_cand.astype(np.uint8))
            clean_clothes = np.zeros_like(cloth_cand)
            if num_l > 1:
                main_lbl = np.argmax(stats[1:, cv2.CC_STAT_AREA]) + 1
                clean_clothes[labels == main_lbl] = True

            alpha = (clean_clothes.astype(np.float32) * 255.0)
            alpha = cv2.GaussianBlur(alpha, (3, 3), 0.5)
            alpha[alpha < 25] = 0

            aligned_rgb = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
            edge = (alpha > 0) & (alpha <= 200)
            inpaint_mask = edge.astype(np.uint8) * 255
            inpainted = cv2.inpaint(aligned_rgb, inpaint_mask, 3, cv2.INPAINT_TELEA)

            final_rgb = aligned_rgb.copy()
            final_rgb[edge] = inpainted[edge]

            final_alpha = alpha.astype(np.uint8)
            final_rgb[final_alpha == 0] = [0, 0, 0]

            rgba = np.dstack([final_rgb, final_alpha])
            cloth_img = Image.fromarray(rgba, "RGBA")

            out_file = out_clothes_dir / f"clothes-{cloth_idx:02d}.webp"
            save_webp(cloth_img, out_file)
            save_webp(cloth_img, OUT_DIR / f"clothes-{cloth_idx:02d}.webp")
            if ALT_OUT_DIR.exists():
                (ALT_OUT_DIR / "clothes").mkdir(parents=True, exist_ok=True)
                save_webp(cloth_img, ALT_OUT_DIR / "clothes" / f"clothes-{cloth_idx:02d}.webp")
                save_webp(cloth_img, ALT_OUT_DIR / f"clothes-{cloth_idx:02d}.webp")
            print(f"  ✓ Одежда #{cloth_idx:02d}: сохранена в {out_file.name} (512x512, пикселей: {int(np.sum(final_alpha > 20))})")
            cloth_idx += 1


def build_hats_assets(base_512: np.ndarray):
    """
    Автоматически нарезает листы hats (hats1.png, hats2.png, hats3.png) в сетке 2x3
    на 18 отдельных головных уборов (512x512):
    - выравнивает кадр по лицу базового голубя;
    - изолирует головной убор на макушке (y <= 165);
    - строго отсекает лицо/глаза/клюв (y >= 135 и x в [225, 360]), предотвращая захват лица зебры или скина;
    - убирает белый фон и тело базового голубя;
    - сохраняет в public/assets/pigeon/hats/hats-01.webp … hats-18.webp.
    """
    hats_dir = RAW_DIR / "hats"
    if not hats_dir.exists():
        alt_hats = Path(r"C:\Users\Chessie\Documents\KOO KOO\raw assets\hats")
        if alt_hats.exists():
            hats_dir = alt_hats

    sheet_names = ["hats1.png", "hats2.png", "hats3.png"]
    out_hats_dir = OUT_DIR / "hats"
    out_hats_dir.mkdir(parents=True, exist_ok=True)

    face_ref = cv2.cvtColor(base_512[130:220, 230:370], cv2.COLOR_BGR2GRAY)

    print(f"\n[7/7] Нарезка, выравнивание и изоляция 18 головных уборов (hats) из {hats_dir}...")
    hat_idx = 1
    for s_name in sheet_names:
        sheet_path = hats_dir / s_name
        if not sheet_path.exists():
            print(f"  ⚠ Пропуск: {s_name} не найден")
            continue
        sheet = cv2.imread(str(sheet_path))
        cw = sheet.shape[1] // 3
        ch = sheet.shape[0] // 2

        for idx in range(6):
            r = idx // 3
            c = idx % 3
            cell = sheet[r*ch:(r+1)*ch, c*cw:(c+1)*cw]

            # Поиск масштаба и смещения лица
            best_val, best_s, best_loc = -1, 0.81, (0, 0)
            scales = np.linspace(0.48, 0.56, 17) if cw > 600 else np.linspace(0.75, 0.90, 16)
            for s in scales:
                c_res = cv2.resize(cell, (0, 0), fx=s, fy=s)
                res = cv2.matchTemplate(cv2.cvtColor(c_res, cv2.COLOR_BGR2GRAY), face_ref, cv2.TM_CCOEFF_NORMED)
                _, mv, _, ml = cv2.minMaxLoc(res)
                if mv > best_val:
                    best_val, best_s, best_loc = mv, s, ml

            tx = 230 - best_loc[0]
            ty = 130 - best_loc[1]

            c_scaled = cv2.resize(cell, (0, 0), fx=best_s, fy=best_s)
            sh, sw = c_scaled.shape[:2]
            aligned = np.full((512, 512, 3), 255, dtype=np.uint8)

            x1, y1 = max(0, tx), max(0, ty)
            x2, y2 = min(512, tx + sw), min(512, ty + sh)
            sx1, sy1 = max(0, -tx), max(0, -ty)
            sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)
            aligned[y1:y2, x1:x2] = c_scaled[sy1:sy2, sx1:sx2]

            bright = np.mean(aligned, axis=2)
            diff_wb = np.max(aligned, axis=2) - np.min(aligned, axis=2)
            is_pure_white = (bright > 242) & (diff_wb < 16)

            y_grid, x_grid = np.indices((512, 512))
            # Строгое отсечение лица/глаз/клюва, но сохранение очков авиатора сверху (y < 132) и ушанок по бокам
            is_face = (y_grid >= 132) & (x_grid >= 210) & (x_grid <= 365)
            is_lower_back = (y_grid >= 165) & (x_grid < 180)
            is_hat_zone = (y_grid <= 215) & (x_grid >= 120) & (x_grid <= 420) & ~is_face & ~is_lower_back

            diff_base = np.max(np.abs(aligned.astype(int) - base_512.astype(int)), axis=2)
            # В зоне головы и затылка отсекаем сине-фиолетовые перья шеи/затылка эталонного голубя
            is_purple_neck = (y_grid >= 148) & (x_grid >= 175) & (x_grid <= 220) & (aligned[:, :, 0].astype(int) > aligned[:, :, 2].astype(int) + 5) & (bright < 170)
            is_neck_back = (y_grid >= 132) & (x_grid >= 175) & (x_grid <= 215) & (diff_base < 60)
            is_base = ((diff_base < 42) & (y_grid >= 88)) | is_neck_back | is_purple_neck

            hat_cand = is_hat_zone & ~is_pure_white & ~is_base
            # Убираем тонкие остаточные полоски кожи лба и крыльев
            kernel_h = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            hat_opened = cv2.morphologyEx(hat_cand.astype(np.uint8), cv2.MORPH_OPEN, kernel_h) > 0
            hat_mask = fill_mask_holes(hat_opened) & ~is_base & ~is_face & ~is_lower_back

            num_l, labels, stats, centroids = cv2.connectedComponentsWithStats(hat_mask.astype(np.uint8))
            clean_hat = np.zeros_like(hat_mask)
            if num_l > 1:
                # Берём только компоненты самой шапки (максимальный компонент + близкие детали сверху, напр. бубенцы/нимб)
                main_lbl = np.argmax(stats[1:, cv2.CC_STAT_AREA]) + 1
                for lbl in range(1, num_l):
                    area = stats[lbl, cv2.CC_STAT_AREA]
                    cx, cy = centroids[lbl]
                    if lbl == main_lbl or (area > 250 and cy < 155 and cx > 165):
                        clean_hat[labels == lbl] = True

            alpha = (clean_hat.astype(np.float32) * 255.0)
            alpha = cv2.GaussianBlur(alpha, (3, 3), 0.5)
            alpha[alpha < 25] = 0

            aligned_rgb = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
            edge = (alpha > 0) & (alpha <= 200)
            inpaint_mask = edge.astype(np.uint8) * 255
            inpainted = cv2.inpaint(aligned_rgb, inpaint_mask, 3, cv2.INPAINT_TELEA)

            final_rgb = aligned_rgb.copy()
            final_rgb[edge] = inpainted[edge]

            final_alpha = alpha.astype(np.uint8)
            final_rgb[final_alpha == 0] = [0, 0, 0]

            rgba = np.dstack([final_rgb, final_alpha])
            hat_img = Image.fromarray(rgba, "RGBA")

            out_file = out_hats_dir / f"hats-{hat_idx:02d}.webp"
            save_webp(hat_img, out_file)
            save_webp(hat_img, OUT_DIR / f"hats-{hat_idx:02d}.webp")
            if ALT_OUT_DIR.exists():
                (ALT_OUT_DIR / "hats").mkdir(parents=True, exist_ok=True)
                save_webp(hat_img, ALT_OUT_DIR / "hats" / f"hats-{hat_idx:02d}.webp")
                save_webp(hat_img, ALT_OUT_DIR / f"hats-{hat_idx:02d}.webp")
            print(f"  ✓ Шапка #{hat_idx:02d}: сохранена в {out_file.name} (512x512, пикселей: {int(np.sum(final_alpha > 20))})")
            hat_idx += 1


def main():
    force = "--force" in sys.argv
    print(f"=== Сборка ассетов персонажа KOO KOO (тело, шея, глаза, веки, 18 скинов, 18 пар обуви) ===")
    print(f"Исходники: {RAW_DIR}")
    print(f"Вывод:     {OUT_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base_path = RAW_DIR / "base.jpg"
    if not base_path.exists():
        print(f"ОШИБКА: Файл base.jpg не найден в {RAW_DIR}")
        sys.exit(1)

    base_out = OUT_DIR / "body-base.webp"
    if not base_out.exists() or force:
        print("\n[1/5] Обработка базового тела body-base.webp (отсечение тени пола + де-фринжинг)...")
        base_raw = Image.open(base_path)
        base_rgba, fg_clean = extract_base_body(base_raw)
        save_webp(base_rgba, base_out)
        print(f"  ✓ Сохранено: {base_out.name} ({TARGET_SIZE[0]}x{TARGET_SIZE[1]})")
        base_arr = np.array(base_raw.convert("RGB"), dtype=np.float32)
    else:
        print(f"\n[1/5] Базовое тело уже существует ({base_out.name}), используем готовое.")
        base_arr = np.array(Image.open(base_path).convert("RGB"), dtype=np.float32)
        fg_clean = (cv2.imread(str(base_out), cv2.IMREAD_UNCHANGED)[:, :, 3] > 0)

    # Шея
    neck_missing = any(not (OUT_DIR / dst).exists() for dst in NECK_MAPPING.values())
    if neck_missing or force:
        print("\n[2/5] Формирование цельной маски шеи и сборка 5 слоёв (neck)...")
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
    else:
        print(f"\n[2/5] Все 5 слоёв шеи уже существуют, пропуск регенерации.")

    # Глаза
    eyes_missing = any(not (OUT_DIR / dst).exists() for dst in EYES_MAPPING.values())
    if eyes_missing or force:
        print("\n[3/5] Обработка 9 слоёв глаз (eyes)...")
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
    else:
        print(f"\n[3/5] Все 9 слоёв глаз и век уже существуют, пропуск регенерации.")

    # Загружаем подготовленные слои для выравнивания скинов и обуви
    bb_arr = cv2.imread(str(OUT_DIR / "body-base.webp"), cv2.IMREAD_UNCHANGED)
    bb_mask = (bb_arr[:, :, 3] > 128).astype(np.uint8)
    base_512 = cv2.resize(cv2.imread(str(base_path)), (512, 512))

    # Сборка 18 окрасов (skins)
    build_skins_assets(bb_mask)

    # Сборка 18 пар обуви (shoes)
    build_shoes_assets(bb_arr, base_512)

    # Сборка 18 нарядов одежды (clothes)
    build_clothes_assets(base_512)

    # Сборка 18 головных уборов (hats)
    build_hats_assets(base_512)

    # Синхронизация с параллельной директорией при наличии
    if ALT_OUT_DIR.parent.parent.exists():
        try:
            ALT_OUT_DIR.mkdir(parents=True, exist_ok=True)
            for sub in ["", "skins", "shoes", "clothes", "hats"]:
                src_sub = OUT_DIR / sub
                dst_sub = ALT_OUT_DIR / sub
                dst_sub.mkdir(parents=True, exist_ok=True)
                for f in src_sub.glob("*.webp"):
                    shutil.copy2(f, dst_sub / f.name)
            print(f"\n✓ Успешно синхронизировано в {ALT_OUT_DIR} (включая skins, shoes, clothes, hats)")
        except Exception as e:
            print(f"  (Предупреждение: синхронизация в ALT_OUT_DIR не удалась: {e})")

    total_files = len(list(OUT_DIR.rglob("*.webp")))
    print(f"\nГотово! Всего сгенерировано файлов: {total_files} в {OUT_DIR}")


if __name__ == "__main__":
    main()
