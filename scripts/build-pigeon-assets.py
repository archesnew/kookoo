#!/usr/bin/env python3
"""
scripts/build-pigeon-assets.py

Единый пайплайн генерации и субпиксельного выравнивания ассетов персонажа KOO KOO (512x512):
  1. Сегментация фона через rembg (isnet-general-use) — без порогов, floodFill и fill_mask_holes.
  2. Единый эталон: body-base.webp (512x512, силуэт ~85% холста, центр в (256, 256)).
  3. Субпиксельное выравнивание всех слоёв (skins, shoes, clothes, hats, neck, eyes, eyelids)
     через cv2.findTransformECC (cv2.MOTION_AFFINE) по альфа-силуэту эталона.
  4. Выделение шеи (neck) и глаз (eyes/eyelids) через connectedComponents без жёсткого ROI.

Зависимости: rembg, onnxruntime, pillow, numpy, opencv-python
Запуск: python scripts/build-pigeon-assets.py [--force]
"""

import sys
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
    import cv2
    from rembg import remove, new_session
except ImportError as e:
    print(f"Необходимы библиотеки rembg, onnxruntime, pillow, numpy и opencv-python ({e}).")
    print("Установите их командой: pip install -r requirements.txt")
    sys.exit(1)

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "raw-assets"
OUT_DIR = ROOT_DIR / "public" / "assets" / "pigeon"

TARGET_SIZE = (512, 512)
REMBG_MODEL = "isnet-general-use"

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


