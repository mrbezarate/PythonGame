"""UI helpers for menu, crosshair, and slider widgets."""

from __future__ import annotations

from typing import Tuple

import pygame

from config import settings


def set_menu_state(open_state: bool) -> bool:
    pygame.mouse.set_visible(open_state)
    pygame.event.set_grab(not open_state)
    pygame.mouse.get_rel()
    return open_state


def draw_hamburger(surface: pygame.Surface, hovered: bool, active: bool) -> None:
    """Draw a simple hamburger icon button."""
    base_color = (230, 230, 230) if hovered else (200, 200, 200)
    if active:
        base_color = (140, 220, 255)
    rect = pygame.Rect(*settings.HAMBURGER_RECT)
    pygame.draw.rect(surface, (40, 40, 50), rect, border_radius=8)
    for i in range(3):
        y = rect.y + 8 + i * 9
        pygame.draw.line(surface, base_color, (rect.x + 8, y), (rect.x + rect.width - 8, y), 3)


def draw_crosshair(surface: pygame.Surface) -> None:
    """Render a minimal crosshair."""
    center = (settings.HALF_WIDTH, settings.HALF_HEIGHT)
    pygame.draw.circle(surface, (220, 220, 220), center, 3, 1)
    pygame.draw.line(surface, (220, 220, 220), (center[0] - 15, center[1]), (center[0] + 15, center[1]), 1)
    pygame.draw.line(surface, (220, 220, 220), (center[0], center[1] - 15), (center[0], center[1] + 15), 1)


def compute_slider_rects(value: float) -> Tuple[pygame.Rect, pygame.Rect]:
    """Return slider bar and handle rectangles for the menu."""
    settings_rect = pygame.Rect(*settings.SETTINGS_RECT)
    slider_bar = pygame.Rect(settings_rect.x + 60, settings_rect.y + 140, settings_rect.width - 120, 6)
    handle_x = slider_bar.x + int(value * slider_bar.width)
    slider_handle = pygame.Rect(handle_x - 8, slider_bar.y - 6, 16, 16)
    return slider_bar, slider_handle


def draw_menu(
    surface: pygame.Surface,
    slider_bar: pygame.Rect,
    slider_handle: pygame.Rect,
    sensitivity: float,
    font,
    title_font,
) -> None:
    """Render the in-game options menu."""
    settings_rect = pygame.Rect(*settings.SETTINGS_RECT)
    pygame.draw.rect(surface, (20, 20, 26), settings_rect, border_radius=16)
    pygame.draw.rect(surface, (80, 80, 110), settings_rect, 2, border_radius=16)
    title = title_font.render("Settings", True, (230, 230, 240))
    surface.blit(title, (settings_rect.centerx - title.get_width() // 2, settings_rect.y + 20))

    label = font.render("Mouse sensitivity", True, (200, 200, 210))
    surface.blit(label, (slider_bar.x, slider_bar.y - 30))
    pygame.draw.rect(surface, (80, 80, 90), slider_bar)
    pygame.draw.circle(surface, (180, 220, 255), slider_handle.center, slider_handle.width // 2)

    value_text = font.render(f"{sensitivity:.4f}", True, (200, 200, 210))
    surface.blit(value_text, (slider_bar.x, slider_bar.y + 20))
