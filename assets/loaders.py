"""Asset loading helpers (sprites, textures)."""

from __future__ import annotations

import logging

import pygame

from assets.paths import (
    ENEMY_TEXTURE_FALLBACK,
    ENEMY_TEXTURE_PRIMARY,
    FIRE_SHEET_PATH,
    WORLD_TILE_TEXTURE,
)


def load_fire_variants(path: str | None = None) -> dict[str, list[pygame.Surface]]:
    """Load projectile sprite variants, provide fallback if sheet missing."""
    target_path = path or FIRE_SHEET_PATH
    try:
        sheet = pygame.image.load(str(target_path)).convert_alpha()
    except FileNotFoundError:
        logging.warning("Sprite sheet not found at %s, using fallback circles", target_path)
        fallback = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(fallback, (255, 100, 100), (16, 16), 15)
        return {
            "front_frames": [fallback.copy() for _ in range(3)],
            "trail_frames": [fallback.copy() for _ in range(4)],
            "explosion_frames": [fallback.copy() for _ in range(4)],
        }

    def grab_sprite(row: int, col: int) -> pygame.Surface:
        rect = pygame.Rect(col * 32, row * 32, 32, 32)
        sprite = sheet.subsurface(rect).copy()
        return sprite.convert_alpha()

    sprites = {
        "front_frames": [grab_sprite(1, 2), grab_sprite(1, 3), grab_sprite(1, 4)],
        "trail_frames": [grab_sprite(9, 6), grab_sprite(9, 7), grab_sprite(9, 8), grab_sprite(9, 9)],
        "explosion_frames": [grab_sprite(9, 6), grab_sprite(9, 7), grab_sprite(9, 8), grab_sprite(9, 9)],
    }
    for key, frames in sprites.items():
        sprites[key] = [frame.convert_alpha() for frame in frames]
    return sprites


def load_enemy_texture() -> pygame.Surface:
    """Load the enemy texture, falling back to placeholder when absent."""
    candidate_paths = [
        ENEMY_TEXTURE_PRIMARY,
        ENEMY_TEXTURE_FALLBACK,
    ]
    texture = None
    for path in candidate_paths:
        if path.exists():
            texture = pygame.image.load(path.as_posix()).convert_alpha()
            break
    if texture is None:
        logging.warning("Enemy texture not found, creating fallback placeholder.")
        texture = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.circle(texture, (220, 60, 60), (32, 32), 28)
    texture = pygame.transform.smoothscale(texture, (96, 96))
    texture.set_alpha(255)
    return texture


def load_world_tile_texture() -> pygame.Surface:
    """Load the floor/ceiling tile texture."""
    try:
        texture = pygame.image.load(WORLD_TILE_TEXTURE.as_posix()).convert()
    except FileNotFoundError:
        logging.warning("World tile texture missing at %s, creating procedural fallback.", WORLD_TILE_TEXTURE)
        texture = pygame.Surface((64, 64))
        texture.fill((60, 60, 70))
        pygame.draw.line(texture, (90, 90, 110), (0, 0), (63, 63), 3)
        pygame.draw.line(texture, (90, 90, 110), (0, 63), (63, 0), 3)
    return texture
