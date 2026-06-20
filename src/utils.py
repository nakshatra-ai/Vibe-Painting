"""
utils.py - Global constants, settings, and utility definitions.
"""

# Webcam Configuration
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
CAMERA_INDEX = 0

# Colors (BGR format for OpenCV)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (0, 0, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (255, 0, 0)
COLOR_YELLOW = (0, 255, 255)
COLOR_PURPLE = (255, 0, 255)
COLOR_CYAN = (255, 255, 0)
COLOR_ORANGE = (0, 165, 255)

# Selection Lock Configurations
HOVER_LOCK_DURATION = 0.25  # seconds (reduced from 0.5s for faster response)

# Coordinate Smoothing (Exponential Moving Average Filter)
EMA_ALPHA = 0.55  # Increased from 0.35 for lower latency and more responsive tracking

# Gestures Definitions
GESTURE_IDLE = "Idle"
GESTURE_DRAW = "Drawing"
GESTURE_ERASE = "Eraser"
GESTURE_PINCH = "Pinch"

# Operating Modes
MODE_SHARED = "Shared"
MODE_SPLIT = "Split"

# UI Theme Config (Hex colors for CustomTkinter)
THEME_BG = "#1A1A1A"
THEME_SIDEBAR_BG = "#2B2B2B"
THEME_ACCENT = "#1F6AA5"
THEME_TEXT = "#E5E5E5"
