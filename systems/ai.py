"""Basic enemy AI for movement and shooting."""

from __future__ import annotations

import math
from typing import Callable, List, Tuple

from config import tuning


def _move_towards(enemy_pos, target_pos, delta_time, is_wall) -> bool:
    dx = target_pos[0] - enemy_pos[0]
    dy = target_pos[1] - enemy_pos[1]
    distance = math.hypot(dx, dy)
    if distance < 1e-5:
        return False
    direction = (dx / distance, dy / distance)
    speed = tuning.ENEMY_MOVE_SPEED * delta_time
    moved = False

    if distance > tuning.ENEMY_STOP_DISTANCE:
        trial_x = enemy_pos[0] + direction[0] * speed
        if not is_wall(trial_x, enemy_pos[1]):
            enemy_pos[0] = trial_x
            moved = True
        trial_y = enemy_pos[1] + direction[1] * speed
        if not is_wall(enemy_pos[0], trial_y):
            enemy_pos[1] = trial_y
            moved = True
    return moved


def update_enemies(
    enemies: List[dict],
    player_pos: Tuple[float, float],
    delta_time: float,
    current_time: float,
    is_wall,
    fire_callback: Callable[[Tuple[float, float], float], None],
) -> bool:
    """Move enemies and trigger shooting; returns True if activity happened."""
    activity = False
    for enemy in enemies:
        moved = _move_towards(enemy["pos"], player_pos, delta_time, is_wall)
        if moved:
            activity = True
        dx = player_pos[0] - enemy["pos"][0]
        dy = player_pos[1] - enemy["pos"][1]
        distance = math.hypot(dx, dy)
        if distance <= tuning.ENEMY_FIRE_DISTANCE:
            if current_time - enemy.get("last_shot", 0.0) >= tuning.ENEMY_FIRE_COOLDOWN:
                angle = math.atan2(dy, dx)
                fire_callback(tuple(enemy["pos"]), angle)
                enemy["last_shot"] = current_time
                activity = True
    return activity
