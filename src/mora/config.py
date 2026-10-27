"""Carga de la configuración central (config/settings.yaml)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_FILE = ROOT / "config" / "settings.yaml"


@lru_cache(maxsize=1)
def settings() -> dict[str, Any]:
    with open(SETTINGS_FILE, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def path(key: str) -> Path:
    """Ruta absoluta de una carpeta definida en `paths` (la crea si no existe)."""
    p = ROOT / settings()["paths"][key]
    p.mkdir(parents=True, exist_ok=True)
    return p
