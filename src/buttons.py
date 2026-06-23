"""
buttons.py - Configurations and event handlers for interactive buttons and sliders.
"""

import cv2
import sys
from src.utils import MODE_SHARED, MODE_SPLIT

# Button Bounding Box Constants (Top Toolbar y: 10 to 36, Height: 26px - 35% smaller)
BUTTONS_SHARED = [
    {"x1": 274, "y1": 10, "x2": 334, "y2": 36, "label": "RED",        "type": "color",  "val": (0, 0, 255)},
    {"x1": 342, "y1": 10, "x2": 402, "y2": 36, "label": "GREEN",      "type": "color",  "val": (0, 255, 0)},
    {"x1": 410, "y1": 10, "x2": 470, "y2": 36, "label": "BLUE",       "type": "color",  "val": (255, 0, 0)},
    {"x1": 478, "y1": 10, "x2": 538, "y2": 36, "label": "YELLOW",     "type": "color",  "val": (0, 255, 255)},
    {"x1": 546, "y1": 10, "x2": 606, "y2": 36, "label": "ERASER",     "type": "toggle", "val": "eraser"},
    {"x1": 614, "y1": 10, "x2": 674, "y2": 36, "label": "UNDO",       "type": "action", "val": "undo"},
    {"x1": 682, "y1": 10, "x2": 742, "y2": 36, "label": "REDO",       "type": "action", "val": "redo"},
    {"x1": 750, "y1": 10, "x2": 810, "y2": 36, "label": "CLEAR",      "type": "action", "val": "clear"},
    {"x1": 818, "y1": 10, "x2": 908, "y2": 36, "label": "SPLIT MODE", "type": "action", "val": "toggle_mode"},
    {"x1": 916, "y1": 10, "x2": 1006, "y2": 36, "label": "FULLSCREEN", "type": "action", "val": "fullscreen"},
    {"x1": 1014, "y1": 10, "x2": 1074, "y2": 36, "label": "EXIT",       "type": "action", "val": "exit"},
]

BUTTONS_SPLIT_P1 = [
    {"x1": 90,  "y1": 10, "x2": 130, "y2": 36, "label": "RED",        "type": "color",  "val": (0, 0, 255),   "hand": "Left"},
    {"x1": 135, "y1": 10, "x2": 175, "y2": 36, "label": "GREEN",      "type": "color",  "val": (0, 255, 0),   "hand": "Left"},
    {"x1": 180, "y1": 10, "x2": 220, "y2": 36, "label": "BLUE",       "type": "color",  "val": (255, 0, 0),   "hand": "Left"},
    {"x1": 225, "y1": 10, "x2": 265, "y2": 36, "label": "YELLOW",     "type": "color",  "val": (0, 255, 255), "hand": "Left"},
    {"x1": 270, "y1": 10, "x2": 325, "y2": 36, "label": "ERASER",     "type": "toggle", "val": "eraser",       "hand": "Left"},
    {"x1": 330, "y1": 10, "x2": 370, "y2": 36, "label": "UNDO",       "type": "action", "val": "undo",         "hand": "Left"},
    {"x1": 375, "y1": 10, "x2": 415, "y2": 36, "label": "REDO",       "type": "action", "val": "redo",         "hand": "Left"},
    {"x1": 420, "y1": 10, "x2": 460, "y2": 36, "label": "CLEAR",      "type": "action", "val": "clear",        "hand": "Left"},
    {"x1": 465, "y1": 10, "x2": 505, "y2": 36, "label": "SHARED",     "type": "action", "val": "toggle_mode",   "hand": "Left"},
    {"x1": 510, "y1": 10, "x2": 550, "y2": 36, "label": "FS",         "type": "action", "val": "fullscreen",    "hand": "Left"},
    {"x1": 555, "y1": 10, "x2": 595, "y2": 36, "label": "EXIT",       "type": "action", "val": "exit",          "hand": "Left"},
]

