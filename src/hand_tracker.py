"""
hand_tracker.py - MediaPipe Tasks API Hand Landmark tracking and gesture classification (Dual-Hand).
"""

import os
import urllib.request
import cv2
import mediapipe as mp
import numpy as np
from src.utils import EMA_ALPHA, GESTURE_DRAW, GESTURE_ERASE, GESTURE_IDLE

# Define hand connection skeleton for custom visualization
CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle
    (9, 10), (10, 11), (11, 12),
    # Ring
    (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm/Knuckles connections
    (5, 9), (9, 13), (13, 17)
]

class HandTracker:
    def __init__(self, max_hands=2, detection_confidence=0.7, tracking_confidence=0.7):
        """
        Initializes the MediaPipe Tasks API Hand Landmarker for up to 2 hands.
        Downloads the model file automatically if it is missing.
        """
        model_path = 'hand_landmarker.task'
        if not os.path.exists(model_path):
            print("Downloading hand_landmarker.task model...")
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            try:
                urllib.request.urlretrieve(url, model_path)
                print("Download complete.")
            except Exception as e:
                print(f"Error downloading hand_landmarker.task: {e}")
                raise e

        # Initialize Tasks API
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        base_options = python.BaseOptions(model_asset_path=model_path)
        self.options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=tracking_confidence
        )
        self.detector = vision.HandLandmarker.create_from_options(self.options)
        self.results = None
        
        # Landmark indices mapping
        self.tip_ids = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky
        self.pip_ids = [3, 6, 10, 14, 18]  # Reference joints for checking extension
        
        # Smoothing states split by hand label
        self.prev_coords = {"Left": (None, None), "Right": (None, None)}

    def find_hands(self, frame, draw=True):
        """
        Processes the input image to find hands using the Tasks API.
        Draws custom stylized landmarks for both hands (distinct colors for Left vs Right).
        """
        h, w, _ = frame.shape
        # Convert BGR OpenCV frame to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Feed-forward video frame with timestamp in milliseconds
        timestamp_ms = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)
        self.results = self.detector.detect_for_video(mp_image, timestamp_ms)
        
        if self.results.hand_landmarks and draw:
            for hand_idx, hand_lms in enumerate(self.results.hand_landmarks):
                # Identify Hand label
                hand_label = "Right"
                if self.results.handedness and hand_idx < len(self.results.handedness):
                    hand_label = self.results.handedness[hand_idx][0].category_name
                
                # Colors: Right uses Cyan/Orange palette, Left uses Purple/Magenta palette
                if hand_label == "Right":
                    line_color = (230, 216, 173)  # Slate
                    tip_color = (0, 165, 255)    # Orange
                    joint_color = (255, 100, 0)  # Orange-red
                else:
                    line_color = (210, 180, 220)  # Pale purple
                    tip_color = (255, 0, 255)    # Magenta
                    joint_color = (128, 0, 128)  # Deep purple
                
                # 1. Draw connection skeleton lines
                for connection in CONNECTIONS:
                    p1_id, p2_id = connection
                    lm1 = hand_lms[p1_id]
                    lm2 = hand_lms[p2_id]
                    pt1 = (int(lm1.x * w), int(lm1.y * h))
                    pt2 = (int(lm2.x * w), int(lm2.y * h))
                    cv2.line(frame, pt1, pt2, line_color, 2, cv2.LINE_AA)
                
                # 2. Draw outer circle at joints
                for lm_id, lm in enumerate(hand_lms):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    if lm_id in self.tip_ids:
                        cv2.circle(frame, (cx, cy), 6, tip_color, cv2.FILLED)
                        cv2.circle(frame, (cx, cy), 8, (255, 255, 255), 1, cv2.LINE_AA)
                    else:
                        cv2.circle(frame, (cx, cy), 4, joint_color, cv2.FILLED)
                        cv2.circle(frame, (cx, cy), 6, (255, 255, 255), 1, cv2.LINE_AA)
                        
        return frame

    def find_position(self, frame):
        """
        Extracts landmark positions and bounding box coordinates for all detected hands.
        Returns a list of hand payloads: [{"lm_list": [...], "bbox": (...), "label": "Left"|"Right"}]
        """
        h, w, _ = frame.shape
        hands_payloads = []
        
        if self.results and self.results.hand_landmarks:
            for hand_idx, hand_lms in enumerate(self.results.hand_landmarks):
                lm_list = []
                hand_label = "Right"
                if self.results.handedness and hand_idx < len(self.results.handedness):
                    hand_label = self.results.handedness[hand_idx][0].category_name
                
                x_min, y_min, x_max, y_max = w, h, 0, 0
                for lm_id, lm in enumerate(hand_lms):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lm_list.append([lm_id, cx, cy])
                    
                    if cx < x_min: x_min = cx
                    if cy < y_min: y_min = cy
                    if cx > x_max: x_max = cx
                    if cy > y_max: y_max = cy
                    
                bbox = (x_min, y_min, x_max, y_max)
                hands_payloads.append({
                    "lm_list": lm_list,
                    "bbox": bbox,
                    "label": hand_label
                })
                
        # If no hands are active, reset filters
        if not hands_payloads:
            self.reset_filter()
            
        return hands_payloads

    def get_fingers_up(self, lm_list, hand_label="Right"):
        """
        Determines which fingers are raised/extended.
        Returns a list of 5 booleans (Thumb, Index, Middle, Ring, Pinky).
        """
        if not lm_list:
            return [0, 0, 0, 0, 0]
            
        fingers = []
        
        # 1. Thumb detection (horizontal check based on Left/Right handedness)
        if hand_label == "Right":
            if lm_list[self.tip_ids[0]][1] > lm_list[self.pip_ids[0]][1]:
                fingers.append(1)
            else:
                fingers.append(0)
        else:  # Left hand
            if lm_list[self.tip_ids[0]][1] < lm_list[self.pip_ids[0]][1]:
                fingers.append(1)
            else:
                fingers.append(0)
                
        # 2. 4 Fingers (Index, Middle, Ring, Pinky) - Vertical extension check
        for i in range(1, 5):
            if lm_list[self.tip_ids[i]][2] < lm_list[self.pip_ids[i]][2]:
                fingers.append(1)
            else:
                fingers.append(0)
                
        return fingers

    def detect_gesture(self, lm_list, hand_label="Right"):
        """
        Classifies gestures based on priority:
        1. Pinch Gesture (Index + Thumb) = Brush Size Adjustment (GESTURE_PINCH)
        2. Closed Fist (All Fingers Folded) = Eraser Mode (GESTURE_ERASE)
        3. Index Finger Only = Draw Mode (GESTURE_DRAW)
        4. Open Palm (All Five Fingers Extended) = Pause Mode (GESTURE_IDLE)
        5. Otherwise = Pause Mode (GESTURE_IDLE)
        """
        from src.utils import GESTURE_DRAW, GESTURE_ERASE, GESTURE_IDLE, GESTURE_PINCH
        import numpy as np

        if not lm_list:
            return GESTURE_IDLE

        fingers = self.get_fingers_up(lm_list, hand_label)

        # 1. Check Pinch Gesture (Highest Priority)
        # Touch Index Finger Tip (8) and Thumb Tip (4) together
        thumb_tip = lm_list[4]
        index_tip = lm_list[8]
        pinch_dist = np.hypot(index_tip[1] - thumb_tip[1], index_tip[2] - thumb_tip[2])
        
        # Check index extension to distinguish pinch from closed fist
        index_knuckle = lm_list[5]
        index_ext_dist = np.hypot(index_tip[1] - index_knuckle[1], index_tip[2] - index_knuckle[2])

        # Pinch: tips are close, index is extended, middle/ring/pinky are folded
        if pinch_dist < 38 and index_ext_dist > 42 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
            return GESTURE_PINCH

        # 2. Closed Fist (All Fingers Folded) = Eraser Mode
        if fingers[0] == 0 and fingers[1] == 0 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
            return GESTURE_ERASE

        # 3. Index Finger Only = Draw Mode
        if fingers[0] == 0 and fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
            return GESTURE_DRAW

        # 4. Open Palm (All Five Fingers Extended) = Pause Mode
        if fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 1 and fingers[4] == 1:
            return GESTURE_IDLE

        # Default fallback to Pause Mode
        return GESTURE_IDLE

    def get_smoothed_coordinates(self, x, y, hand_label):
        """
        Applies Exponential Moving Average (EMA) to smooth coords and reduce jitter for a specific hand.
        """
        prev_x, prev_y = self.prev_coords.get(hand_label, (None, None))
        
        if prev_x is None or prev_y is None:
            new_x, new_y = x, y
        else:
            new_x = EMA_ALPHA * x + (1 - EMA_ALPHA) * prev_x
            new_y = EMA_ALPHA * y + (1 - EMA_ALPHA) * prev_y
            
        self.prev_coords[hand_label] = (new_x, new_y)
        return int(new_x), int(new_y)

    def reset_filter(self, hand_label=None):
        """
        Resets the smoothing filter state for one or all hands.
        """
        if hand_label:
            self.prev_coords[hand_label] = (None, None)
        else:
            self.prev_coords = {"Left": (None, None), "Right": (None, None)}

    def close(self):
        """
        Explicitly closes the MediaPipe detector resource.
        """
        try:
            if hasattr(self, 'detector') and self.detector:
                self.detector.close()
        except:
            pass

    def __del__(self):
        """
        Cleans up and closes the MediaPipe detector resource.
        """
        self.close()

