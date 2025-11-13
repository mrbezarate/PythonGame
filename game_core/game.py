"""High-level game loop orchestration."""

from __future__ import annotations

import logging
import math
import sys
from typing import Tuple

import pygame

from assets.loaders import load_enemy_texture, load_fire_variants, load_world_tile_texture
from config import settings, tuning
from systems import ai, combat, raycast, spawner
from ui import hud, menu
from world.map_data import build_minimap_surfaces, build_world


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))
        pygame.display.set_caption("Pygame Window")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont(None, settings.TEXT_FONT_SIZE)
        self.title_font = pygame.font.SysFont(None, settings.TITLE_FONT_SIZE)

        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

        self.world_map, self.wall_cache = build_world()
        self.minimap_base, self.minimap_overlay = build_minimap_surfaces(self.world_map)
        self.world_tile_texture = load_world_tile_texture()
        raycast.configure(self.world_map, self.wall_cache, tile_texture=self.world_tile_texture)

        self.player_x = settings.MAP_WIDTH / 2 + 0.5
        self.player_y = settings.MAP_HEIGHT / 2 + 0.5
        self.player_angle = 0.0

        self.projectiles: list = []
        self.explosions: list = []
        self.enemies: list = []

        self.last_shot_time = 0.0
        self.last_dash_time = -10.0
        self.last_move_vector = (math.cos(self.player_angle), math.sin(self.player_angle))
        self.last_enemy_spawn_time = pygame.time.get_ticks() / 1000.0

        self.player_health = tuning.PLAYER_MAX_HEALTH

        self.fire_sprites = load_fire_variants()
        self.enemy_texture = load_enemy_texture()

        self.menu_open = False
        self.slider_dragging = False
        self.slider_value = settings.DEFAULT_SLIDER_VALUE
        self.mouse_sensitivity = self._compute_mouse_sensitivity()
        self.minimap_zoom = settings.MINIMAP_DEFAULT_ZOOM

        self.hamburger_rect = pygame.Rect(*settings.HAMBURGER_RECT)

        self.last_fps_log = 0.0
        self.last_activity_time = pygame.time.get_ticks() / 1000.0
        self.current_target_fps = settings.TARGET_FPS_ACTIVE

        menu.set_menu_state(False)
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()

    def _compute_mouse_sensitivity(self) -> float:
        return settings.SENSITIVITY_MIN + self.slider_value * (settings.SENSITIVITY_MAX - settings.SENSITIVITY_MIN)

    def _adjust_minimap_zoom(self, delta: float) -> bool:
        new_zoom = max(
            settings.MINIMAP_MIN_ZOOM,
            min(settings.MINIMAP_MAX_ZOOM, self.minimap_zoom + delta),
        )
        if abs(new_zoom - self.minimap_zoom) < 1e-3:
            return False
        self.minimap_zoom = new_zoom
        return True
    def is_wall(self, x: float, y: float) -> bool:
        ix = int(x)
        iy = int(y)
        if ix < 0 or ix >= settings.MAP_WIDTH or iy < 0 or iy >= settings.MAP_HEIGHT:
            return True
        return (ix, iy) in self.wall_cache

    def handle_dash(self, dash_requested: bool, move_direction: Tuple[float, float], current_time: float) -> bool:
        if not dash_requested or self.menu_open or (current_time - self.last_dash_time) < tuning.DASH_COOLDOWN:
            return False
        dash_dir = move_direction
        if abs(dash_dir[0]) < 1e-6 and abs(dash_dir[1]) < 1e-6:
            dash_dir = self.last_move_vector
        if abs(dash_dir[0]) < 1e-6 and abs(dash_dir[1]) < 1e-6:
            dash_dir = (math.cos(self.player_angle), math.sin(self.player_angle))
        dash_length = math.hypot(dash_dir[0], dash_dir[1])
        moved = False
        if dash_length > 0.0:
            norm_dir = (dash_dir[0] / dash_length, dash_dir[1] / dash_length)
            steps = max(1, int(tuning.DASH_DISTANCE / tuning.DASH_STEP_DISTANCE))
            step_dx = norm_dir[0] * (tuning.DASH_DISTANCE / steps)
            step_dy = norm_dir[1] * (tuning.DASH_DISTANCE / steps)
            for _ in range(steps):
                next_x = self.player_x + step_dx
                if not self.is_wall(next_x, self.player_y):
                    self.player_x = next_x
                    moved = True
                next_y = self.player_y + step_dy
                if not self.is_wall(self.player_x, next_y):
                    self.player_y = next_y
                    moved = True
            if moved:
                self.last_move_vector = norm_dir
        self.last_dash_time = current_time
        return moved

    def handle_shooting(self, shoot_requested: bool, current_time: float) -> bool:
        if not shoot_requested or self.menu_open:
            return False
        if (current_time - self.last_shot_time) < tuning.PROJECTILE_COOLDOWN:
            return False
        combat.spawn_projectile(self.projectiles, self.player_x, self.player_y, self.player_angle)
        self.last_shot_time = current_time
        return True

    def handle_enemy_spawns(self, current_time: float) -> bool:
        if (current_time - self.last_enemy_spawn_time) < tuning.ENEMY_SPAWN_INTERVAL:
            return False
        if len(self.enemies) >= tuning.ENEMY_MAX_COUNT:
            return False
        if spawner.spawn_enemy(self.enemies, self.player_x, self.player_y, current_time, self.is_wall):
            self.last_enemy_spawn_time = current_time
            return True
        return False

    def respawn_player(self) -> None:
        logging.info("Player down, respawning at center.")
        self.player_x = settings.MAP_WIDTH / 2 + 0.5
        self.player_y = settings.MAP_HEIGHT / 2 + 0.5
        self.player_angle = 0.0
        self.last_move_vector = (math.cos(self.player_angle), math.sin(self.player_angle))
        self.projectiles.clear()
        self.explosions.clear()
        self.enemies.clear()
        self.player_health = tuning.PLAYER_MAX_HEALTH

    def apply_player_damage(self, amount: int) -> bool:
        previous = self.player_health
        self.player_health = max(0, self.player_health - amount)
        was_hit = self.player_health < previous
        if self.player_health == 0:
            self.respawn_player()
        return was_hit

    def run(self) -> None:
        running = True
        while running:
            delta_time = max(self.clock.get_time(), 1) / 1000.0
            current_time = pygame.time.get_ticks() / 1000.0
            activity_detected = False
            shoot_requested = False
            dash_requested = False
            move_direction = (0.0, 0.0)

            slider_bar_rect, slider_handle_rect = menu.compute_slider_rects(self.slider_value)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_CTRL:
                        if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                            if self._adjust_minimap_zoom(-settings.MINIMAP_ZOOM_STEP):
                                activity_detected = True
                            continue
                        if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                            if self._adjust_minimap_zoom(settings.MINIMAP_ZOOM_STEP):
                                activity_detected = True
                            continue
                    activity_detected = True
                    if event.key == pygame.K_ESCAPE:
                        self.menu_open = menu.set_menu_state(not self.menu_open)
                        self.slider_dragging = False
                    elif event.key == pygame.K_e and not self.menu_open:
                        shoot_requested = True
                    elif event.key == pygame.K_q and not self.menu_open:
                        dash_requested = True
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        activity_detected = True
                        if self.hamburger_rect.collidepoint(event.pos):
                            self.menu_open = menu.set_menu_state(not self.menu_open)
                            self.slider_dragging = False
                        elif self.menu_open and slider_handle_rect.collidepoint(event.pos):
                            self.slider_dragging = True
                        elif self.menu_open and slider_bar_rect.collidepoint(event.pos):
                            self.slider_dragging = True
                            rel_x = event.pos[0] - slider_bar_rect.x
                            self.slider_value = max(0.0, min(1.0, rel_x / slider_bar_rect.width))
                            self.mouse_sensitivity = self._compute_mouse_sensitivity()
                            slider_bar_rect, slider_handle_rect = menu.compute_slider_rects(self.slider_value)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.slider_dragging = False
                elif event.type == pygame.MOUSEMOTION and self.slider_dragging and self.menu_open:
                    activity_detected = True
                    rel_x = event.pos[0] - slider_bar_rect.x
                    self.slider_value = max(0.0, min(1.0, rel_x / slider_bar_rect.width))
                    self.mouse_sensitivity = self._compute_mouse_sensitivity()
                    slider_bar_rect, slider_handle_rect = menu.compute_slider_rects(self.slider_value)

            keys = pygame.key.get_pressed()
            movement_happened = False
            if self.menu_open:
                pygame.mouse.get_rel()
            else:
                move_speed = 3.2 * delta_time
                if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                    move_speed *= 1.5

                sin_a = math.sin(self.player_angle)
                cos_a = math.cos(self.player_angle)

                move_input_x = 0.0
                move_input_y = 0.0

                if keys[pygame.K_w]:
                    move_input_x += cos_a
                    move_input_y += sin_a
                if keys[pygame.K_s]:
                    move_input_x -= cos_a
                    move_input_y -= sin_a
                if keys[pygame.K_a]:
                    move_input_x += sin_a
                    move_input_y -= cos_a
                if keys[pygame.K_d]:
                    move_input_x -= sin_a
                    move_input_y += cos_a

                move_length = math.hypot(move_input_x, move_input_y)
                if move_length > 0.0:
                    dir_x = move_input_x / move_length
                    dir_y = move_input_y / move_length
                    move_direction = (dir_x, dir_y)
                    move_dx = dir_x * move_speed
                    move_dy = dir_y * move_speed
                    moved = False
                    trial_x = self.player_x + move_dx
                    if not self.is_wall(trial_x, self.player_y):
                        self.player_x = trial_x
                        moved = True
                    trial_y = self.player_y + move_dy
                    if not self.is_wall(self.player_x, trial_y):
                        self.player_y = trial_y
                        moved = True
                    if moved:
                        movement_happened = True
                        self.last_move_vector = move_direction
                    activity_detected = True

                rotation_speed = 1.5 * delta_time
                if keys[pygame.K_LEFT]:
                    self.player_angle -= rotation_speed
                    movement_happened = True
                    activity_detected = True
                if keys[pygame.K_RIGHT]:
                    self.player_angle += rotation_speed
                    movement_happened = True
                    activity_detected = True

                mouse_dx, _ = pygame.mouse.get_rel()
                if mouse_dx:
                    self.player_angle += mouse_dx * self.mouse_sensitivity
                    movement_happened = True
                    activity_detected = True

                self.player_angle %= 2 * math.pi

            dash_result = self.handle_dash(dash_requested, move_direction, current_time)
            shoot_result = self.handle_shooting(shoot_requested, current_time)
            spawn_result = self.handle_enemy_spawns(current_time)
            enemy_activity = ai.update_enemies(
                self.enemies,
                (self.player_x, self.player_y),
                delta_time,
                current_time,
                self.is_wall,
                lambda pos, ang: combat.spawn_projectile(
                    self.projectiles,
                    pos[0],
                    pos[1],
                    ang,
                    owner="enemy",
                    speed=tuning.ENEMY_PROJECTILE_SPEED,
                ),
            )
            if dash_result or shoot_result or spawn_result or enemy_activity:
                activity_detected = True

            damage_events: list[bool] = []
            self.projectiles, enemies_hit = combat.update_projectiles(
                self.projectiles,
                self.explosions,
                self.enemies,
                delta_time,
                current_time,
                self.is_wall,
                (self.player_x, self.player_y),
                tuning.PLAYER_HIT_RADIUS,
                lambda: damage_events.append(self.apply_player_damage(tuning.ENEMY_PROJECTILE_DAMAGE)),
            )
            if any(damage_events):
                activity_detected = True

            if enemies_hit:
                for enemy in enemies_hit:
                    if enemy in self.enemies:
                        self.enemies.remove(enemy)
                activity_detected = True

            self.explosions = [exp for exp in self.explosions if current_time - exp["start"] < tuning.EXPLOSION_DURATION]
            if self.projectiles or self.explosions:
                activity_detected = True

            if movement_happened or self.slider_dragging:
                activity_detected = True

            raycast.draw_world(self.screen, self.player_x, self.player_y, self.player_angle)
            raycast.draw_enemies(
                self.screen,
                self.player_x,
                self.player_y,
                self.player_angle,
                self.enemies,
                current_time,
                self.enemy_texture,
            )
            raycast.draw_projectiles(
                self.screen,
                self.player_x,
                self.player_y,
                self.player_angle,
                self.projectiles,
                self.explosions,
                current_time,
                self.fire_sprites,
            )
            raycast.draw_minimap(
                self.screen,
                self.player_x,
                self.player_y,
                self.player_angle,
                self.minimap_base,
                self.minimap_overlay,
                self.projectiles,
                self.explosions,
                self.enemies,
                zoom=self.minimap_zoom,
            )

            hamburger_hovered = self.hamburger_rect.collidepoint(pygame.mouse.get_pos())
            menu.draw_hamburger(self.screen, hamburger_hovered, self.menu_open)

            fps = self.clock.get_fps()
            fps_value = int(fps) if fps else 0
            fps_text = self.font.render(f"FPS: {fps_value}", True, (235, 235, 235))
            self.screen.blit(fps_text, (settings.WIDTH - 120, 20))

            if self.menu_open:
                menu.draw_menu(
                    self.screen,
                    slider_bar_rect,
                    slider_handle_rect,
                    self.mouse_sensitivity,
                    self.font,
                    self.title_font,
                )
            else:
                menu.draw_crosshair(self.screen)
            hud.draw_health_bar(self.screen, self.player_health, tuning.PLAYER_MAX_HEALTH)

            if current_time - self.last_fps_log >= 1.0:
                logging.info("FPS: %d (target %d)", fps_value, self.current_target_fps)
                self.last_fps_log = current_time

            pygame.display.flip()

            if activity_detected:
                self.last_activity_time = current_time

            idle_duration = current_time - self.last_activity_time
            if idle_duration >= settings.DEEP_IDLE_THRESHOLD:
                desired_fps = settings.TARGET_FPS_DEEP_IDLE
            elif idle_duration >= settings.IDLE_THRESHOLD:
                desired_fps = settings.TARGET_FPS_IDLE
            else:
                desired_fps = settings.TARGET_FPS_ACTIVE

            if desired_fps != self.current_target_fps:
                logging.info("Adjusting target FPS to %d (idle %.2fs)", desired_fps, idle_duration)
                self.current_target_fps = desired_fps

            self.clock.tick(self.current_target_fps)

        pygame.quit()
        sys.exit()
