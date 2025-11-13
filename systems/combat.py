"""Projectile and explosion management."""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import pygame

from config import tuning


def spawn_projectile(
    container: list,
    px: float,
    py: float,
    angle: float,
    *,
    owner: str = "player",
    speed: float | None = None,
) -> None:
    direction_x = math.cos(angle)
    direction_y = math.sin(angle)
    start_x = px + direction_x * 0.35
    start_y = py + direction_y * 0.35
    container.append(
        {
            "pos": [start_x, start_y],
            "dir": (direction_x, direction_y),
            "speed": speed or tuning.PROJECTILE_SPEED,
            "distance": 0.0,
            "spawn_time": pygame.time.get_ticks() / 1000.0,
            "owner": owner,
        }
    )


def update_projectiles(
    active_projectiles: list,
    active_explosions: list,
    active_enemies: list,
    delta_time: float,
    time_now: float,
    is_wall,
    player_pos: Tuple[float, float],
    player_hit_radius: float,
    on_player_hit,
) -> Tuple[List[Dict], List[Dict]]:
    updated_projectiles = []
    enemies_hit: List[Dict] = []
    for projectile in active_projectiles:
        direction_x, direction_y = projectile["dir"]
        distance_step = projectile["speed"] * delta_time
        if distance_step <= 0.0:
            updated_projectiles.append(projectile)
            continue
        steps = max(1, int(distance_step / tuning.PROJECTILE_STEP_DISTANCE))
        step_distance = distance_step / steps
        step_dx = direction_x * step_distance
        step_dy = direction_y * step_distance
        pos_x, pos_y = projectile["pos"]
        travelled = projectile["distance"]
        collided = False
        for _ in range(steps):
            pos_x += step_dx
            pos_y += step_dy
            travelled += math.hypot(step_dx, step_dy)
            if is_wall(pos_x, pos_y):
                collided = True
                break
            if projectile["owner"] == "player":
                for enemy in active_enemies:
                    if enemy in enemies_hit:
                        continue
                    if math.hypot(pos_x - enemy["pos"][0], pos_y - enemy["pos"][1]) <= tuning.ENEMY_HIT_RADIUS:
                        enemies_hit.append(enemy)
                        collided = True
                        break
            else:
                if math.hypot(pos_x - player_pos[0], pos_y - player_pos[1]) <= player_hit_radius:
                    on_player_hit()
                    collided = True
                    break
            if collided:
                break
        if collided or travelled >= tuning.PROJECTILE_MAX_DISTANCE:
            active_explosions.append({"pos": (pos_x, pos_y), "start": time_now})
            continue
        projectile["pos"] = [pos_x, pos_y]
        projectile["distance"] = travelled
        updated_projectiles.append(projectile)
    return updated_projectiles, enemies_hit
