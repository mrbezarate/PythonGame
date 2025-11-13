"""Rendering and raycasting helpers with textured floor/ceiling and lighting."""

from __future__ import annotations

import math
from typing import NamedTuple, Sequence

import pygame

from config import settings, tuning

FOV = math.radians(70)
HALF_FOV = FOV / 2
NUM_RAYS = settings.WIDTH // 2
DELTA_ANGLE = FOV / NUM_RAYS
MAX_DEPTH = math.hypot(settings.MAP_WIDTH, settings.MAP_HEIGHT)
MAX_RAY_STEPS = int(MAX_DEPTH)
DISTANCE_PROJ_PLANE = settings.HALF_WIDTH / math.tan(HALF_FOV)
SCALE = settings.WIDTH / NUM_RAYS
FLOOR_PIXEL_STEP = 4


class RayHit(NamedTuple):
    distance: float
    side: int
    map_x: int
    map_y: int


_world_map: Sequence[str] | None = None
_wall_cache: set[tuple[int, int]] | None = None
_lighting_overlay: pygame.Surface | None = None
_tile_palette: list[list[tuple[int, int, int]]] | None = None
_tile_width = 0
_tile_height = 0


def _build_lighting_overlay() -> pygame.Surface:
    overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
    for y in range(settings.HEIGHT):
        strength = int(120 * (y / settings.HEIGHT))
        pygame.draw.line(overlay, (0, 0, 0, strength), (0, y), (settings.WIDTH, y))
    return overlay


def configure(
    world_map: Sequence[str],
    wall_cache: set[tuple[int, int]],
    *,
    tile_texture: pygame.Surface | None = None,
) -> None:
    """Provide map data and optional floor/ceiling texture."""
    global _world_map, _wall_cache, _lighting_overlay, _tile_palette, _tile_width, _tile_height
    _world_map = world_map
    _wall_cache = wall_cache
    if tile_texture:
        converted = tile_texture.convert()
        _tile_width, _tile_height = converted.get_size()
        _tile_palette = [
            [tuple(converted.get_at((x, y))[:3]) for x in range(_tile_width)]
            for y in range(_tile_height)
        ]
    else:
        _tile_palette = None
        _tile_width = _tile_height = 0
    _lighting_overlay = _build_lighting_overlay()


def _ensure_map() -> tuple[Sequence[str], set[tuple[int, int]]]:
    if _world_map is None or _wall_cache is None:
        raise RuntimeError("Raycasting module not configured with world data.")
    return _world_map, _wall_cache


def _sample_tile(world_x: float, world_y: float) -> tuple[int, int, int]:
    if not _tile_palette:
        return (60, 60, 70)
    frac_x = world_x - math.floor(world_x)
    frac_y = world_y - math.floor(world_y)
    tx = int(frac_x * _tile_width) % _tile_width
    ty = int(frac_y * _tile_height) % _tile_height
    return _tile_palette[ty][tx]


