"""
main.py - Entry point for Phase 2: Drawing Engine and Canvas Verification.
Implements the main video loop, gestural drawing engine, mouse callbacks, and top bar controls.
Supports runtime mode switching and is fully optimized for stability, usability, and modern minimal UI.
"""

import cv2
import time
import numpy as np
from src.hand_tracker import HandTracker
from src.canvas_manager import CanvasManager
from src.utils import (
    FRAME_WIDTH,
    FRAME_HEIGHT,
    CAMERA_INDEX,
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_PURPLE,
    GESTURE_DRAW,
    GESTURE_ERASE,
    GESTURE_IDLE,
    GESTURE_PINCH,
    MODE_SHARED,
    MODE_SPLIT,
    HOVER_LOCK_DURATION
)

class AppContext:
    def __init__(self, canvas_manager, window_name):
        self.canvas_manager = canvas_manager
        self.window_name = window_name
        self.is_fullscreen = False

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

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
    if mode == MODE_SHARED:
        return BUTTONS_SHARED
    else:
        return BUTTONS_SPLIT_P1 + BUTTONS_SPLIT_P2

def trigger_button_action(btn, hand_label, canvas_manager, app_context):
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
            import sys
            print("Exit button clicked. Shutting down...")
            sys.exit(0)

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

def draw_gui_overlay(frame, canvas_manager, hand_states=None):
    """
    Renders sleek, semi-transparent top toolbar and bottom status bar panel.
    """
    h, w, _ = frame.shape
    
    # 1. Glassmorphic Background Bars
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 45), (20, 20, 20), cv2.FILLED)      # Top bar
    cv2.rectangle(overlay, (0, 675), (w, h), (20, 20, 20), cv2.FILLED)    # Bottom bar
    cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
    
    # Slate border lines
    cv2.line(frame, (0, 45), (w, 45), (45, 45, 45), 1, cv2.LINE_AA)
    cv2.line(frame, (0, 675), (w, 675), (45, 45, 45), 1, cv2.LINE_AA)
    
    # 2. Draw Split-Screen Divider Line (1px slate divider)
    if canvas_manager.mode == MODE_SPLIT:
        cv2.line(frame, (w // 2, 45), (w // 2, 675), (80, 80, 80), 1, cv2.LINE_AA)
        cv2.putText(frame, "PLAYER 1", (10, 660), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 0, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "PLAYER 2", (w // 2 + 10, 660), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 0), 1, cv2.LINE_AA)
    
    # Helper to map raw state string to user-friendly mode label
    def get_mode_label(state):
        if state == GESTURE_DRAW:
            return "DRAW MODE"
        elif state == GESTURE_ERASE:
            return "ERASER MODE"
        elif state == GESTURE_PINCH:
            return "BRUSH SIZE MODE"
        else:
            return "PAUSE MODE"

    # 3. Draw Buttons
    buttons = get_active_buttons(canvas_manager.mode)
    for btn in buttons:
        is_active = False
        btn_color = (40, 40, 40)
        text_color = COLOR_WHITE
        
        hand_label = btn.get("hand", "Left")
        
        if btn["type"] == "color":
            btn_color = btn["val"]
            active_color = canvas_manager.get_color(hand_label)
            is_eraser = canvas_manager.get_eraser_mode(hand_label)
            if active_color == btn["val"] and not is_eraser:
                is_active = True
        elif btn["type"] == "toggle" and btn["val"] == "eraser":
            is_eraser = canvas_manager.get_eraser_mode(hand_label)
            if is_eraser:
                is_active = True
                btn_color = (240, 240, 240)
                text_color = COLOR_BLACK
        
        # Draw button box
        cv2.rectangle(frame, (btn["x1"], btn["y1"]), (btn["x2"], btn["y2"]), btn_color, cv2.FILLED)
        
        # Border
        border_color = (230, 230, 230) if is_active else (80, 80, 80)
        border_thickness = 2 if is_active else 1
        cv2.rectangle(frame, (btn["x1"], btn["y1"]), (btn["x2"], btn["y2"]), border_color, border_thickness, cv2.LINE_AA)
        
        # Label
        font_scale = 0.38
        thickness = 1
        (txt_w, txt_h), _ = cv2.getTextSize(btn["label"], cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        text_x = btn["x1"] + (btn["x2"] - btn["x1"] - txt_w) // 2
        text_y = btn["y1"] + (btn["y2"] - btn["y1"] + txt_h) // 2
        cv2.putText(frame, btn["label"], (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, thickness, cv2.LINE_AA)

    # 4. Draw Integrated Bottom Status Bar
    font_scale = 0.45
    text_color = (190, 190, 190)
    
    if canvas_manager.mode == MODE_SHARED:
        l_state = hand_states.get("Left", GESTURE_IDLE) if hand_states else GESTURE_IDLE
        r_state = hand_states.get("Right", GESTURE_IDLE) if hand_states else GESTURE_IDLE
        
        l_label = get_mode_label(l_state)
        r_label = get_mode_label(r_state)
        
        l_color = COLOR_GREEN if l_state == GESTURE_DRAW else ((0, 165, 255) if l_state == GESTURE_ERASE else ((255, 0, 255) if l_state == GESTURE_PINCH else (180, 180, 180)))
        r_color = COLOR_GREEN if r_state == GESTURE_DRAW else ((0, 165, 255) if r_state == GESTURE_ERASE else ((255, 255, 0) if r_state == GESTURE_PINCH else (180, 180, 180)))
        
        cv2.putText(frame, "L-Hand: ", (20, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1, cv2.LINE_AA)
        cv2.putText(frame, l_label, (85, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, l_color, 1, cv2.LINE_AA)
        
        cv2.putText(frame, "R-Hand: ", (220, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1, cv2.LINE_AA)
        cv2.putText(frame, r_label, (285, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, r_color, 1, cv2.LINE_AA)
        
        brush_desc = "Eraser" if canvas_manager.is_eraser else "Brush"
        cv2.putText(frame, f"Tool: {brush_desc}", (460, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1, cv2.LINE_AA)
        
        preview_color = (255, 255, 255) if canvas_manager.is_eraser else canvas_manager.active_color
        cv2.circle(frame, (580, 698), 8, preview_color, cv2.FILLED)
        cv2.circle(frame, (580, 698), 9, COLOR_WHITE, 1, cv2.LINE_AA)
        
        # Shared Slider (x: 1000 -> 1150)
        cv2.putText(frame, f"Size: {canvas_manager.active_thickness} px", (880, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1, cv2.LINE_AA)
        cv2.line(frame, (1000, 698), (1150, 698), (60, 60, 60), 4, cv2.LINE_AA)
        fill_x = 1000 + int(((canvas_manager.active_thickness - 2) / 48) * 150)
        cv2.line(frame, (1000, 698), (fill_x, 698), (0, 165, 255), 4, cv2.LINE_AA)
        cv2.circle(frame, (fill_x, 698), 6, COLOR_WHITE, cv2.FILLED)
        cv2.circle(frame, (fill_x, 698), 7, (40, 40, 40), 1, cv2.LINE_AA)
    else:
        # PLAYER 1 (Left side)
        p1_state = hand_states.get("Left", GESTURE_IDLE) if hand_states else GESTURE_IDLE
        p1_label = get_mode_label(p1_state)
        p1_color = COLOR_GREEN if p1_state == GESTURE_DRAW else ((0, 165, 255) if p1_state == GESTURE_ERASE else ((255, 0, 255) if p1_state == GESTURE_PINCH else (180, 180, 180)))
        p1_size = canvas_manager.get_thickness("Left")
        
        cv2.putText(frame, "P1 Hand: ", (20, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1, cv2.LINE_AA)
        cv2.putText(frame, p1_label, (90, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, p1_color, 1, cv2.LINE_AA)
        
        p1_eraser = canvas_manager.get_eraser_mode("Left")
        p1_preview_color = (255, 255, 255) if p1_eraser else canvas_manager.get_color("Left")
        cv2.circle(frame, (230, 698), 7, p1_preview_color, cv2.FILLED)
        cv2.circle(frame, (230, 698), 8, COLOR_WHITE, 1, cv2.LINE_AA)
        
        # P1 Slider (x: 420 -> 570)
        cv2.putText(frame, f"Size: {p1_size} px", (310, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1, cv2.LINE_AA)
        cv2.line(frame, (420, 698), (570, 698), (60, 60, 60), 4, cv2.LINE_AA)
        p1_fill_x = 420 + int(((p1_size - 2) / 48) * 150)
        cv2.line(frame, (420, 698), (p1_fill_x, 698), (255, 0, 255), 4, cv2.LINE_AA)
        cv2.circle(frame, (p1_fill_x, 698), 6, COLOR_WHITE, cv2.FILLED)
        cv2.circle(frame, (p1_fill_x, 698), 7, (40, 40, 40), 1, cv2.LINE_AA)
        
        # PLAYER 2 (Right side)
        p2_state = hand_states.get("Right", GESTURE_IDLE) if hand_states else GESTURE_IDLE
        p2_label = get_mode_label(p2_state)
        p2_color = COLOR_GREEN if p2_state == GESTURE_DRAW else ((0, 165, 255) if p2_state == GESTURE_ERASE else ((255, 255, 0) if p2_state == GESTURE_PINCH else (180, 180, 180)))
        p2_size = canvas_manager.get_thickness("Right")
        
        cv2.putText(frame, "P2 Hand: ", (660, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1, cv2.LINE_AA)
        cv2.putText(frame, p2_label, (730, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, p2_color, 1, cv2.LINE_AA)
        
        p2_eraser = canvas_manager.get_eraser_mode("Right")
        p2_preview_color = (255, 255, 255) if p2_eraser else canvas_manager.get_color("Right")
        cv2.circle(frame, (870, 698), 7, p2_preview_color, cv2.FILLED)
        cv2.circle(frame, (870, 698), 8, COLOR_WHITE, 1, cv2.LINE_AA)
        
        # P2 Slider (x: 1050 -> 1200)
        cv2.putText(frame, f"Size: {p2_size} px", (940, 702), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1, cv2.LINE_AA)
        cv2.line(frame, (1050, 698), (1200, 698), (60, 60, 60), 4, cv2.LINE_AA)
        p2_fill_x = 1050 + int(((p2_size - 2) / 48) * 150)
        cv2.line(frame, (1050, 698), (p2_fill_x, 698), (255, 255, 0), 4, cv2.LINE_AA)
        cv2.circle(frame, (p2_fill_x, 698), 6, COLOR_WHITE, cv2.FILLED)
        cv2.circle(frame, (p2_fill_x, 698), 7, (40, 40, 40), 1, cv2.LINE_AA)

def draw_startup_message(window_name, message, color=(255, 255, 255)):
    """
    Renders temporary loading feedback or startup error card on screen.
    """
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame.fill(20)  # Modern dark slate background
    
    cv2.putText(frame, "AIR CANVAS PRO", (450, 280), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 165, 255), 3, cv2.LINE_AA)
    
    font_scale = 0.65
    thickness = 1
    (txt_w, txt_h), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    x = (1280 - txt_w) // 2
    cv2.putText(frame, message, (x, 400), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness, cv2.LINE_AA)
    
    cv2.imshow(window_name, frame)
    cv2.waitKey(1)

def main():
    window_name = "Air Canvas Pro - Dual Hand Edition"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_KEEPRATIO)
    
    # Start in Fullscreen mode by default
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    cap = None
    tracker = None
    
    try:
        # 1. Initialize Webcam with visual loading feedback
        draw_startup_message(window_name, "Initializing Camera...")
        
        cap = cv2.VideoCapture(CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        
        success = False
        if cap.isOpened():
            success, frame = cap.read()
            if not success:
                for warmup in range(10):
                    time.sleep(0.05)
                    success, frame = cap.read()
                    if success:
                        break
                        
        # If the default camera failed, search for any working index [1, 2, 0, 3]
        if not success:
            print(f"Webcam index {CAMERA_INDEX} failed. Searching for fallback camera...")
            cap.release()
            found_cam = False
            for alt_idx in [1, 2, 0, 3]:
                if alt_idx == CAMERA_INDEX and alt_idx != 0:
                    continue
                cap = cv2.VideoCapture(alt_idx)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                if cap.isOpened():
                    success = False
                    for warmup in range(10):
                        time.sleep(0.05)
                        success, frame = cap.read()
                        if success:
                            break
                    if success:
                        print(f"Successfully connected to fallback camera at index {alt_idx}!")
                        found_cam = True
                        break
                cap.release()
                
            if not found_cam:
                draw_startup_message(window_name, "Camera not detected. Press any key to exit.", (0, 0, 255))
                for _ in range(40):
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                        break
                    if cv2.waitKey(100) != -1:
                        break
                return

        # 2. Initialize Hand Tracker with visual loading feedback
        draw_startup_message(window_name, "Loading Hand Tracking...")
        try:
            tracker = HandTracker(max_hands=2, detection_confidence=0.7, tracking_confidence=0.7)
        except Exception as e:
            print(f"Hand tracking initialization failed: {e}")
            draw_startup_message(window_name, "Hand tracking initialization failed. Press any key to exit.", (0, 0, 255))
            for _ in range(40):
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
                if cv2.waitKey(100) != -1:
                    break
            return
            
        canvas_manager = CanvasManager(width=FRAME_WIDTH, height=FRAME_HEIGHT)

        app_context = AppContext(canvas_manager, window_name)
        cv2.setMouseCallback(window_name, mouse_click_handler, app_context)
        app_context.is_fullscreen = True

        # State tracking maps
        prev_gestures = {"Left": GESTURE_IDLE, "Right": GESTURE_IDLE}
        prev_in_ui_zone = {"Left": False, "Right": False}
        hand_lost_times = {"Left": None, "Right": None}
        last_tracked_positions = {"Left": None, "Right": None}
        velocities = {"Left": (0.0, 0.0), "Right": (0.0, 0.0)}

        # Gesture confirmation debouncer parameters
        consecutive_counts = {"Left": 0, "Right": 0}
        pending_gestures = {"Left": GESTURE_IDLE, "Right": GESTURE_IDLE}
        current_states = {"Left": GESTURE_IDLE, "Right": GESTURE_IDLE}

        # Pinch gesture tracking states
        start_pinch_x = {"Left": None, "Right": None}
        start_brush_size = {"Left": 10, "Right": 10}
        smooth_brush_size = {"Left": 10.0, "Right": 10.0}

        # Track hover selection states for buttons
        hover_states = {
            "Left": {"btn": None, "time": 0.0, "triggered": False},
            "Right": {"btn": None, "time": 0.0, "triggered": False}
        }

        prev_time = time.time()
        
        print("--------------------------------------------------")
        print("Air Canvas Pro - Gesture Redesign Active")
        print("--------------------------------------------------")
        print("Gesture Controls:")
        print("  - Index Finger Only : DRAW MODE")
        print("  - Closed Fist       : ERASER MODE (Displays large cursor)")
        print("  - Open Palm         : PAUSE MODE (Cursor visible, no strokes)")
        print("  - Thumb + Index     : BRUSH SIZE MODE (Move Right/Left to change size)")
        print("--------------------------------------------------")

        while True:
            # Check if native window closed (Alt+F4 / 'X' click)
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                print("Window closed by user. Exiting...")
                break
                
            curr_time = time.time()
            dt = curr_time - prev_time
            
            success, frame = cap.read()
            if not success:
                # Allow camera to warm up/initialize on some Windows hardware (retry up to 20 times)
                for warmup in range(20):
                    time.sleep(0.05)
                    success, frame = cap.read()
                    if success:
                        break
                if not success:
                    print("Failed to capture frame after retry. Exiting...")
                    break
                
            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            frame = cv2.flip(frame, 1)
            
            # 4. Hand Detection & Gesture Mapping
            frame = tracker.find_hands(frame, draw=True)
            hands_payloads = tracker.find_position(frame)
            
            # Build map of detected hands with spatial mappings in Split Screen Mode
            detected_hands = {}
            for payload in hands_payloads:
                if canvas_manager.mode == MODE_SPLIT:
                    lm_list = payload["lm_list"]
                    raw_index_x = lm_list[8][1]
                    player_label = "Left" if raw_index_x < 640 else "Right"
                else:
                    player_label = payload["label"]
                detected_hands[player_label] = payload
            
            hand_states = {"Left": GESTURE_IDLE, "Right": GESTURE_IDLE}
            cursors_to_render = {}
            
            for hand_label in ["Left", "Right"]:
                is_detected = hand_label in detected_hands
                index_x, index_y = 0, 0
                raw_gesture = GESTURE_IDLE
                
                if is_detected:
                    hand_lost_times[hand_label] = None
                    
                    payload = detected_hands[hand_label]
                    lm_list = payload["lm_list"]
                    raw_gesture = tracker.detect_gesture(lm_list, payload["label"])
                    
                    raw_index_x, raw_index_y = lm_list[8][1], lm_list[8][2]
                    index_x, index_y = tracker.get_smoothed_coordinates(raw_index_x, raw_index_y, hand_label)
                    
                    if last_tracked_positions[hand_label] is not None and dt > 0:
                        prev_pos = last_tracked_positions[hand_label]
                        vx = (index_x - prev_pos[0]) / dt
                        vy = (index_y - prev_pos[1]) / dt
                        velocities[hand_label] = (vx, vy)
                        
                    last_tracked_positions[hand_label] = (index_x, index_y)
                else:
                    raw_gesture = GESTURE_IDLE
                    
                # Stabilization State Machine:
                if not is_detected and prev_gestures[hand_label] in [GESTURE_DRAW, GESTURE_ERASE]:
                    if hand_lost_times[hand_label] is None:
                        hand_lost_times[hand_label] = curr_time
                        
                    elapsed_lost = curr_time - hand_lost_times[hand_label]
                    if elapsed_lost <= 0.30:  # 300ms grace window
                        active_gesture = prev_gestures[hand_label]
                        vx, vy = velocities.get(hand_label, (0.0, 0.0))
                        last_pos = last_tracked_positions[hand_label]
                        if last_pos is not None:
                            pred_x = int(last_pos[0] + vx * elapsed_lost)
                            pred_y = int(last_pos[1] + vy * elapsed_lost)
                            pred_x = max(0, min(pred_x, FRAME_WIDTH - 1))
                            pred_y = max(0, min(pred_y, FRAME_HEIGHT - 1))
                            index_x, index_y = pred_x, pred_y
                    else:
                        active_gesture = GESTURE_IDLE
                        current_states[hand_label] = GESTURE_IDLE
                        consecutive_counts[hand_label] = 0
                else:
                    # Apply asymmetric confirmation filters to prevent accidental switches
                    if raw_gesture == current_states[hand_label]:
                        consecutive_counts[hand_label] = 0
                        pending_gestures[hand_label] = raw_gesture
                    else:
                        if raw_gesture == pending_gestures[hand_label]:
                            consecutive_counts[hand_label] += 1
                        else:
                            pending_gestures[hand_label] = raw_gesture
                            consecutive_counts[hand_label] = 1
                            
                        threshold = 8 if current_states[hand_label] == GESTURE_DRAW else 5
                        if consecutive_counts[hand_label] >= threshold:
                            current_states[hand_label] = pending_gestures[hand_label]
                            consecutive_counts[hand_label] = 0
                            
                    active_gesture = current_states[hand_label]
                    
                hand_states[hand_label] = active_gesture
                
                # Suppress drawing inside UI zones (top toolbar y < 45 or bottom status bar y > 675)
                is_in_ui_zone = (index_y < 45 or index_y > 675)
                
                # Gesture State Transitions
                if active_gesture == GESTURE_DRAW and not is_in_ui_zone:
                    if prev_gestures[hand_label] != GESTURE_DRAW or prev_in_ui_zone[hand_label]:
                        canvas_manager.start_stroke(hand_label, force_eraser=False)
                    if index_x > 0 or index_y > 0:
                        canvas_manager.add_point(index_x, index_y, hand_label)
                elif active_gesture == GESTURE_ERASE and not is_in_ui_zone:
                    if prev_gestures[hand_label] != GESTURE_ERASE or prev_in_ui_zone[hand_label]:
                        canvas_manager.start_stroke(hand_label, force_eraser=True)
                    if index_x > 0 or index_y > 0:
                        canvas_manager.add_point(index_x, index_y, hand_label)
                else:
                    if prev_gestures[hand_label] in [GESTURE_DRAW, GESTURE_ERASE] and not prev_in_ui_zone[hand_label]:
                        canvas_manager.end_stroke(hand_label)
                        
                prev_in_ui_zone[hand_label] = is_in_ui_zone
                
                # Pinch gesture brush size adjustment logic
                if active_gesture == GESTURE_PINCH and is_detected:
                    if start_pinch_x[hand_label] is None:
                        start_pinch_x[hand_label] = index_x
                        start_brush_size[hand_label] = canvas_manager.get_thickness(hand_label)
                        smooth_brush_size[hand_label] = float(start_brush_size[hand_label])
                    else:
                        dx = index_x - start_pinch_x[hand_label]
                        target_size = start_brush_size[hand_label] + dx * 0.15
                        target_size = max(2, min(50, target_size))
                        
                        smooth_brush_size[hand_label] = 0.25 * target_size + 0.75 * smooth_brush_size[hand_label]
                        canvas_manager.set_brush_thickness(int(smooth_brush_size[hand_label]), hand_label)
                else:
                    start_pinch_x[hand_label] = None
                        
                # 5. Hover Button & Slider Selection logic inside UI zones (when pointing index finger)
                if is_in_ui_zone and active_gesture == GESTURE_DRAW and (index_x > 0 or index_y > 0):
                    # Slider Real-time hover slider updates
                    if canvas_manager.mode == MODE_SHARED:
                        if 1000 <= index_x <= 1150 and 685 <= index_y <= 710:
                            new_thickness = max(2, min(50, 2 + int((index_x - 1000) / 150 * 48)))
                            canvas_manager.set_brush_thickness(new_thickness)
                    else:
                        if hand_label == "Left" and 420 <= index_x <= 570 and 685 <= index_y <= 710:
                            new_thickness = max(2, min(50, 2 + int((index_x - 420) / 150 * 48)))
                            canvas_manager.set_brush_thickness(new_thickness, "Left")
                        elif hand_label == "Right" and 1050 <= index_x <= 1200 and 685 <= index_y <= 710:
                            new_thickness = max(2, min(50, 2 + int((index_x - 1050) / 150 * 48)))
                            canvas_manager.set_brush_thickness(new_thickness, "Right")
                    
                    # Check button hovers
                    buttons = get_active_buttons(canvas_manager.mode)
                    hovered_btn = None
                    for btn in buttons:
                        if btn["x1"] <= index_x <= btn["x2"] and btn["y1"] <= index_y <= btn["y2"]:
                            if canvas_manager.mode == MODE_SPLIT:
                                if btn.get("hand") == hand_label:
                                    hovered_btn = btn
                                    break
                            else:
                                hovered_btn = btn
                                break
                                
                    h_state = hover_states[hand_label]
                    if hovered_btn is not None:
                        if h_state["btn"] == hovered_btn:
                            if not h_state["triggered"]:
                                h_state["time"] += dt
                                if h_state["time"] >= HOVER_LOCK_DURATION:
                                    trigger_button_action(hovered_btn, hand_label, canvas_manager, app_context)
                                    h_state["triggered"] = True
                        else:
                            h_state["btn"] = hovered_btn
                            h_state["time"] = 0.0
                            h_state["triggered"] = False
                    else:
                        h_state["btn"] = None
                        h_state["time"] = 0.0
                        h_state["triggered"] = False
                else:
                    hover_states[hand_label]["btn"] = None
                    hover_states[hand_label]["time"] = 0.0
                    hover_states[hand_label]["triggered"] = False
     
                # Keep cursor coordinates for rendering overlays
                if is_detected or (active_gesture in [GESTURE_DRAW, GESTURE_ERASE, GESTURE_PINCH] and last_tracked_positions[hand_label] is not None):
                    cx, cy = (index_x, index_y) if (not is_detected and last_tracked_positions[hand_label]) else (index_x, index_y)
                    cursors_to_render[hand_label] = {
                        "cx": cx,
                        "cy": cy,
                        "state": active_gesture
                    }
                    
                prev_gestures[hand_label] = active_gesture
                
            # 6. Composite Drawing Layers
            frame = canvas_manager.composite_frame(frame)
            
            # 7. Render Custom Cursors based on simplified gestures
            for hand_label, cursor in cursors_to_render.items():
                cx, cy = cursor["cx"], cursor["cy"]
                state = cursor["state"]
                
                brush_size = canvas_manager.get_thickness(hand_label)
                cursor_radius = max(5, brush_size // 2)
                is_eraser = canvas_manager.get_eraser_mode(hand_label)
                active_color = canvas_manager.get_color(hand_label)
                
                if hand_label == "Right":
                    border_color = (255, 255, 0)       # Cyan BGR for Right (P2)
                    text_color = (255, 255, 0)
                    label_char = "R"
                else:
                    border_color = (255, 0, 255)       # Magenta BGR for Left (P1)
                    text_color = (255, 0, 255)
                    label_char = "L"
                    
                is_in_ui = (cy < 45 or cy > 675)
                
                if is_in_ui and state == GESTURE_DRAW:
                    # UI Selection mode cursor
                    cv2.circle(frame, (cx, cy), 10, border_color, 2, cv2.LINE_AA)
                    cv2.circle(frame, (cx, cy), 2, border_color, cv2.FILLED)
                    
                    # Render hover progress arc
                    h_state = hover_states[hand_label]
                    if h_state["btn"] is not None and not h_state["triggered"]:
                        progress = min(1.0, h_state["time"] / HOVER_LOCK_DURATION)
                        angle = int(progress * 360)
                        cv2.ellipse(frame, (cx, cy), (16, 16), -90, 0, angle, border_color, 2, cv2.LINE_AA)
                else:
                    # Standard gestures cursors
                    if state == GESTURE_DRAW:
                        if is_eraser:
                            cv2.circle(frame, (cx, cy), cursor_radius, COLOR_WHITE, 2, cv2.LINE_AA)
                            cv2.circle(frame, (cx, cy), cursor_radius + 2, border_color, 1, cv2.LINE_AA)
                            cv2.circle(frame, (cx, cy), 2, COLOR_WHITE, cv2.FILLED)
                        else:
                            cv2.circle(frame, (cx, cy), cursor_radius, active_color, cv2.FILLED)
                            cv2.circle(frame, (cx, cy), cursor_radius + 3, border_color, 1, cv2.LINE_AA)
                    elif state == GESTURE_ERASE:
                        eraser_size = cursor_radius * 2 + 8
                        cv2.circle(frame, (cx, cy), eraser_size, (255, 255, 255), 1, cv2.LINE_AA)
                        cv2.circle(frame, (cx, cy), eraser_size + 3, border_color, 1, cv2.LINE_AA)
                        cv2.circle(frame, (cx, cy), 3, border_color, cv2.FILLED)
                    elif state == GESTURE_PINCH:
                        # Brush Size Adjustment cursor: solid color circle matching size, with thin white outer circle and text
                        cv2.circle(frame, (cx, cy), cursor_radius, active_color, cv2.FILLED)
                        cv2.circle(frame, (cx, cy), cursor_radius + 4, (255, 255, 255), 1, cv2.LINE_AA)
                        cv2.putText(frame, f"SIZE: {brush_size}px", (cx + 15, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_WHITE, 1, cv2.LINE_AA)
                    else:
                        cv2.circle(frame, (cx, cy), 5, border_color, 1, cv2.LINE_AA)
                        cv2.circle(frame, (cx, cy), 1, border_color, cv2.FILLED)
                    
                cv2.putText(frame, label_char, (cx + 12, cy - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, text_color, 1, cv2.LINE_AA)
                
            # 8. Render GUI Panels & Status
            draw_gui_overlay(frame, canvas_manager, hand_states)
            
            # Calculate Frame Rate
            fps = 1 / dt if dt > 0 else 0.0
            prev_time = curr_time
            
            cv2.putText(frame, f"FPS: {int(fps)}", (FRAME_WIDTH - 100, 660), cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_WHITE, 1, cv2.LINE_AA)
            
            # 9. Render Frame
            cv2.imshow(window_name, frame)
            
            # 10. Keyboard Event Handlers
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                print("Quit key pressed. Exiting...")
                break
            elif key == 27:  # ESC key
                if app_context.is_fullscreen:
                    app_context.toggle_fullscreen()
                    print("Fullscreen disabled.")
            elif key == ord('f') or key == 122:
                app_context.toggle_fullscreen()
                print(f"Fullscreen: {app_context.is_fullscreen}")
            elif key == ord('m'):
                new_mode = MODE_SPLIT if canvas_manager.mode == MODE_SHARED else MODE_SHARED
                canvas_manager.set_mode(new_mode)
                print(f"Mode switched to {new_mode}")
            elif key == ord('c'):
                canvas_manager.clear()
                print("Canvas Cleared.")
            elif key == ord('u'):
                if canvas_manager.undo():
                    print("Undo triggered.")
            elif key == ord('r'):
                if canvas_manager.redo():
                    print("Redo triggered.")
            elif key == ord('e'):
                if canvas_manager.mode == MODE_SHARED:
                    canvas_manager.set_eraser_mode(not canvas_manager.is_eraser)
                    print(f"Eraser mode: {canvas_manager.is_eraser}")
                else:
                    active_any = False
                    for h in ["Left", "Right"]:
                        if h in detected_hands:
                            curr_eraser = canvas_manager.get_eraser_mode(h)
                            canvas_manager.set_eraser_mode(not curr_eraser, h)
                            print(f"[{h}] Eraser mode: {not curr_eraser}")
                            active_any = True
                    if not active_any:
                        for h in ["Left", "Right"]:
                            curr_eraser = canvas_manager.get_eraser_mode(h)
                            canvas_manager.set_eraser_mode(not curr_eraser, h)
                        print("Both Eraser modes toggled.")
            elif key == ord('1'):
                if canvas_manager.mode == MODE_SHARED:
                    canvas_manager.set_brush_color((0, 0, 255))  # Red
                    print("Color set to RED.")
                else:
                    for h in ["Left", "Right"]:
                        if h in detected_hands:
                            canvas_manager.set_brush_color((0, 0, 255), h)
                            print(f"[{h}] Color set to RED.")
            elif key == ord('2'):
                if canvas_manager.mode == MODE_SHARED:
                    canvas_manager.set_brush_color((0, 255, 0))  # Green
                    print("Color set to GREEN.")
                else:
                    for h in ["Left", "Right"]:
                        if h in detected_hands:
                            canvas_manager.set_brush_color((0, 255, 0), h)
                            print(f"[{h}] Color set to GREEN.")
            elif key == ord('3'):
                if canvas_manager.mode == MODE_SHARED:
                    canvas_manager.set_brush_color((255, 0, 0))  # Blue
                    print("Color set to BLUE.")
                else:
                    for h in ["Left", "Right"]:
                        if h in detected_hands:
                            canvas_manager.set_brush_color((255, 0, 0), h)
                            print(f"[{h}] Color set to BLUE.")
            elif key == ord('4'):
                if canvas_manager.mode == MODE_SHARED:
                    canvas_manager.set_brush_color((0, 255, 255))  # Yellow
                    print("Color set to YELLOW.")
                else:
                    for h in ["Left", "Right"]:
                        if h in detected_hands:
                            canvas_manager.set_brush_color((0, 255, 255), h)
                            print(f"[{h}] Color set to YELLOW.")
            elif key == ord('['):
                if canvas_manager.mode == MODE_SHARED:
                    canvas_manager.set_brush_thickness(max(2, canvas_manager.active_thickness - 2))
                    print(f"Brush size decreased to {canvas_manager.active_thickness}.")
                else:
                    active_any = False
                    for h in ["Left", "Right"]:
                        if h in detected_hands:
                            new_size = max(2, canvas_manager.active_thicknesses[h] - 2)
                            canvas_manager.set_brush_thickness(new_size, h)
                            print(f"[{h}] Brush size decreased to {new_size}.")
                            active_any = True
                    if not active_any:
                        for h in ["Left", "Right"]:
                            new_size = max(2, canvas_manager.active_thicknesses[h] - 2)
                            canvas_manager.set_brush_thickness(new_size, h)
                        print(f"Both brush sizes decreased.")
            elif key == ord(']'):
                if canvas_manager.mode == MODE_SHARED:
                    canvas_manager.set_brush_thickness(min(50, canvas_manager.active_thickness + 2)) # max 50px
                    print(f"Brush size increased to {canvas_manager.active_thickness}.")
                else:
                    active_any = False
                    for h in ["Left", "Right"]:
                        if h in detected_hands:
                            new_size = min(50, canvas_manager.active_thicknesses[h] + 2) # max 50px
                            canvas_manager.set_brush_thickness(new_size, h)
                            print(f"[{h}] Brush size increased to {new_size}.")
                            active_any = True
                    if not active_any:
                        for h in ["Left", "Right"]:
                            new_size = min(50, canvas_manager.active_thicknesses[h] + 2) # max 50px
                            canvas_manager.set_brush_thickness(new_size, h)
                        print(f"Both brush sizes increased.")

    finally:
        print("Cleaning up resources...")
        if cap is not None and cap.isOpened():
            cap.release()
        if tracker is not None:
            tracker.close()
        cv2.destroyAllWindows()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
