"""Load per-person avatar images as base64 data URIs.

Avatars live in footballwatcher/assets/avatars/<Person>.png. Embedding them as
data URIs keeps the generated dashboard a single self-contained file (works over
file:// and on GitHub Pages with no separate asset hosting).
"""

from __future__ import annotations

import base64
from pathlib import Path

AVATAR_DIR = Path(__file__).resolve().parent / "assets" / "avatars"


def load_avatar_uris(avatar_dir: Path | None = None) -> dict[str, str]:
    """person name -> 'data:image/png;base64,...' for every avatar on disk."""
    directory = avatar_dir or AVATAR_DIR
    uris: dict[str, str] = {}
    if not directory.exists():
        return uris
    for png in sorted(directory.glob("*.png")):
        data = base64.b64encode(png.read_bytes()).decode("ascii")
        uris[png.stem] = f"data:image/png;base64,{data}"
    return uris
