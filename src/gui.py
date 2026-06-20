"""
gui.py - GUI overlay components, status bar indicators, and startup load screens.
"""

import cv2
import numpy as np
from src.utils import (
    COLOR_WHITE,
    COLOR_BLACK,
    COLOR_GREEN,
    GESTURE_DRAW,
    GESTURE_ERASE,
    GESTURE_PINCH,
    GESTURE_IDLE,
    MODE_SHARED,
    MODE_SPLIT,
)
from src.buttons import get_active_buttons

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
