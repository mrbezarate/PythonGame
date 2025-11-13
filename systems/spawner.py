"""Enemy spawning helpers."""

from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from config import settings, tuning


def find_enemy_spawn_position(existing_enemies: List[Dict], px: float, py: float, is_wall) -> Tuple[float, float] | None:
    """Attempt to find a spawn location away from the player and other enemies."""
    for _ in range(tuning.ENEMY_SPAWN_ATTEMPTS):
        candidate_x = random.uniform(0.8, settings.MAP_WIDTH - 0.8)
        candidate_y = random.uniform(0.8, settings.MAP_HEIGHT - 0.8)
        if is_wall(candidate_x, candidate_y):
            continue
        if math.hypot(candidate_x - px, candidate_y - py) < tuning.ENEMY_SPAWN_DISTANCE:
            continue
        too_close = False
        for enemy in existing_enemies:
            if math.hypot(candidate_x - enemy["pos"][0], candidate_y - enemy["pos"][1]) < tuning.ENEMY_MIN_SEPARATION:
                too_close = True
                break
        if too_close:
            continue
        return candidate_x, candidate_y
    return None


def spawn_enemy(existing_enemies: List[Dict], px: float, py: float, current_time: float, is_wall) -> bool:
    """Spawn an enemy if there is free space."""
    spawn_pos = find_enemy_spawn_position(existing_enemies, px, py, is_wall)
    if spawn_pos is None:
        return False
    enemy_entry = {
        "pos": [spawn_pos[0], spawn_pos[1]],
        "spawn_time": current_time,
        "last_shot": current_time,
    }
    existing_enemies.append(enemy_entry)
    return True
