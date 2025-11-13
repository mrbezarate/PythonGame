"""HUD rendering helpers (health bar etc.)."""

from __future__ import annotations

import pygame


def draw_health_bar(surface: pygame.Surface, current: int, maximum: int) -> None:
    bar_width = 240
    bar_height = 22
    margin = 20
    ratio = max(0.0, min(1.0, current / maximum))
    outer_rect = pygame.Rect(margin, margin, bar_width, bar_height)
    inner_rect = pygame.Rect(margin + 2, margin + 2, int((bar_width - 4) * ratio), bar_height - 4)
    pygame.draw.rect(surface, (50, 50, 60), outer_rect, border_radius=6)
    pygame.draw.rect(surface, (180, 50, 60), outer_rect, 2, border_radius=6)
    pygame.draw.rect(surface, (90, 200, 90), inner_rect, border_radius=4)