def _draw_floor_and_ceiling(surface: pygame.Surface, px: float, py: float, angle: float) -> None:
    surface.fill(settings.BG_COLOR, pygame.Rect(0, 0, settings.WIDTH, settings.HALF_HEIGHT))
    surface.fill(
        settings.FLOOR_COLOR,
        pygame.Rect(0, settings.HALF_HEIGHT, settings.WIDTH, settings.HALF_HEIGHT),
    )
    if not _tile_palette:
        return

    dir_x = math.cos(angle)
    dir_y = math.sin(angle)
    plane_scale = math.tan(HALF_FOV)
    plane_x = -dir_y * plane_scale
    plane_y = dir_x * plane_scale
    ray_dir_x0 = dir_x - plane_x
    ray_dir_y0 = dir_y - plane_y
    ray_dir_x1 = dir_x + plane_x
    ray_dir_y1 = dir_y + plane_y
    pos_z = settings.HALF_HEIGHT

    for y in range(settings.HALF_HEIGHT, settings.HEIGHT, FLOOR_PIXEL_STEP):
        p = y - settings.HALF_HEIGHT
        denom = max(1.0, p)
        row_distance = pos_z / denom
        base_x = px + row_distance * ray_dir_x0
        base_y = py + row_distance * ray_dir_y0
        step_x = row_distance * (ray_dir_x1 - ray_dir_x0) / settings.WIDTH
        step_y = row_distance * (ray_dir_y1 - ray_dir_y0) / settings.WIDTH
        world_x = base_x
        world_y = base_y
        rect_height = min(FLOOR_PIXEL_STEP, settings.HEIGHT - y)
        for x in range(0, settings.WIDTH, FLOOR_PIXEL_STEP):
            col = _sample_tile(world_x, world_y)
            shade = max(0.2, min(1.0, 1.2 / (row_distance * 0.1 + 0.4)))
            floor_color = tuple(max(0, min(255, int(component * shade))) for component in col)
            surface.fill(floor_color, (x, y, FLOOR_PIXEL_STEP, rect_height))

            mirror_y = settings.HEIGHT - y - rect_height
            if mirror_y >= 0:
                ceiling_color = (
                    min(255, int(floor_color[0] * 0.6 + 30)),
                    min(255, int(floor_color[1] * 0.7 + 40)),
                    min(255, int(floor_color[2] * 0.9 + 50)),
                )
                surface.fill(ceiling_color, (x, mirror_y, FLOOR_PIXEL_STEP, rect_height))

            world_x += step_x * FLOOR_PIXEL_STEP
            world_y += step_y * FLOOR_PIXEL_STEP


def cast_single_ray(px: float, py: float, angle: float) -> RayHit:
    """Traditional DDA raycast returning distance and side information."""
    _, wall_cache = _ensure_map()
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    sin_a = sin_a if abs(sin_a) > 1e-6 else 1e-6
    cos_a = cos_a if abs(cos_a) > 1e-6 else 1e-6

    map_x = int(px)
    map_y = int(py)

    delta_dist_x = abs(1 / cos_a)
    delta_dist_y = abs(1 / sin_a)

    if cos_a > 0:
        step_x = 1
        side_dist_x = (map_x + 1 - px) * delta_dist_x
    else:
        step_x = -1
        side_dist_x = (px - map_x) * delta_dist_x

    if sin_a > 0:
        step_y = 1
        side_dist_y = (map_y + 1 - py) * delta_dist_y
    else:
        step_y = -1
        side_dist_y = (py - map_y) * delta_dist_y

    for _ in range(MAX_RAY_STEPS):
        if side_dist_x < side_dist_y:
            map_x += step_x
            distance = side_dist_x
            side_dist_x += delta_dist_x
            side = 0
        else:
            map_y += step_y
            distance = side_dist_y
            side_dist_y += delta_dist_y
            side = 1

        if map_x < 0 or map_x >= settings.MAP_WIDTH or map_y < 0 or map_y >= settings.MAP_HEIGHT:
            break
        if (map_x, map_y) in wall_cache:
            return RayHit(distance=distance, side=side, map_x=map_x, map_y=map_y)
    return RayHit(distance=MAX_DEPTH, side=0, map_x=map_x, map_y=map_y)


def _wall_color(hit: RayHit, distance: float) -> tuple[int, int, int]:
    base_variation = ((hit.map_x + hit.map_y) % 3) * 8
    base_color = (150 + base_variation, 170 + base_variation, 205)
    light = max(0.18, min(1.0, 1 / (1 + distance * 0.05)))
    if hit.side == 1:
        light *= 0.6
    shaded = tuple(max(0, min(255, int(channel * light))) for channel in base_color)
    return shaded