def save_rgba_webp(rgba: np.ndarray, out_path: Path):
    """Сохраняет 512x512 RGBA массив в WebP без порчи матовой альфы от rembg."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")
    if img.size != TARGET_SIZE:
        img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    img.save(str(out_path), "WEBP", quality=95, method=4)


def segment_subject(rgb_img: np.ndarray, session) -> np.ndarray:
    """Сегментирует объект через rembg и возвращает RGBA uint8 с сохранением мягкой альфы."""
    pil_in = Image.fromarray(rgb_img, "RGB")
    pil_out = remove(pil_in, session=session)
    return np.array(pil_out, dtype=np.uint8)


def compute_base_warp_and_reference(base_rgb: np.ndarray, session) -> tuple[np.ndarray, np.ndarray]:
    """
    Сегментирует base.jpg через rembg, нормирует силуэт так, чтобы он занимал ~85% холста (435 px),
    а центр bbox находился в (256, 256).
    Возвращает:
      - ref_rgba: эталон 512x512 RGBA uint8
      - M_base: аффинная матрица 2x3 (для WARP_INVERSE_MAP из base_rgb в 512x512)
    """
    seg_rgba = segment_subject(base_rgb, session)
    alpha = seg_rgba[:, :, 3]
    ys, xs = np.where(alpha > 128)
    ymin, ymax = int(ys.min()), int(ys.max())
    xmin, xmax = int(xs.min()), int(xs.max())

    h_box = max(1, ymax - ymin)
    w_box = max(1, xmax - xmin)
    target_span = 435.0  # ~85% от 512
    scale = target_span / max(h_box, w_box)

    cx_src = (xmin + xmax) / 2.0
    cy_src = (ymin + ymax) / 2.0
    cx_dst, cy_dst = 256.0, 256.0

    inv_s = 1.0 / scale
    M_base = np.array([
        [inv_s, 0.0, cx_src - inv_s * cx_dst],
        [0.0, inv_s, cy_src - inv_s * cy_dst],
    ], dtype=np.float32)

    ref_rgba = cv2.warpAffine(
        seg_rgba,
        M_base,
        TARGET_SIZE,
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    return ref_rgba, M_base


def align_to_reference_ecc(
    src_rgba: np.ndarray,
    ref_alpha: np.ndarray,
    mask_mode: str = "full",
) -> np.ndarray:
    """
    Выравнивает src_rgba под эталон ref_alpha (512x512) через cv2.findTransformECC (MOTION_AFFINE).
    mask_mode:
      - "full": по всему силуэту (для skins)
      - "upper": по голове и верху тела (для shoes)
      - "lower_body": по нижней части тела y=190..430 (для hats, чтобы высокие шляпы не сбивали масштаб)
      - "head_and_feet": по голове и лапам (для clothes)
    """
    src_alpha = src_rgba[:, :, 3].astype(np.float32) / 255.0

    ys_ref, xs_ref = np.where(ref_alpha > 0.5)
    ys_src, xs_src = np.where(src_alpha > 0.5)
    if len(ys_src) == 0 or len(ys_ref) == 0:
        return cv2.resize(src_rgba, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)

    if mask_mode == "lower_body":
        # Игнорируем верхнюю шапку при оценке масштаба и центра
        y_ref_cut = int(ys_ref.min() + (ys_ref.max() - ys_ref.min()) * 0.35)
        y_src_cut = int(ys_src.min() + (ys_src.max() - ys_src.min()) * 0.35)
        m_ref = (ref_alpha > 0.5) & (np.arange(TARGET_SIZE[1])[:, None] >= y_ref_cut)
        m_src = (src_alpha > 0.5) & (np.arange(src_alpha.shape[0])[:, None] >= y_src_cut)
        yr, xr = np.where(m_ref)
        ys, xs = np.where(m_src)
        h_ref = max(1, int(yr.max() - yr.min()))
        h_src = max(1, int(ys.max() - ys.min()))
        scale_init = h_ref / h_src
        cx_ref, cy_ref = float(xr.mean()), float(yr.mean())
        cx_src, cy_src = float(xs.mean()), float(ys.mean())
    else:
        h_ref = max(1, int(ys_ref.max() - ys_ref.min()))
        h_src = max(1, int(ys_src.max() - ys_src.min()))
        scale_init = h_ref / h_src
        cx_ref, cy_ref = float(xs_ref.mean()), float(ys_ref.mean())
        cx_src, cy_src = float(xs_src.mean()), float(ys_src.mean())

    inv_s = 1.0 / scale_init
    M = np.array([
        [inv_s, 0.0, cx_src - inv_s * cx_ref],
        [0.0, inv_s, cy_src - inv_s * cy_ref],
    ], dtype=np.float32)

    tmpl = cv2.GaussianBlur(ref_alpha, (7, 7), 1.5)
    inp = cv2.GaussianBlur(src_alpha, (7, 7), 1.5)

    input_mask = None
    if mask_mode == "upper":
        input_mask = np.zeros(TARGET_SIZE, dtype=np.uint8)
        input_mask[45:370, :] = 255
    elif mask_mode == "lower_body":
        input_mask = np.zeros(TARGET_SIZE, dtype=np.uint8)
        input_mask[190:440, :] = 255
    elif mask_mode == "head_and_feet":
        input_mask = np.zeros(TARGET_SIZE, dtype=np.uint8)
        input_mask[45:175, :] = 255
        input_mask[415:485, :] = 255

    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 120, 1e-5)
    try:
        _, M_ecc = cv2.findTransformECC(
            tmpl,
            inp,
            M.copy(),
            cv2.MOTION_AFFINE,
            criteria,
            inputMask=input_mask,
        )
        det = M_ecc[0, 0] * M_ecc[1, 1] - M_ecc[0, 1] * M_ecc[1, 0]
        if det > 0.1 and abs(M_ecc[0, 1]) < 0.35 and abs(M_ecc[1, 0]) < 0.35:
            M = M_ecc
    except cv2.error:
        pass

    aligned = cv2.warpAffine(
        src_rgba,
        M,
        TARGET_SIZE,
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    return aligned


def build_solid_neck_mask(
    necks_512: list[np.ndarray],
    base_512: np.ndarray,
    ref_alpha: np.ndarray,
) -> np.ndarray:
    """
    Выделяет цельную маску шеи без жёстких ROI-координат:
    использует max_diff всех вариантов шеи относительно base_512 и связный компонент,
    пересекающийся с эталонным силуэтом в области шеи.
    """
    diff_maps = [np.abs(n.astype(np.float32) - base_512.astype(np.float32)).max(axis=-1) for n in necks_512]
    max_diff = np.maximum.reduce(diff_maps) if diff_maps else np.zeros(TARGET_SIZE, dtype=np.float32)

    fg_mask = ref_alpha > 0.5
    raw_blob = (max_diff > 20.0) & fg_mask

    # Морфологическое закрытие внутри перьев шеи
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    closed = cv2.morphologyEx(raw_blob.astype(np.uint8), cv2.MORPH_CLOSE, kernel)

    num_l, labels, stats, _ = cv2.connectedComponentsWithStats(closed)
    solid_mask = np.zeros_like(closed, dtype=np.uint8)
    if num_l > 1:
        # Главный связный компонент, пересекающийся с зоной силуэта
        best_lbl = 0
        best_area = 0
        for lbl in range(1, num_l):
            area = int(stats[lbl, cv2.CC_STAT_AREA])
            if area > best_area and np.any((labels == lbl) & fg_mask):
                best_area = area
                best_lbl = lbl
        if best_lbl > 0:
            contours, _ = cv2.findContours((labels == best_lbl).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                cv2.drawContours(solid_mask, [max(contours, key=cv2.contourArea)], -1, 1, thickness=cv2.FILLED)

    dist_inside = cv2.distanceTransform(solid_mask, cv2.DIST_L2, 5)
    t = np.clip(dist_inside / 5.0, 0.0, 1.0)
    feather = t * t * (3.0 - 2.0 * t)
    feather *= ref_alpha
    return feather


def extract_eyes_and_lids(
    eye_512: np.ndarray,
    base_512: np.ndarray,
    ref_alpha: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Выделяет слой глаз/бровей без жёстких ROI-координат через connectedComponents
    и разделяет его на веки (grayscale для тонирования) и зрачки/белки.
    """
    diff = np.abs(eye_512.astype(np.float32) - base_512.astype(np.float32)).max(axis=-1)
    fg_mask = ref_alpha > 0.5

    # Выделяем компоненты отличий на верхней половине силуэта (голова/глаза)
    ys_fg, _ = np.where(fg_mask)
    y_head_limit = int(ys_fg.min() + (ys_fg.max() - ys_fg.min()) * 0.48) if len(ys_fg) else 256
    cand = (diff > 14.0) & fg_mask
    num_l, labels, stats, centroids = cv2.connectedComponentsWithStats(cand.astype(np.uint8))

    eye_region_mask = np.zeros(TARGET_SIZE, dtype=np.float32)
    for lbl in range(1, num_l):
        area = stats[lbl, cv2.CC_STAT_AREA]
        cy = centroids[lbl][1]
        if area >= 25 and cy <= y_head_limit:
            eye_region_mask[labels == lbl] = 1.0

    t = np.clip((diff - 12.0) / 20.0, 0.0, 1.0)
    smooth_diff = t * t * (3.0 - 2.0 * t)
    region_dilated = cv2.dilate(eye_region_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    alpha = cv2.GaussianBlur(smooth_diff * region_dilated, (5, 5), 1.0) * ref_alpha

    alpha_u8 = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    full_eyes_rgba = np.dstack([eye_512, alpha_u8])

    # Разделение на веки (grayscale для тонирования) и зрачки/белки
    vis = alpha_u8 > 20
    ch_diff = eye_512.max(axis=-1).astype(int) - eye_512.min(axis=-1).astype(int)
    means = eye_512.mean(axis=-1)
    is_eyelid = vis & (means >= 55) & (means <= 180) & (ch_diff < 38)
    is_eyeball = vis & (~is_eyelid)

    lids_rgba = np.zeros_like(full_eyes_rgba)
    gray_lids = cv2.cvtColor(eye_512, cv2.COLOR_RGB2GRAY)
    lids_rgba[:, :, 0] = gray_lids
    lids_rgba[:, :, 1] = gray_lids
    lids_rgba[:, :, 2] = gray_lids
    lids_rgba[:, :, 3] = np.where(is_eyelid, alpha_u8, 0)

    pupils_rgba = full_eyes_rgba.copy()
    pupils_rgba[~is_eyeball, 3] = 0

    return full_eyes_rgba, lids_rgba, pupils_rgba


def iter_sheet_cells(sheet_path: Path):
    """Разрезает лист 2x3 на 6 RGB-ячеек."""
    sheet_bgr = cv2.imread(str(sheet_path))
    if sheet_bgr is None:
        return
    sheet_rgb = cv2.cvtColor(sheet_bgr, cv2.COLOR_BGR2RGB)
    h, w, _ = sheet_rgb.shape
    ch, cw = h // 2, w // 3
    for idx in range(6):
        r, c = idx // 3, idx % 3
        yield sheet_rgb[r * ch : (r + 1) * ch, c * cw : (c + 1) * cw]


def build_skins_assets(ref_rgba: np.ndarray, session):
    """Сегментирует 18 скинов через rembg и выравнивает под эталон через findTransformECC."""
    skins_dir = RAW_DIR / "skins"
    out_skins_dir = OUT_DIR / "skins"
    out_skins_dir.mkdir(parents=True, exist_ok=True)
    ref_alpha = ref_rgba[:, :, 3].astype(np.float32) / 255.0

    print(f"\n[4/7] Сегментация (rembg) и ECC-выравнивание 18 окрасов из {skins_dir}...")
    skin_idx = 1
    for s_name in ["skins1.jpg", "skins2.jpg", "skins3.jpg"]:
        sheet_path = skins_dir / s_name
        if not sheet_path.exists():
            print(f"  ⚠ Пропуск: {s_name} не найден")
            continue
        for cell_rgb in iter_sheet_cells(sheet_path):
            seg_rgba = segment_subject(cell_rgb, session)
            # Сохраняем исходный RGB (чтобы на узорных белых полосах, напр. зебра #07, не терялся цвет внутри ядра)
            seg_with_rgb = np.dstack([cell_rgb, seg_rgba[:, :, 3]])
            aligned_rgba = align_to_reference_ecc(seg_with_rgb, ref_alpha, mask_mode="full")
            # Внутри плотного ядра эталона (ref_alpha > 0.88) не должно быть прозрачных дыр от rembg
            core_fill = (ref_alpha > 0.88) & (aligned_rgba[:, :, 3] < 240)
            if np.any(core_fill):
                aligned_rgba[core_fill, 3] = 255
            out_file = out_skins_dir / f"skin-{skin_idx:02d}.webp"
            save_rgba_webp(aligned_rgba, out_file)
            px = int(np.sum(aligned_rgba[:, :, 3] > 20))
            print(f"  ✓ Скин #{skin_idx:02d}: {out_file.name} (пикселей: {px})")
            skin_idx += 1


def extract_accessory_diff(
    aligned_rgba: np.ndarray,
    ref_rgba: np.ndarray,
    slot: str,
) -> np.ndarray:
    """
    Изолирует аксессуар (shoes / clothes / hats) после rembg + ECC без жёстких прямоугольных срезов:
    закрывает внутренние совпадения цвета внутри предмета (MORPH_CLOSE), оставляя главный
    связный силуэт предмета гардероба с сохранением мягкой альфы rembg.
    """
    out = aligned_rgba.copy()
    alpha_src = aligned_rgba[:, :, 3]
    ref_alpha = ref_rgba[:, :, 3].astype(np.float32) / 255.0
    ref_body = ref_alpha > 0.5
    diff = np.abs(aligned_rgba[:, :, :3].astype(np.float32) - ref_rgba[:, :, :3].astype(np.float32)).max(axis=-1)

    ys_ref, xs_ref = np.where(ref_body)
    y_min_ref, y_max_ref = int(ys_ref.min()), int(ys_ref.max())
    h_ref = y_max_ref - y_min_ref
    y_grid, x_grid = np.indices(TARGET_SIZE)

    if slot == "shoes":
        # Оставляем зону обуви внизу и убираем мелкие обрывки лодыжек выше ботинок
        y_top_limit = y_min_ref + int(h_ref * 0.72)
        cand = (alpha_src > 40) & (y_grid >= y_top_limit) & ((~ref_body) | (diff > 24.0) | (y_grid >= y_min_ref + int(h_ref * 0.82)))
        num_l, labels, stats, centroids = cv2.connectedComponentsWithStats(cand.astype(np.uint8))
        keep = np.zeros_like(cand)
        for lbl in range(1, num_l):
            if stats[lbl, cv2.CC_STAT_AREA] > 250 and centroids[lbl][1] > y_min_ref + int(h_ref * 0.76):
                keep[labels == lbl] = True
        keep = cv2.dilate(keep.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) > 0
        out[~keep, 3] = 0

    elif slot == "clothes":
        # Изолируем ткань: отсекаем сине-серый хвост слева, сине-серую шею над воротником, голову и лапы,
        # затем закрываем совпадения цвета внутри самой одежды.
        y_head_end = y_min_ref + int(h_ref * 0.25)
        y_feet_start = y_min_ref + int(h_ref * 0.86)
        w_ref = int(xs_ref.max() - xs_ref.min())
        x_min_ref = int(xs_ref.min())
        rgb_c = aligned_rgba[:, :, :3].astype(int)
        is_gray_feather = (rgb_c[:, :, 2] >= rgb_c[:, :, 0] - 8) & (rgb_c.mean(axis=-1) < 190)
        is_tail = (x_grid < int(x_min_ref + w_ref * 0.23)) & is_gray_feather
        is_neck = (y_grid < y_min_ref + int(h_ref * 0.36)) & (x_grid > x_min_ref + int(w_ref * 0.30)) & (x_grid < x_min_ref + int(w_ref * 0.78)) & is_gray_feather & (diff < 75.0)
        raw_diff = (alpha_src > 40) & ((~ref_body) | (diff > 28.0)) & (y_grid >= y_head_end) & (y_grid <= y_feet_start) & (~is_tail) & (~is_neck)
        opened = cv2.morphologyEx(raw_diff.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))) > 0
        closed[is_tail | is_neck] = False
        num_l, labels, stats, _ = cv2.connectedComponentsWithStats(closed.astype(np.uint8))
        keep = np.zeros_like(closed)
        if num_l > 1:
            main_lbl = np.argmax(stats[1:, cv2.CC_STAT_AREA]) + 1
            keep[labels == main_lbl] = True
        keep_soft = cv2.GaussianBlur(keep.astype(np.float32), (3, 3), 0.7)
        new_alpha = np.minimum(alpha_src.astype(np.float32), keep_soft * 255.0)
        out[:, :, 3] = np.clip(new_alpha, 0, 255).astype(np.uint8)

    elif slot == "hats":
        # Изолируем головной убор сверху: мягко убираем эллиптическую область лица (глаза/клюв), без прямых углов
        y_hat_max = y_min_ref + int(h_ref * 0.36)
        cy_face = y_min_ref + int(h_ref * 0.24)
        cx_face = int(xs_ref.mean() + (xs_ref.max() - xs_ref.min()) * 0.14)
        rx_face = max(1, int((xs_ref.max() - xs_ref.min()) * 0.24))
        ry_face = max(1, int(h_ref * 0.10))
        is_face_ellipse = (((x_grid - cx_face) / rx_face) ** 2 + ((y_grid - cy_face) / ry_face) ** 2) <= 1.0
        is_face_area = ref_body & is_face_ellipse
        is_head_skin = ref_body & (diff < 45.0) & (y_grid >= y_min_ref + int(h_ref * 0.05))
        raw_hat = (alpha_src > 40) & (y_grid <= y_hat_max) & ((~ref_body) | (diff > 32.0)) & (~is_face_area) & (~is_head_skin)
        opened = cv2.morphologyEx(raw_hat.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) > 0
        closed[is_face_area] = False
        num_l, labels, stats, centroids = cv2.connectedComponentsWithStats(closed.astype(np.uint8))
        keep = np.zeros_like(closed)
        if num_l > 1:
            main_lbl = np.argmax(stats[1:, cv2.CC_STAT_AREA]) + 1
            for lbl in range(1, num_l):
                if lbl == main_lbl or (stats[lbl, cv2.CC_STAT_AREA] > 200 and centroids[lbl][1] < y_min_ref + int(h_ref * 0.28)):
                    keep[labels == lbl] = True
        keep_soft = cv2.GaussianBlur(keep.astype(np.float32), (3, 3), 0.7)
        new_alpha = np.minimum(alpha_src.astype(np.float32), keep_soft * 255.0)
        out[:, :, 3] = np.clip(new_alpha, 0, 255).astype(np.uint8)

    return out


