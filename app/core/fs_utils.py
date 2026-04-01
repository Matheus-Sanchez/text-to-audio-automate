from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import shutil


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    normalized = re.sub(r"[-\s]+", "-", normalized)
    return normalized or "documento"


def safe_copy_to_dir(source: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / source.name
    stem = destination.stem
    suffix = destination.suffix
    counter = 1
    while destination.exists():
        destination = target_dir / f"{stem}__{counter}{suffix}"
        counter += 1
    shutil.copy2(source, destination)
    return destination


def safe_move_to_dir(source: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / source.name
    stem = destination.stem
    suffix = destination.suffix
    counter = 1
    while destination.exists():
        destination = target_dir / f"{stem}__{counter}{suffix}"
        counter += 1
    return source.replace(destination)


def copytree_atomic(source: Path, destination: Path) -> Path:
    temp_destination = destination.with_name(f"{destination.name}.tmp")
    if temp_destination.exists():
        shutil.rmtree(temp_destination)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, temp_destination)
    temp_destination.replace(destination)
    return destination