def draw_world(surface: pygame.Surface, px: float, py: float, angle: float) -> None:
    """Render the pseudo-3D view via ray casting."""
    _ensure_map()
    _draw_floor_and_ceiling(surface, px, py, angle)

    start_angle = angle - HALF_FOV
    for ray in range(NUM_RAYS):
        ray_angle = start_angle + ray * DELTA_ANGLE
        hit = cast_single_ray(px, py, ray_angle)
        depth = max(hit.distance, 0.0001)
        depth_corrected = depth * math.cos(angle - ray_angle)
        proj_height = min(settings.HEIGHT, max(30, int(DISTANCE_PROJ_PLANE / depth_corrected)))
        color = _wall_color(hit, depth_corrected)
        pygame.draw.rect(
            surface,
            color,
            (ray * SCALE, settings.HALF_HEIGHT - proj_height // 2, SCALE, proj_height),
        )
    if _lighting_overlay:
        surface.blit(_lighting_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)


def draw_minimap(
    surface: pygame.Surface,
    px: float,
    py: float,
    angle: float,
    minimap_base: pygame.Surface,
    minimap_overlay: pygame.Surface,
    projectiles: list | None = None,
    explosions: list | None = None,
    enemies: list | None = None,
    zoom: float = settings.MINIMAP_DEFAULT_ZOOM,
) -> None:
    """Render a zoomable minimap with local focus near the player."""
    texture_scale = settings.MINIMAP_TEXTURE_SCALE
    center_x = int(px * texture_scale)
    center_y = int(py * texture_scale)
    half_view = max(8, int(zoom * texture_scale // 2))
    view_rect = pygame.Rect(center_x - half_view, center_y - half_view, half_view * 2, half_view * 2)
    view_rect.clamp_ip(minimap_base.get_rect())
    cropped = minimap_base.subsurface(view_rect)
    minimap_surface = pygame.transform.scale(cropped, (settings.MINIMAP_SIZE, settings.MINIMAP_SIZE))

    def world_to_minimap(wx: float, wy: float) -> tuple[int, int]:
        sx = (wx * texture_scale - view_rect.x) / view_rect.width
        sy = (wy * texture_scale - view_rect.y) / view_rect.height
        return (
            int(max(0.0, min(1.0, sx)) * settings.MINIMAP_SIZE),
            int(max(0.0, min(1.0, sy)) * settings.MINIMAP_SIZE),
        )

    player_point = world_to_minimap(px, py)
    pygame.draw.circle(minimap_surface, (250, 200, 80), player_point, 4)
    line_length = 24
    facing_point = (
        player_point[0] + int(math.cos(angle) * line_length),
        player_point[1] + int(math.sin(angle) * line_length),
    )
    pygame.draw.line(minimap_surface, (250, 200, 80), player_point, facing_point, 2)

    if projectiles:
        for projectile in projectiles:
            proj_pos = projectile["pos"]
            color = (255, 120, 80) if projectile.get("owner") == "player" else (80, 180, 255)
            pygame.draw.circle(minimap_surface, color, world_to_minimap(proj_pos[0], proj_pos[1]), 3)
    if explosions:
        for explosion in explosions:
            exp_pos = explosion["pos"]
            pygame.draw.circle(minimap_surface, (255, 200, 140), world_to_minimap(exp_pos[0], exp_pos[1]), 6, 1)
    if enemies:
        for enemy in enemies:
            pygame.draw.circle(minimap_surface, (220, 70, 70), world_to_minimap(enemy["pos"][0], enemy["pos"][1]), 5)

    minimap_surface.blit(minimap_overlay, (0, 0))
    surface.blit(minimap_surface, settings.MAP_OFFSET)


def project_sprite(px: float, py: float, angle: float, target_x: float, target_y: float):
    """Compute sprite projection coordinates for billboard rendering."""
    dx = target_x - px
    dy = target_y - py
    sprite_angle = math.atan2(dy, dx)
    angle_diff = (sprite_angle - angle + math.pi) % (2 * math.pi) - math.pi
    if abs(angle_diff) > HALF_FOV:
        return None
    distance = math.hypot(dx, dy)
    if distance <= 0.0001:
        return None
    depth_to_wall = cast_single_ray(px, py, angle + angle_diff).distance
    if depth_to_wall < distance - 0.05:
        return None
    screen_x = int(settings.HALF_WIDTH + math.tan(angle_diff) * DISTANCE_PROJ_PLANE)
    return distance, screen_x


def draw_enemies(
    surface: pygame.Surface,
    px: float,
    py: float,
    angle: float,
    active_enemies: list,
    time_now: float,
    enemy_texture: pygame.Surface,
) -> None:
    """Render billboarded enemies sorted back-to-front."""
    sprites_to_draw = []

    for enemy in active_enemies:
        projection = project_sprite(px, py, angle, enemy["pos"][0], enemy["pos"][1])
        if projection is None:
            continue
        distance, screen_x = projection
        distance = max(distance, 0.0001)
        scale_factor = max(0.5, min(2.5, 3.0 / (distance + 0.4)))
        size = int(enemy_texture.get_width() * scale_factor)
        sprite = pygame.transform.smoothscale(enemy_texture, (size, size))
        bob = math.sin((time_now - enemy["spawn_time"]) * 2.4) * 6
        sprite_rect = sprite.get_rect(center=(screen_x, settings.HALF_HEIGHT - 20 + bob))
        sprites_to_draw.append((distance, sprite, sprite_rect))

    sprites_to_draw.sort(key=lambda item: item[0], reverse=True)
    for _, sprite, rect in sprites_to_draw:
        surface.blit(sprite, rect)


def draw_projectiles(
    surface: pygame.Surface,
    px: float,
    py: float,
    angle: float,
    active_projectiles: list,
    active_explosions: list,
    time_now: float,
    fire_sprites: dict[str, list[pygame.Surface]],
) -> None:
    """Draw projectiles and explosion effects."""
    sprites_to_draw = []

    for projectile in active_projectiles:
        projection = project_sprite(px, py, angle, projectile["pos"][0], projectile["pos"][1])
        if projection is None:
            continue
        distance, screen_x = projection
        size = max(42, min(160, int(320 / distance)))
        life = max(0.0, time_now - projectile["spawn_time"])
        body_frames = fire_sprites["front_frames"]
        trail_frames = fire_sprites["trail_frames"]
        body_index = int(life * 8) % len(body_frames)
        trail_index = int(life * 10) % len(trail_frames)

        body_frame = pygame.transform.smoothscale(body_frames[body_index], (size, size))
        trail_frame = pygame.transform.smoothscale(trail_frames[trail_index], (int(size * 1.5), int(size * 1.5)))
        body_frame.set_alpha(235)
        trail_frame.set_alpha(210)

        orientation_angle = math.degrees(math.atan2(projectile["dir"][1], projectile["dir"][0])) - 90
        tint = (255, 140, 90) if projectile.get("owner") == "player" else (90, 180, 255)
        tint_surface = pygame.Surface(body_frame.get_size(), pygame.SRCALPHA)
        tint_surface.fill((*tint, 60))
        body_frame.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        trail_rotated = pygame.transform.rotate(trail_frame, orientation_angle)
        body_rotated = pygame.transform.rotate(body_frame, orientation_angle)

        trail_rect = trail_rotated.get_rect(center=(screen_x, settings.HALF_HEIGHT + 10))
        body_rect = body_rotated.get_rect(center=(screen_x, settings.HALF_HEIGHT))

        sprites_to_draw.append((distance + 0.2, trail_rotated, trail_rect))
        sprites_to_draw.append((distance, body_rotated, body_rect))

    explosion_frames = fire_sprites["explosion_frames"]
    explosion_frame_count = len(explosion_frames)

    for explosion in active_explosions:
        projection = project_sprite(px, py, angle, explosion["pos"][0], explosion["pos"][1])
        if projection is None:
            continue
        distance, screen_x = projection
        progress = (time_now - explosion["start"]) / tuning.EXPLOSION_DURATION
        if progress >= 1.0:
            continue
        frame_index = min(int(progress * explosion_frame_count * 1.4), explosion_frame_count - 1)
        frame_surface = explosion_frames[frame_index]
        size = int(max(80, min(260, 130 + progress * 220)))
        explosion_surface = pygame.transform.smoothscale(frame_surface, (size, size))
        explosion_surface.set_alpha(max(0, min(255, int(255 * (1.0 - progress)))))
        explosion_rect = explosion_surface.get_rect(center=(screen_x, settings.HALF_HEIGHT))
        sprites_to_draw.append((distance, explosion_surface, explosion_rect))

    sprites_to_draw.sort(key=lambda item: item[0], reverse=True)
    for _, sprite, rect in sprites_to_draw:
        surface.blit(sprite, rect)
