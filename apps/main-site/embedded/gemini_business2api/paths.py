from __future__ import annotations

import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
STATIC_DIR = PACKAGE_ROOT / "static"
DOCS_DIR = PACKAGE_ROOT / "docs"
LOGO_FILE = DOCS_DIR / "logo.svg"
VERSION_FILE = PACKAGE_ROOT / "VERSION"
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data" / "gemini_business2api"


def resolve_data_dir(base_data_dir: str | os.PathLike[str] | None = None) -> Path:
    if base_data_dir:
        root = Path(base_data_dir).expanduser().resolve()
        return root / "gemini_business2api"

    env_value = str(os.getenv("GEMINI_BUSINESS2API_DATA_DIR") or "").strip()
    if env_value:
        return Path(env_value).expanduser().resolve()

    return DEFAULT_DATA_ROOT.resolve()


def ensure_data_dirs(base_data_dir: str | os.PathLike[str] | None = None) -> Path:
    data_dir = resolve_data_dir(base_data_dir)
    (data_dir / "images").mkdir(parents=True, exist_ok=True)
    (data_dir / "videos").mkdir(parents=True, exist_ok=True)
    return data_dir


def sqlite_path_for(data_dir: Path) -> Path:
    return data_dir / "data.db"