def build_accessories_assets(
    slot: str,
    sheet_names: list[str],
    ref_rgba: np.ndarray,
    session,
    step_label: str,
):
    """Универсальный конвейер rembg + ECC + вычитание базового силуэта для shoes, clothes, hats."""
    src_dir = RAW_DIR / slot
    out_slot_dir = OUT_DIR / slot
    out_slot_dir.mkdir(parents=True, exist_ok=True)
    ref_alpha = ref_rgba[:, :, 3].astype(np.float32) / 255.0

    mode_map = {"shoes": "upper", "clothes": "head_and_feet", "hats": "lower_body"}
    mask_mode = mode_map.get(slot, "upper")

    print(f"\n{step_label} Сегментация (rembg) и ECC-выравнивание ({mask_mode}) {slot} из {src_dir}...")
    item_idx = 1
    for s_name in sheet_names:
        sheet_path = src_dir / s_name
        if not sheet_path.exists():
            print(f"  ⚠ Пропуск: {s_name} не найден")
            continue
        for cell_rgb in iter_sheet_cells(sheet_path):
            seg_rgba = segment_subject(cell_rgb, session)
            aligned_rgba = align_to_reference_ecc(seg_rgba, ref_alpha, mask_mode=mask_mode)
            isolated_rgba = extract_accessory_diff(aligned_rgba, ref_rgba, slot)
            out_file = out_slot_dir / f"{slot}-{item_idx:02d}.webp"
            save_rgba_webp(isolated_rgba, out_file)
            px = int(np.sum(isolated_rgba[:, :, 3] > 20))
            print(f"  ✓ {slot} #{item_idx:02d}: {out_file.name} (пикселей: {px})")
            item_idx += 1


