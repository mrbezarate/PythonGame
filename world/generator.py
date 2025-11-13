"""Procedural world generation for the maze-like map."""

from __future__ import annotations

import random
from collections import deque
from typing import Dict, List, Tuple


def generate_world_map(width: int, height: int, seed: int = 42) -> List[str]:
    rng = random.Random(seed)
    grid: List[List[str]] = [["1" for _ in range(width)] for _ in range(height)]
    carved_centers: List[Tuple[int, int]] = []

    def carve(x: int, y: int) -> None:
        if 0 < x < width - 1 and 0 < y < height - 1:
            grid[y][x] = "0"

    def carve_ellipse(cx: int, cy: int, rx: int, ry: int) -> None:
        rx_sq = max(1, rx * rx)
        ry_sq = max(1, ry * ry)
        for dy in range(-ry, ry + 1):
            py = cy + dy
            if py <= 0 or py >= height - 1:
                continue
            for dx in range(-rx, rx + 1):
                px = cx + dx
                if px <= 0 or px >= width - 1:
                    continue
                if (dx * dx) * ry_sq + (dy * dy) * rx_sq <= rx_sq * ry_sq:
                    grid[py][px] = "0"

    def carve_rectangle(cx: int, cy: int, half_w: int, half_h: int) -> None:
        x0 = max(1, cx - half_w)
        x1 = min(width - 2, cx + half_w)
        y0 = max(1, cy - half_h)
        y1 = min(height - 2, cy + half_h)
        for py in range(y0, y1 + 1):
            row = grid[py]
            for px in range(x0, x1 + 1):
                row[px] = "0"

    area = width * height
    room_attempts = max(80, area // 1700)
    for _ in range(room_attempts):
        cx = rng.randint(8, width - 9)
        cy = rng.randint(8, height - 9)
        if rng.random() < 0.6:
            carve_ellipse(cx, cy, rng.randint(5, 13), rng.randint(4, 11))
        else:
            carve_rectangle(cx, cy, rng.randint(4, 12), rng.randint(4, 12))
        carved_centers.append((cx, cy))

    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    corridor_count = room_attempts * 2
    for _ in range(corridor_count):
        if not carved_centers:
            break
        x, y = rng.choice(carved_centers)
        dx, dy = rng.choice(directions)
        length = rng.randint(18, 64)
        corridor_half_width = 1 if rng.random() < 0.75 else 2
        for _ in range(length):
            if x <= 1 or x >= width - 2 or y <= 1 or y >= height - 2:
                break
            carve(x, y)
            for offset in range(1, corridor_half_width + 1):
                if dx != 0:
                    carve(x, y + offset)
                    carve(x, y - offset)
                else:
                    carve(x + offset, y)
                    carve(x - offset, y)
            if rng.random() < 0.1:
                dx, dy = rng.choice(directions)
            x += dx
            y += dy

    neighbor_offsets = [
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (1, 0),
        (-1, 1),
        (0, 1),
        (1, 1),
    ]

    for _ in range(3):
        new_grid = [row[:] for row in grid]
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                floor_neighbors = 0
                for ox, oy in neighbor_offsets:
                    nx = x + ox
                    ny = y + oy
                    if grid[ny][nx] == "0":
                        floor_neighbors += 1
                if grid[y][x] == "0":
                    if floor_neighbors < 2:
                        new_grid[y][x] = "1"
                else:
                    if floor_neighbors >= 5:
                        new_grid[y][x] = "0"
        grid = new_grid

    def carve_wide(x: int, y: int, radius: int = 1) -> None:
        radius = max(0, radius)
        for dy in range(-radius, radius + 1):
            py = y + dy
            if py <= 0 or py >= height - 1:
                continue
            for dx in range(-radius, radius + 1):
                px = x + dx
                if px <= 0 or px >= width - 1:
                    continue
                if max(abs(dx), abs(dy)) <= radius:
                    grid[py][px] = "0"

    def carve_line(x0: int, y0: int, x1: int, y1: int, radius: int = 1) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0))
        if steps == 0:
            carve_wide(x0, y0, radius)
            return
        for step in range(steps + 1):
            t = step / steps
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            if 1 <= x < width - 1 and 1 <= y < height - 1:
                carve_wide(x, y, radius)

    def ensure_spawn_area() -> Tuple[int, int]:
        cx = width // 2
        cy = height // 2
        spawn_radius = 7
        for dy in range(-spawn_radius, spawn_radius + 1):
            py = cy + dy
            if py <= 1 or py >= height - 2:
                continue
            for dx in range(-spawn_radius, spawn_radius + 1):
                px = cx + dx
                if px <= 1 or px >= width - 2:
                    continue
                if dx * dx + dy * dy <= spawn_radius * spawn_radius:
                    grid[py][px] = "0"

        corridor_radius = 2

        def dig_corridor(dir_x: int, dir_y: int) -> None:
            x, y = cx, cy
            max_steps = max(width, height)
            for step in range(1, max_steps):
                x += dir_x
                y += dir_y
                if not (1 <= x < width - 1 and 1 <= y < height - 1):
                    break
                was_floor = grid[y][x] == "0"
                carve_wide(x, y, corridor_radius)
                if was_floor and step > spawn_radius + 4:
                    break
                if random.random() < 0.08:
                    turn_dir = random.choice(directions)
                    tx = x + turn_dir[0]
                    ty = y + turn_dir[1]
                    if 1 <= tx < width - 1 and 1 <= ty < height - 1:
                        carve_wide(tx, ty, corridor_radius)

        for dir_x, dir_y in directions:
            dig_corridor(dir_x, dir_y)
        return cx, cy

    def build_navigation_lattice(center: Tuple[int, int]) -> None:
        cx, cy = center
        divisions = 8
        for i in range(2, divisions, 2):
            x = int(i * width / divisions)
            carve_line(x, 1, x, height - 2, 1)
            y = int(i * height / divisions)
            carve_line(1, y, width - 2, y, 1)
        edge_targets = [
            (1, 1),
            (width - 2, 1),
            (1, height - 2),
            (width - 2, height - 2),
            (width // 2, 1),
            (width // 2, height - 2),
            (1, height // 2),
            (width - 2, height // 2),
        ]
        for ex, ey in edge_targets:
            carve_line(cx, cy, ex, ey, 2)

    def compute_reachable_from(sx: int, sy: int) -> Tuple[List[List[bool]], int, List[Tuple[int, int]]]:
        reachable_mask = [[False] * width for _ in range(height)]
        reachable_cells: List[Tuple[int, int]] = []
        if not (0 <= sx < width and 0 <= sy < height):
            return reachable_mask, 0, reachable_cells
        if grid[sy][sx] != "0":
            return reachable_mask, 0, reachable_cells
        queue_local: deque[Tuple[int, int]] = deque()
        queue_local.append((sx, sy))
        reachable_mask[sy][sx] = True
        reachable_cells.append((sx, sy))
        while queue_local:
            x, y = queue_local.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx = x + dx
                ny = y + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue
                if grid[ny][nx] != "0" or reachable_mask[ny][nx]:
                    continue
                reachable_mask[ny][nx] = True
                reachable_cells.append((nx, ny))
                queue_local.append((nx, ny))
        return reachable_mask, len(reachable_cells), reachable_cells

    def mark_reachable_from(
        sx: int,
        sy: int,
        reachable_mask: List[List[bool]],
        reachable_cells: List[Tuple[int, int]],
    ) -> None:
        if not (0 <= sx < width and 0 <= sy < height):
            return
        if grid[sy][sx] != "0" or reachable_mask[sy][sx]:
            return
        queue_local: deque[Tuple[int, int]] = deque()
        queue_local.append((sx, sy))
        reachable_mask[sy][sx] = True
        reachable_cells.append((sx, sy))
        while queue_local:
            x, y = queue_local.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx = x + dx
                ny = y + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue
                if grid[ny][nx] != "0" or reachable_mask[ny][nx]:
                    continue
                reachable_mask[ny][nx] = True
                reachable_cells.append((nx, ny))
                queue_local.append((nx, ny))

    def carve_tunnel(start: Tuple[int, int], end: Tuple[int, int]) -> None:
        x, y = start
        tx, ty = end
        carve_wide(x, y, 1)
        max_steps = width + height
        steps = 0
        while (x, y) != (tx, ty) and steps < max_steps:
            steps += 1
            move_horizontal = abs(tx - x) > abs(ty - y)
            if move_horizontal and x != tx:
                x += 1 if tx > x else -1
            elif y != ty:
                y += 1 if ty > y else -1
            elif x != tx:
                x += 1 if tx > x else -1
            carve_wide(x, y, 1)
            if rng.random() < 0.3 and x != tx:
                side_step = 1 if tx > x else -1
                carve_wide(x + side_step, y, 0)
            if rng.random() < 0.3 and y != ty:
                vertical_step = 1 if ty > y else -1
                carve_wide(x, y + vertical_step, 0)
        carve_wide(tx, ty, 1)

    def connect_unreachable_components(
        reachable_mask: List[List[bool]],
        reachable_cells: List[Tuple[int, int]],
        center: Tuple[int, int],
    ) -> None:
        seen = [[False] * width for _ in range(height)]
        cx, cy = center
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if grid[y][x] != "0" or reachable_mask[y][x] or seen[y][x]:
                    continue
                component: List[Tuple[int, int]] = []
                queue_local: deque[Tuple[int, int]] = deque()
                queue_local.append((x, y))
                seen[y][x] = True
                while queue_local:
                    px, py = queue_local.popleft()
                    component.append((px, py))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx = px + dx
                        ny = py + dy
                        if not (1 <= nx < width - 1 and 1 <= ny < height - 1):
                            continue
                        if grid[ny][nx] != "0" or reachable_mask[ny][nx] or seen[ny][nx]:
                            continue
                        seen[ny][nx] = True
                        queue_local.append((nx, ny))
                if not component or not reachable_cells:
                    continue
                target = min(component, key=lambda cell: (cell[0] - cx) ** 2 + (cell[1] - cy) ** 2)
                connect_to = min(
                    reachable_cells,
                    key=lambda cell: (cell[0] - target[0]) ** 2 + (cell[1] - target[1]) ** 2,
                )
                carve_tunnel(connect_to, target)
                mark_reachable_from(target[0], target[1], reachable_mask, reachable_cells)

    center = ensure_spawn_area()
    build_navigation_lattice(center)
    reachable_mask, reachable_count, reachable_cells = compute_reachable_from(center[0], center[1])
    if reachable_count == 0:
        carve(center[0], center[1])
        reachable_mask, reachable_count, reachable_cells = compute_reachable_from(center[0], center[1])
    connect_unreachable_components(reachable_mask, reachable_cells, center)
    reachable_mask, _, _ = compute_reachable_from(center[0], center[1])

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] == "0" and not reachable_mask[y][x]:
                grid[y][x] = "1"

    for x in range(width):
        grid[0][x] = "1"
        grid[height - 1][x] = "1"
    for y in range(height):
        grid[y][0] = "1"
        grid[y][width - 1] = "1"

    return ["".join(row) for row in grid]