BUTTONS_SPLIT_P2 = [
    {"x1": 685, "y1": 10, "x2": 725, "y2": 36, "label": "EXIT",       "type": "action", "val": "exit",          "hand": "Right"},
    {"x1": 730, "y1": 10, "x2": 770, "y2": 36, "label": "FS",         "type": "action", "val": "fullscreen",    "hand": "Right"},
    {"x1": 775, "y1": 10, "x2": 815, "y2": 36, "label": "SHARED",     "type": "action", "val": "toggle_mode",   "hand": "Right"},
    {"x1": 820, "y1": 10, "x2": 860, "y2": 36, "label": "RED",        "type": "color",  "val": (0, 0, 255),   "hand": "Right"},
    {"x1": 865, "y1": 10, "x2": 905, "y2": 36, "label": "GREEN",      "type": "color",  "val": (0, 255, 0),   "hand": "Right"},
    {"x1": 910, "y1": 10, "x2": 950, "y2": 36, "label": "BLUE",       "type": "color",  "val": (255, 0, 0),   "hand": "Right"},
    {"x1": 955, "y1": 10, "x2": 995, "y2": 36, "label": "YELLOW",     "type": "color",  "val": (0, 255, 255), "hand": "Right"},
    {"x1": 1000, "y1": 10, "x2": 1055, "y2": 36, "label": "ERASER",     "type": "toggle", "val": "eraser",       "hand": "Right"},
    {"x1": 1060, "y1": 10, "x2": 1100, "y2": 36, "label": "UNDO",       "type": "action", "val": "undo",         "hand": "Right"},
    {"x1": 1105, "y1": 10, "x2": 1145, "y2": 36, "label": "REDO",       "type": "action", "val": "redo",         "hand": "Right"},
    {"x1": 1150, "y1": 10, "x2": 1190, "y2": 36, "label": "CLEAR",      "type": "action", "val": "clear",        "hand": "Right"},
]

def get_active_buttons(mode):
    """Returns the list of buttons active in the current screen mode."""
    if mode == MODE_SHARED:
        return BUTTONS_SHARED
    else:
        return BUTTONS_SPLIT_P1 + BUTTONS_SPLIT_P2

def trigger_button_action(btn, hand_label, canvas_manager, app_context):
    """Executes settings changes or history operations based on button configurations."""
    if btn["type"] == "color":
        canvas_manager.set_brush_color(btn["val"], hand_label)
        print(f"[{hand_label}] Color set to {btn['label']}")
    elif btn["type"] == "toggle":
        if btn["val"] == "eraser":
            current_eraser = canvas_manager.get_eraser_mode(hand_label)
            canvas_manager.set_eraser_mode(not current_eraser, hand_label)
            print(f"[{hand_label}] Eraser toggled to {not current_eraser}")
    elif btn["type"] == "action":
        if btn["val"] == "undo":
            canvas_manager.undo(hand_label)
            print(f"[{hand_label}] Undo triggered")
        elif btn["val"] == "redo":
            canvas_manager.redo(hand_label)
            print(f"[{hand_label}] Redo triggered")
        elif btn["val"] == "clear":
            canvas_manager.clear(hand_label)
            print(f"[{hand_label}] Clear triggered")
        elif btn["val"] == "toggle_mode":
            new_mode = MODE_SPLIT if canvas_manager.mode == MODE_SHARED else MODE_SHARED
            canvas_manager.set_mode(new_mode)
            print(f"Mode switched to {new_mode}")
        elif btn["val"] == "fullscreen":
            app_context.toggle_fullscreen()
            print("Fullscreen toggled")
        elif btn["val"] == "exit":
            print("Exit button clicked. Shutting down...")
            app_context.should_exit = True

def mouse_click_handler(event, x, y, flags, param):
    """
    Mouse callback to trigger top-bar button operations (clicks) and bottom status bar sliders.
    Supports clicking and dragging on sliders.
    """
    app_context = param
    canvas_manager = app_context.canvas_manager
    
    if event == cv2.EVENT_LBUTTONDOWN or (event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON)):
        if canvas_manager.mode == MODE_SHARED:
            if 1000 <= x <= 1150 and 685 <= y <= 710:
                new_thickness = max(2, min(50, 2 + int((x - 1000) / 150 * 48))) # max 50px
                canvas_manager.set_brush_thickness(new_thickness)
                return
        else:
            if 420 <= x <= 570 and 685 <= y <= 710:
                new_thickness = max(2, min(50, 2 + int((x - 420) / 150 * 48))) # max 50px
                canvas_manager.set_brush_thickness(new_thickness, "Left")
                return
            elif 1050 <= x <= 1200 and 685 <= y <= 710:
                new_thickness = max(2, min(50, 2 + int((x - 1050) / 150 * 48))) # max 50px
                canvas_manager.set_brush_thickness(new_thickness, "Right")
                return

    if event == cv2.EVENT_LBUTTONDOWN:
        buttons = get_active_buttons(canvas_manager.mode)
        for btn in buttons:
            if btn["x1"] <= x <= btn["x2"] and btn["y1"] <= y <= btn["y2"]:
                if canvas_manager.mode == MODE_SPLIT:
                    hand_label = btn.get("hand", "Left" if x < 640 else "Right")
                else:
                    hand_label = "Left"
                trigger_button_action(btn, hand_label, canvas_manager, app_context)
                break
