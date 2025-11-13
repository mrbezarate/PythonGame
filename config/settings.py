"""Screen, color, and runtime tuning constants."""

WIDTH = 1200
HEIGHT = 800
HALF_WIDTH = WIDTH // 2
HALF_HEIGHT = HEIGHT // 2

BG_COLOR = (22, 22, 28)
FLOOR_COLOR = (32, 32, 38)

TITLE_FONT_SIZE = 32
TEXT_FONT_SIZE = 24

# Target FPS behaviour depending on player activity (seconds since last action)
TARGET_FPS_ACTIVE = 240
TARGET_FPS_IDLE = 30
TARGET_FPS_DEEP_IDLE = 10
IDLE_THRESHOLD = 2.0
DEEP_IDLE_THRESHOLD = 5.0

# Menu widgets (pygame.Rect values created lazily after pygame.init())
HAMBURGER_RECT = (20, 20, 46, 34)
SETTINGS_RECT = (WIDTH // 2 - 220, HEIGHT // 2 - 180, 440, 320)

# Mouse sensitivity slider range
SENSITIVITY_MIN = 0.0015
SENSITIVITY_MAX = 0.008
DEFAULT_SLIDER_VALUE = 0.35

# World / minimap settings
MAP_WIDTH = 516
MAP_HEIGHT = 516
MINIMAP_SIZE = 240
MAP_OFFSET = (WIDTH - MINIMAP_SIZE - 20, HEIGHT - MINIMAP_SIZE - 20)
MINIMAP_TEXTURE_SCALE = 2  # pixels per tile in the high-res minimap texture
MINIMAP_DEFAULT_ZOOM = 70  # tiles visible across the minimap view
MINIMAP_MIN_ZOOM = 30
MINIMAP_MAX_ZOOM = 140
MINIMAP_ZOOM_STEP = 10
