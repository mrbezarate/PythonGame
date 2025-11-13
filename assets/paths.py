"""Utilities for locating asset files."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "materials"

FIRE_SHEET_PATH = ASSETS_DIR / "fire" / "Red Effect Bullet Impact Explosion 32x32.png"
ENEMY_TEXTURE_PRIMARY = ASSETS_DIR / "enemy" / "Enemy.png"
ENEMY_TEXTURE_FALLBACK = ASSETS_DIR / "enemy" / "Enemy.jpg"
WORLD_TILE_TEXTURE = ASSETS_DIR / "world" / "Pow.jpg"
