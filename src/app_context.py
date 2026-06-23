"""
app_context.py - Handles application-wide context such as fullscreen mode state and configuration.
"""

import cv2

class AppContext:
    def __init__(self, canvas_manager, window_name):
        self.canvas_manager = canvas_manager
        self.window_name = window_name
        self.is_fullscreen = False
        self.should_exit = False

    def toggle_fullscreen(self):
        """Toggles fullscreen state for the primary window."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