def main():
    force = "--force" in sys.argv
    print("=== Сборка ассетов KOO KOO (rembg + ECC MOTION_AFFINE, единый эталон 512x512) ===")
    print(f"Исходники: {RAW_DIR}")
    print(f"Вывод:     {OUT_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base_path = RAW_DIR / "base.jpg"
    if not base_path.exists():
        print(f"ОШИБКА: Файл base.jpg не найден в {RAW_DIR}")
        sys.exit(1)

    session = new_session(REMBG_MODEL)
    base_rgb = np.array(Image.open(base_path).convert("RGB"))
    base_out = OUT_DIR / "body-base.webp"

    # 1. Эталон body-base.webp (512x512) + матрица M_base
    if not base_out.exists() or force:
        print("\n[1/7] Создание эталона body-base.webp (rembg + нормирование ~85%, центр (256, 256))...")
        ref_rgba, M_base = compute_base_warp_and_reference(base_rgb, session)
        save_rgba_webp(ref_rgba, base_out)
        print(f"  ✓ Сохранено: {base_out.name}")
    else:
        print(f"\n[1/7] Эталон уже существует ({base_out.name}), выравниваем M_base под него.")
        ref_rgba = cv2.cvtColor(cv2.imread(str(base_out), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
        seg_base = segment_subject(base_rgb, session)
        ref_alpha_tmp = ref_rgba[:, :, 3].astype(np.float32) / 255.0
        # Находим матрицу для base_rgb, чтобы шея и глаза точно ложились на существующий body-base.webp
        _, M_base = compute_base_warp_and_reference(base_rgb, session)
        # Если существующий body-base.webp имеет другие пропорции, уточняем ECC:
        ys_ref, xs_ref = np.where(ref_alpha_tmp > 0.5)
        ys_src, xs_src = np.where(seg_base[:, :, 3] > 128)
        if len(ys_ref) > 0 and len(ys_src) > 0:
            inv_s = (ys_src.max() - ys_src.min()) / max(1, (ys_ref.max() - ys_ref.min()))
            M_init = np.array([
                [inv_s, 0.0, xs_src.mean() - inv_s * xs_ref.mean()],
                [0.0, inv_s, ys_src.mean() - inv_s * ys_ref.mean()],
            ], dtype=np.float32)
            try:
                _, M_base = cv2.findTransformECC(
                    cv2.GaussianBlur(ref_alpha_tmp, (7, 7), 1.5),
                    cv2.GaussianBlur(seg_base[:, :, 3].astype(np.float32) / 255.0, (7, 7), 1.5),
                    M_init,
                    cv2.MOTION_AFFINE,
                    (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5),
                )
            except cv2.error:
                M_base = M_init

    ref_alpha = ref_rgba[:, :, 3].astype(np.float32) / 255.0
    base_512 = cv2.warpAffine(
        base_rgb,
        M_base,
        TARGET_SIZE,
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )

    # 2. Шея (без жёсткого ROI)
    neck_missing = any(not (OUT_DIR / dst).exists() for dst in NECK_MAPPING.values())
    if neck_missing or force:
        print("\n[2/7] Сборка 5 слоёв шеи (без жёсткого ROI)...")
        necks_512 = []
        valid_necks = []
        for src_name, dst_name in NECK_MAPPING.items():
            src_path = RAW_DIR / src_name
            if not src_path.exists():
                print(f"  ⚠ Пропуск: {src_name} не найден")
                continue
            n_rgb = np.array(Image.open(src_path).convert("RGB"))
            n_512 = cv2.warpAffine(n_rgb, M_base, TARGET_SIZE, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
            necks_512.append(n_512)
            valid_necks.append((dst_name, n_512))

        neck_mask = build_solid_neck_mask(necks_512, base_512, ref_alpha)
        print(f"  ✓ Цельная маска шеи: {int(np.sum(neck_mask > 0.5))} px")
        for dst_name, n_512 in valid_necks:
            alpha_u8 = np.clip(neck_mask * 255.0, 0, 255).astype(np.uint8)
            save_rgba_webp(np.dstack([n_512, alpha_u8]), OUT_DIR / dst_name)
            print(f"  ✓ {dst_name}")
    else:
        print("\n[2/7] Все 5 слоёв шеи существуют, пропуск.")

    # 3. Глаза и веки (без жёсткого ROI)
    eyes_missing = any(not (OUT_DIR / dst).exists() for dst in EYES_MAPPING.values())
    if eyes_missing or force:
        print("\n[3/7] Сборка 9 слоёв глаз и век (без жёсткого ROI)...")
        for src_name, dst_name in EYES_MAPPING.items():
            src_path = RAW_DIR / src_name
            if not src_path.exists():
                print(f"  ⚠ Пропуск: {src_name} не найден")
                continue
            e_rgb = np.array(Image.open(src_path).convert("RGB"))
            e_512 = cv2.warpAffine(e_rgb, M_base, TARGET_SIZE, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
            full_eyes, lids_rgba, pupils_rgba = extract_eyes_and_lids(e_512, base_512, ref_alpha)

            trait_key = dst_name.replace("eyes-", "").replace(".webp", "")
            save_rgba_webp(full_eyes, OUT_DIR / dst_name)
            save_rgba_webp(lids_rgba, OUT_DIR / f"eyelids-{trait_key}.webp")
            save_rgba_webp(lids_rgba, OUT_DIR / f"eyelids_{trait_key}.webp")
            save_rgba_webp(pupils_rgba, OUT_DIR / f"eyes_{trait_key}.webp")
            print(f"  ✓ {dst_name} + eyelids_{trait_key}.webp + eyes_{trait_key}.webp")
    else:
        print("\n[3/7] Все 9 слоёв глаз и век существуют, пропуск.")

    # 4. 18 скинов
    build_skins_assets(ref_rgba, session)

    # 5–7. Обувь, одежда, головные уборы
    build_accessories_assets("shoes", ["shoes1.jpg", "shoes2.jpg", "shoes3.jpg"], ref_rgba, session, "[5/7]")
    build_accessories_assets("clothes", ["clothes1.jpg", "clothes2.png", "clothes3.png"], ref_rgba, session, "[6/7]")
    build_accessories_assets("hats", ["hats1.png", "hats2.png", "hats3.png"], ref_rgba, session, "[7/7]")

    total_files = len(list(OUT_DIR.rglob("*.webp")))
    print(f"\nГотово! Всего WebP файлов в {OUT_DIR}: {total_files}")


if __name__ == "__main__":
    main()
