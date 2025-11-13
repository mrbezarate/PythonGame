"""Helpers for building the world map, wall cache, and minimap surfaces."""

from __future__ import annotations

import math
from typing import Sequence

import pygame

from config import settings
from world.generator import generate_world_map


def build_world() -> tuple[list[str], set[tuple[int, int]]]:
    """Generate the world map and the corresponding wall cache."""
    mutable_map = [list(row) for row in generate_world_map(settings.MAP_WIDTH, settings.MAP_HEIGHT)]
    center_x = settings.MAP_WIDTH // 2
    center_y = settings.MAP_HEIGHT // 2
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            x = center_x + dx
            y = center_y + dy
            if 0 <= x < settings.MAP_WIDTH and 0 <= y < settings.MAP_HEIGHT:
                mutable_map[y][x] = "0"

    world_map = ["".join(row) for row in mutable_map]
    wall_cache = {
        (x, y)
        for y, row in enumerate(world_map)
        for x, tile in enumerate(row)
        if tile == "1"
    }
    return world_map, wall_cache


def build_minimap_surfaces(world_map: Sequence[str]) -> tuple[pygame.Surface, pygame.Surface]:
    """Pre-render a high-resolution minimap texture plus overlay."""
    scale = settings.MINIMAP_TEXTURE_SCALE
    base_width = settings.MAP_WIDTH * scale
    base_height = settings.MAP_HEIGHT * scale
    minimap_base = pygame.Surface((base_width, base_height), pygame.SRCALPHA)
    wall_color = (70, 82, 102)
    accent_color = (100, 115, 140)
    for y, row in enumerate(world_map):
        for x, tile in enumerate(row):
            if tile == "1":
                color = wall_color if (x + y) % 4 else accent_color
                rect = pygame.Rect(x * scale, y * scale, scale, scale)
                minimap_base.fill(color, rect)
    minimap_overlay = pygame.Surface((settings.MINIMAP_SIZE, settings.MINIMAP_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(minimap_overlay, (0, 0, 0, 130), minimap_overlay.get_rect(), border_radius=6)
    pygame.draw.rect(minimap_overlay, (255, 255, 255, 40), minimap_overlay.get_rect(), 2, border_radius=6)
    return minimap_base, minimap_overlay
