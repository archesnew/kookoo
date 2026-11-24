#!/usr/bin/env python3
"""
scripts/daily-backup.py

Скрипт локального ежедневного бэкапа проекта KOO KOO.
Создаёт архив koo-koo-backup-YYYY-MM-DD.zip в папке backups/,
исключая node_modules, dist и системный кэш, и сохраняет последние 14 копий.

Запуск: py scripts/daily-backup.py
"""

import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT_DIR / "backups"

# Папки и файлы, исключаемые из архива
EXCLUDE_DIRS = {
    "node_modules",
    "dist",
    ".git",
    ".next",
    ".nextjs_staya_backup",
    "KOO_KOO_Codex_Starter",
    "backups",
    "__pycache__",
    ".pytest_cache",
}

EXCLUDE_FILES = {
    ".DS_Store",
}


def create_daily_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    archive_name = f"koo-koo-backup-{today_str}.zip"
    archive_path = BACKUP_DIR / archive_name

    print(f"=== Создание ежедневного бэкапа KOO KOO ===")
    print(f"Корень проекта: {ROOT_DIR}")
    print(f"Целевой архив: {archive_path}")

    file_count = 0
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ROOT_DIR):
            rel_root = Path(root).relative_to(ROOT_DIR)

            # Фильтруем директории на месте
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]

            # Проверяем, не находимся ли мы внутри исключённого пути
            if any(part in EXCLUDE_DIRS for part in rel_root.parts):
                continue

            for file in files:
                if file in EXCLUDE_FILES or file.endswith(".pyc") or file.endswith(".tsbuildinfo"):
                    continue

                file_path = Path(root) / file
                arcname = str(rel_root / file) if str(rel_root) != "." else file
                zf.write(file_path, arcname)
                file_count += 1

    archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"✓ Архив успешно создан: {archive_name}")
    print(f"  Файлов заархивировано: {file_count}")
    print(f"  Размер архива: {archive_size_mb:.2f} МБ")

    # Ротация: оставляем последние 14 бэкапов
    backups = sorted(BACKUP_DIR.glob("koo-koo-backup-*.zip"), key=lambda p: p.stat().st_mtime)
    if len(backups) > 14:
        for old in backups[:-14]:
            print(f"  Удаление старого бэкапа: {old.name}")
            old.unlink()

    print("Готово!")


if __name__ == "__main__":
    create_daily_backup()
