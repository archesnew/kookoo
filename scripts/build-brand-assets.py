#!/usr/bin/env python3
"""
scripts/build-brand-assets.py

Генератор брендовых ассетов KOO KOO из references/splash.png:
  1. public/assets/brand/logo-koo-koo.webp — фирменный логотип (3 золотых семечка + KOO KOO) на прозрачном фоне
  2. public/assets/brand/seed-trio.webp — три семечка над логотипом на прозрачном фоне
  3. public/assets/brand/seed-icon.webp — одиночное золотое семечко для иконок и спиннера
  4. public/assets/brand/splash-poster.webp — оптимизированный сплэш-арт загрузочного экрана

Запуск: py scripts/build-brand-assets.py
"""

import shutil
import sys
from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
SPLASH_PATH = ROOT_DIR / "references" / "splash.png"
OUT_DIR = ROOT_DIR / "public" / "assets" / "brand"
ALT_OUT_DIR = Path(r"C:\Users\Chessie\Documents\KOO KOO\public\assets\brand")


def main():
    if not SPLASH_PATH.exists():
        print(f"ОШИБКА: Файл {SPLASH_PATH} не найден!")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"=== Сборка брендовых ассетов KOO KOO ===")
    print(f"Исходник: {SPLASH_PATH}")
    print(f"Вывод:    {OUT_DIR}")

    im = Image.open(SPLASH_PATH).convert("RGB")
    arr = np.array(im, dtype=np.float32)

    # Базовый цвет фона в районе логотипа (#0c0516)
    bg_color = np.array([12.0, 5.0, 22.0], dtype=np.float32)

    # ─────────────────────────────────────────────────────────────
    # 1. Логотип KOO KOO с тремя золотыми семечками (на прозрачном фоне)
    # y: [1010, 1195], x: [115, 825]
    # ─────────────────────────────────────────────────────────────
    logo_crop = arr[1010:1195, 115:825].copy()

    # Очищаем фиолетовые боковые полосы слева и справа от трёх семечек в верхней части (y < 55)
    for y in range(55):
        for x in range(logo_crop.shape[1]):
            if x < 285 or x > 425:
                logo_crop[y, x] = bg_color

    diff = np.maximum(logo_crop - bg_color, 0.0)
    diff_bright = 0.299 * diff[:, :, 0] + 0.587 * diff[:, :, 1] + 0.114 * diff[:, :, 2]
    alpha = np.clip((diff_bright - 10.0) / (180.0 - 10.0), 0.0, 1.0)

    # Плавное сглаживание краёв альфа-канала
    alpha_img = Image.fromarray((alpha * 255.0).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    alpha = np.array(alpha_img, dtype=np.float32) / 255.0
    alpha[alpha < 0.04] = 0.0

    # Размешивание (unblend) фонового цвета
    alpha_3d = np.maximum(alpha[:, :, None], 0.05)
    fg = (logo_crop - bg_color * (1.0 - alpha[:, :, None])) / alpha_3d
    fg = np.clip(fg, 0.0, 255.0)

    logo_rgba = np.dstack([fg.astype(np.uint8), (alpha * 255.0).astype(np.uint8)])
    logo_pil = Image.fromarray(logo_rgba, "RGBA")

    # Авто-обрезка пустых прозрачных полей
    bbox = logo_pil.getbbox()
    if bbox:
        logo_pil = logo_pil.crop(bbox)

    logo_out = OUT_DIR / "logo-koo-koo.webp"
    logo_pil.save(logo_out, "WEBP", quality=95, method=6)
    print(f"  ✓ {logo_out.name}: {logo_pil.size} (RGBA, прозрачный фон)")

    # ─────────────────────────────────────────────────────────────
    # 2. Три золотых семечка (seed-trio.webp)
    # y: [1010, 1060], x: [425, 520]
    # ─────────────────────────────────────────────────────────────
    trio_crop = arr[1010:1062, 424:522].copy()
    diff_trio = np.maximum(trio_crop - bg_color, 0.0)
    bright_trio = 0.299 * diff_trio[:, :, 0] + 0.587 * diff_trio[:, :, 1] + 0.114 * diff_trio[:, :, 2]
    alpha_trio = np.clip((bright_trio - 10.0) / (180.0 - 10.0), 0.0, 1.0)
    alpha_trio[alpha_trio < 0.05] = 0.0

    alpha_trio_3d = np.maximum(alpha_trio[:, :, None], 0.05)
    fg_trio = (trio_crop - bg_color * (1.0 - alpha_trio[:, :, None])) / alpha_trio_3d
    fg_trio = np.clip(fg_trio, 0.0, 255.0)

    trio_rgba = np.dstack([fg_trio.astype(np.uint8), (alpha_trio * 255.0).astype(np.uint8)])
    trio_pil = Image.fromarray(trio_rgba, "RGBA")
    bbox_trio = trio_pil.getbbox()
    if bbox_trio:
        trio_pil = trio_pil.crop(bbox_trio)

    trio_out = OUT_DIR / "seed-trio.webp"
    trio_pil.save(trio_out, "WEBP", quality=95, method=6)
    print(f"  ✓ {trio_out.name}: {trio_pil.size} (RGBA)")

    # ─────────────────────────────────────────────────────────────
    # 3. Одиночное золотое семечко (seed-icon.webp) из центра спиннера
    # y: [1412, 1472], x: [445, 505]
    # ─────────────────────────────────────────────────────────────
    seed_crop = arr[1412:1472, 445:505].copy()
    diff_seed = np.maximum(seed_crop - bg_color, 0.0)
    bright_seed = 0.299 * diff_seed[:, :, 0] + 0.587 * diff_seed[:, :, 1] + 0.114 * diff_seed[:, :, 2]
    alpha_seed = np.clip((bright_seed - 10.0) / (180.0 - 10.0), 0.0, 1.0)
    alpha_seed[alpha_seed < 0.05] = 0.0

    alpha_seed_3d = np.maximum(alpha_seed[:, :, None], 0.05)
    fg_seed = (seed_crop - bg_color * (1.0 - alpha_seed[:, :, None])) / alpha_seed_3d
    fg_seed = np.clip(fg_seed, 0.0, 255.0)

    seed_rgba = np.dstack([fg_seed.astype(np.uint8), (alpha_seed * 255.0).astype(np.uint8)])
    seed_pil = Image.fromarray(seed_rgba, "RGBA")
    bbox_seed = seed_pil.getbbox()
    if bbox_seed:
        seed_pil = seed_pil.crop(bbox_seed)

    # Ресайз до квадратной аккуратной иконки 64x64
    seed_square = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    offset = ((64 - seed_pil.width) // 2, (64 - seed_pil.height) // 2)
    seed_square.paste(seed_pil, offset)

    seed_out = OUT_DIR / "seed-icon.webp"
    seed_square.save(seed_out, "WEBP", quality=95, method=6)
    print(f"  ✓ {seed_out.name}: {seed_square.size} (RGBA)")

    # ─────────────────────────────────────────────────────────────
    # 4. Сплэш-постер (splash-poster.webp)
    # ─────────────────────────────────────────────────────────────
    # Ресайзим сплэш до 720x1280 для быстрой мобильной загрузки
    splash_resized = im.resize((720, 1280), Image.Resampling.LANCZOS)
    poster_out = OUT_DIR / "splash-poster.webp"
    splash_resized.save(poster_out, "WEBP", quality=88, method=6)
    size_kb = poster_out.stat().st_size / 1024
    print(f"  ✓ {poster_out.name}: {splash_resized.size} ({size_kb:.1f} КБ)")

    # Синхронизация с альтернативной директорией при наличии
    if ALT_OUT_DIR.parent.parent.exists():
        try:
            ALT_OUT_DIR.mkdir(parents=True, exist_ok=True)
            for f in OUT_DIR.glob("*.webp"):
                shutil.copy2(f, ALT_OUT_DIR / f.name)
            print(f"✓ Синхронизировано в {ALT_OUT_DIR}")
        except Exception as e:
            print(f"  (Предупреждение: синхронизация в ALT_OUT_DIR не удалась: {e})")

    print("\nСборка брендовых ассетов успешно завершена!")


if __name__ == "__main__":
    main()
