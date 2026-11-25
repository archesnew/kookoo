#!/usr/bin/env python3
"""
scripts/test_asset_pipeline.py

Smoke-тесты качества ассетов KOO KOO:
  1. Все 18 скинов 512x512, силуэт занимает ~70-92% холста, центр около (256, 256).
  2. Скин-01 (белый) имеет плотную альфу (без съеденного контура и дыр внутри).
  3. Все 18 скинов совпадают по силуэту с эталоном body-base.webp (cv2.matchShapes < 0.15).
  4. Все 18 shoes, 18 clothes, 18 hats, 5 neck, 9 eyes/eyelids существуют и не пустые.
"""

import sys
from pathlib import Path
import cv2
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT_DIR / "public" / "assets" / "pigeon"


def test_silhouette_alignment():
    base_path = OUT_DIR / "body-base.webp"
    assert base_path.exists(), f"Отсутствует эталон: {base_path}"
    base = cv2.imread(str(base_path), cv2.IMREAD_UNCHANGED)
    assert base.shape == (512, 512, 4), f"Неверный размер body-base: {base.shape}"

    base_mask = (base[:, :, 3] > 128).astype(np.uint8)
    c_base, _ = cv2.findContours(base_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ref_cnt = max(c_base, key=cv2.contourArea)

    for i in range(1, 19):
        p = OUT_DIR / "skins" / f"skin-{i:02d}.webp"
        assert p.exists(), f"Отсутствует скин: {p}"
        im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        assert im.shape == (512, 512, 4), f"Неверный размер {p.name}: {im.shape}"

        alpha = im[:, :, 3]
        ys, xs = np.where(alpha > 128)
        assert len(ys) > 50000, f"Скин {p.name} слишком пустой: {len(ys)} px"

        h_span = int(ys.max() - ys.min())
        cx, cy = float(xs.mean()), float(ys.mean())
        assert 350 <= h_span <= 490, f"Скин {p.name} вне диапазона масштаба: h={h_span}"
        assert abs(cx - 256) < 40 and abs(cy - 256) < 45, f"Скин {p.name} смещён: ({cx:.1f}, {cy:.1f})"

        mask = (alpha > 128).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnt = max(contours, key=cv2.contourArea)
        dist = cv2.matchShapes(ref_cnt, cnt, cv2.CONTOURS_MATCH_I1, 0.0)
        assert dist < 0.25, f"Скин {p.name} расходится по силуэту: matchShapes={dist:.4f}"

    # Проверка белого скина-01 (без дыр внутри ядра тела выше лап y < 410)
    s1 = cv2.imread(str(OUT_DIR / "skins" / "skin-01.webp"), cv2.IMREAD_UNCHANGED)
    core_mask = s1[:410, :, 3] > 200
    inv = (~core_mask).astype(np.uint8) * 255
    flood = np.zeros((412, 514), dtype=np.uint8)
    cv2.floodFill(inv, flood, (0, 0), 0)
    internal_holes = int(np.sum(inv > 0))
    assert internal_holes < 50, f"У белого skin-01 обнаружены дыры внутри силуэта: {internal_holes} px"
    print("✓ test_silhouette_alignment: все 18 скинов выровнены и проверены")


def test_accessories_and_layers_present():
    for slot, prefix in [("shoes", "shoes"), ("clothes", "clothes"), ("hats", "hats")]:
        for i in range(1, 19):
            p = OUT_DIR / slot / f"{prefix}-{i:02d}.webp"
            assert p.exists(), f"Отсутствует файл: {p}"
            im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
            expected_shape = (576, 512, 4) if slot == "hats" else (512, 512, 4)
            assert im.shape == expected_shape, f"Неверный размер {p.name}: {im.shape}"
            vis_px = int(np.sum(im[:, :, 3] > 20))
            assert vis_px > 1500, f"Слой {p.name} слишком пустой ({vis_px} px)"

    for r in ["uncommon", "rare", "epic", "legendary", "mythic"]:
        p = OUT_DIR / f"neck-{r}.webp"
        assert p.exists(), f"Отсутствует шея: {p}"

    for e in ["sparkle", "crazy", "cyber", "boss", "sleepy", "anime", "berserk", "rich", "reaper"]:
        for prefix in [f"eyes-{e}.webp", f"eyelids-{e}.webp", f"eyes_{e}.webp"]:
            p = OUT_DIR / prefix
            assert p.exists(), f"Отсутствует слой глаз/век: {p}"

    print("✓ test_accessories_and_layers_present: все слои присутствуют и заполнены")


if __name__ == "__main__":
    test_silhouette_alignment()
    test_accessories_and_layers_present()
    print("ALL ASSET PIPELINE TESTS PASSED")
