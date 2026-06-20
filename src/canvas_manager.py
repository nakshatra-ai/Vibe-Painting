"""
canvas_manager.py - Manages drawing stroke data, layers blending, and Undo/Redo stacks.
"""

import cv2
import numpy as np

class Stroke:
    def __init__(self, color, thickness, is_eraser=False):
        """
        Represents a single continuous freehand drawing line or eraser path.
        """
        self.points = []  # List of (x, y) tuples
        self.color = color  # BGR tuple
        self.thickness = thickness  # integer thickness
        self.is_eraser = is_eraser  # boolean flag

    def draw(self, canvas, mask):
        """
        Draws the entire stroke onto the provided canvas and mask layers.
        """
        if not self.points:
            return
            
        if len(self.points) == 1:
            # Draw a dot if there is only one point in the stroke
            pt = self.points[0]
            val = 0 if self.is_eraser else 255
            color_val = (0, 0, 0) if self.is_eraser else self.color
            cv2.circle(canvas, pt, self.thickness // 2, color_val, cv2.FILLED)
            cv2.circle(mask, pt, self.thickness // 2, val, cv2.FILLED)
            return

        # Draw line segments connecting consecutive points
        for i in range(len(self.points) - 1):
            pt1 = self.points[i]
            pt2 = self.points[i + 1]
            val = 0 if self.is_eraser else 255
            color_val = (0, 0, 0) if self.is_eraser else self.color
            
            # Anti-aliased line drawing for smooth curves
            cv2.line(canvas, pt1, pt2, color_val, self.thickness, cv2.LINE_AA)
            cv2.line(mask, pt1, pt2, val, self.thickness, cv2.LINE_AA)


class CanvasManager:
    def __init__(self, width=1280, height=720, max_history=100):
        """
        Manages the active canvas layers, current stroke state, and undo/redo stacks.
        Supports both Shared Canvas and Split-Screen modes.
        """
        self.width = width
        self.height = height
        self.max_history = max_history

        from src.utils import MODE_SHARED
        self.mode = MODE_SHARED

        # ---------------------------------------------
        # SHARED MODE VARIABLES
        # ---------------------------------------------
        self.undo_stack = []
        self.redo_stack = []
        self.active_color = (0, 0, 255)  # Default BGR: Red
        self.active_thickness = 10
        self.is_eraser = False

        # ---------------------------------------------
        # SPLIT-SCREEN VARIABLES (independent per hand)
        # ---------------------------------------------
        # "Left" represents Player 1 (Left canvas), "Right" represents Player 2 (Right canvas)
        self.undo_stacks = {"Left": [], "Right": []}
        self.redo_stacks = {"Left": [], "Right": []}
        self.active_colors = {"Left": (0, 0, 255), "Right": (255, 0, 0)}  # P1: Red, P2: Blue
        self.active_thicknesses = {"Left": 10, "Right": 10}
        self.is_erasers = {"Left": False, "Right": False}
        
        # Track order of strokes for global keyboard undo/redo in split mode
        self.stroke_order = []
        self.redo_order = []

        # Two concurrent active drawing stroke streams
        self.current_strokes = {"Left": None, "Right": None}

        # Canvas Images
        self.canvas_image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.mask_image = np.zeros((self.height, self.width), dtype=np.uint8)

    def set_brush_color(self, color, hand_label=None):
        """Sets the active drawing color (BGR format)."""
        from src.utils import MODE_SHARED
        if self.mode == MODE_SHARED:
            self.active_color = color
            self.is_eraser = False
        else:
            if hand_label:
                self.active_colors[hand_label] = color
                self.is_erasers[hand_label] = False

    def set_brush_thickness(self, thickness, hand_label=None):
        """Sets the active brush thickness."""
        from src.utils import MODE_SHARED
        if self.mode == MODE_SHARED:
            self.active_thickness = thickness
        else:
            if hand_label:
                self.active_thicknesses[hand_label] = thickness

    def set_eraser_mode(self, enabled=True, hand_label=None):
        """Enables or disables eraser mode."""
        from src.utils import MODE_SHARED
        if self.mode == MODE_SHARED:
            self.is_eraser = enabled
        else:
            if hand_label:
                self.is_erasers[hand_label] = enabled

    def get_color(self, hand_label):
        from src.utils import MODE_SHARED
        return self.active_color if self.mode == MODE_SHARED else self.active_colors[hand_label]

    def get_thickness(self, hand_label):
        from src.utils import MODE_SHARED
        return self.active_thickness if self.mode == MODE_SHARED else self.active_thicknesses[hand_label]

    def get_eraser_mode(self, hand_label):
        from src.utils import MODE_SHARED
        return self.is_eraser if self.mode == MODE_SHARED else self.is_erasers[hand_label]

    def set_mode(self, mode):
        """Sets the operating mode (Shared or Split) and rebuilds the canvas."""
        self.end_stroke("Left")
        self.end_stroke("Right")
        self.mode = mode
        self.rebuild_canvas()

    def start_stroke(self, hand_label="Left", force_eraser=False):
        """
        Initializes a new drawing stroke for a specific hand.
        """
        if self.current_strokes.get(hand_label) is not None:
            self.end_stroke(hand_label)
            
        from src.utils import MODE_SHARED
        if self.mode == MODE_SHARED:
            self.current_strokes[hand_label] = Stroke(
                color=self.active_color,
                thickness=self.active_thickness,
                is_eraser=self.is_eraser or force_eraser
            )
        else:
            self.current_strokes[hand_label] = Stroke(
                color=self.active_colors[hand_label],
                thickness=self.active_thicknesses[hand_label],
                is_eraser=self.is_erasers[hand_label] or force_eraser
            )

    def add_point(self, x, y, hand_label="Left"):
        """
        Adds a new coordinate point to the current stroke of a specific hand.
        Applies linear interpolation and enforces vertical split screen boundaries.
        """
        stroke = self.current_strokes.get(hand_label)
        if stroke is None:
            self.start_stroke(hand_label)
            stroke = self.current_strokes[hand_label]
            
        # Bound coordinates based on active mode
        from src.utils import MODE_SHARED, MODE_SPLIT
        if self.mode == MODE_SPLIT:
            mid_x = self.width // 2
            if hand_label == "Left":
                x = max(0, min(x, mid_x - 1))
            else:
                x = max(mid_x, min(x, self.width - 1))
        else:
            x = max(0, min(x, self.width - 1))
            
        y = max(0, min(y, self.height - 1))
        
        new_pt = (x, y)
        val = 0 if stroke.is_eraser else 255
        color_val = (0, 0, 0) if stroke.is_eraser else stroke.color

        # If we have previous points, check if we need to interpolate
        if stroke.points:
            last_pt = stroke.points[-1]
            dist = np.hypot(x - last_pt[0], y - last_pt[1])
            
            if 8 < dist < 300:
                step_size = 3 if dist > 30 else 5
                num_steps = int(dist / step_size)
                if num_steps > 1:
                    for step in range(1, num_steps):
                        t = step / num_steps
                        ix = int(last_pt[0] + t * (x - last_pt[0]))
                        iy = int(last_pt[1] + t * (y - last_pt[1]))
                        
                        inter_pt = (ix, iy)
                        stroke.points.append(inter_pt)
                        
                        # Draw the intermediate segment
                        pt_prev = stroke.points[-2]
                        cv2.line(self.canvas_image, pt_prev, inter_pt, color_val, stroke.thickness, cv2.LINE_AA)
                        cv2.line(self.mask_image, pt_prev, inter_pt, val, stroke.thickness, cv2.LINE_AA)

            # Draw final segment to the new point
            pt_prev = stroke.points[-1]
            stroke.points.append(new_pt)
            cv2.line(self.canvas_image, pt_prev, new_pt, color_val, stroke.thickness, cv2.LINE_AA)
            cv2.line(self.mask_image, pt_prev, new_pt, val, stroke.thickness, cv2.LINE_AA)
        else:
            # Draw single point dot if stroke has just started
            stroke.points.append(new_pt)
            cv2.circle(self.canvas_image, new_pt, stroke.thickness // 2, color_val, cv2.FILLED)
            cv2.circle(self.mask_image, new_pt, stroke.thickness // 2, val, cv2.FILLED)

    def smooth_stroke_points(self, points, window_size=5):
        """
        Applies a moving average smoothing filter to a list of coordinates.
        """
        if len(points) < window_size:
            return points
            
        smoothed = []
        half = window_size // 2
        n = len(points)
        
        for i in range(n):
            if i < half or i >= n - half:
                smoothed.append(points[i])
            else:
                window = points[i - half : i + half + 1]
                xs = [pt[0] for pt in window]
                ys = [pt[1] for pt in window]
                smoothed.append((int(np.mean(xs)), int(np.mean(ys))))
        return smoothed

    def end_stroke(self, hand_label="Left"):
        """
        Finalizes the current stroke of a specific hand, applies moving average smoothing,
        and commits it to the appropriate stack.
        """
        stroke = self.current_strokes.get(hand_label)
        if stroke is not None:
            if stroke.points:
                # Apply post-processing smoothing to finished strokes (excluding erasers)
                if not stroke.is_eraser and len(stroke.points) > 3:
                    stroke.points = self.smooth_stroke_points(stroke.points, window_size=5)
                
                from src.utils import MODE_SHARED
                if self.mode == MODE_SHARED:
                    self.undo_stack.append(stroke)
                    self.redo_stack.clear()
                    if len(self.undo_stack) > self.max_history:
                        self.undo_stack.pop(0)
                else:
                    self.undo_stacks[hand_label].append(stroke)
                    self.redo_stacks[hand_label].clear()
                    self.stroke_order.append(hand_label)
                    # Clean redo order for this hand when drawing a new stroke
                    self.redo_order = [h for h in self.redo_order if h != hand_label]
                    if len(self.undo_stacks[hand_label]) > self.max_history:
                        self.undo_stacks[hand_label].pop(0)
                    
                self.rebuild_canvas()  # Re-render to show the smoothed, stabilized path
            self.current_strokes[hand_label] = None

    def undo(self, hand_label=None):
        """
        Undoes the last stroke for either the shared canvas or a specific split screen side.
        """
        self.end_stroke("Left")
        self.end_stroke("Right")
        
        from src.utils import MODE_SHARED
        if self.mode == MODE_SHARED:
            if self.undo_stack:
                stroke = self.undo_stack.pop()
                self.redo_stack.append(stroke)
                self.rebuild_canvas()
                return True
        else:
            if hand_label:
                if self.undo_stacks[hand_label]:
                    stroke = self.undo_stacks[hand_label].pop()
                    self.redo_stacks[hand_label].append(stroke)
                    if hand_label in self.stroke_order:
                        for idx in reversed(range(len(self.stroke_order))):
                            if self.stroke_order[idx] == hand_label:
                                self.stroke_order.pop(idx)
                                break
                    self.redo_order.append(hand_label)
                    self.rebuild_canvas()
                    return True
            else:
                if self.stroke_order:
                    last_hand = self.stroke_order.pop()
                    if self.undo_stacks[last_hand]:
                        stroke = self.undo_stacks[last_hand].pop()
                        self.redo_stacks[last_hand].append(stroke)
                        self.redo_order.append(last_hand)
                        self.rebuild_canvas()
                        return True
        return False

    def redo(self, hand_label=None):
        """
        Redoes the last undone stroke for either the shared canvas or a specific split screen side.
        """
        self.end_stroke("Left")
        self.end_stroke("Right")
        
        from src.utils import MODE_SHARED
        if self.mode == MODE_SHARED:
            if self.redo_stack:
                stroke = self.redo_stack.pop()
                self.undo_stack.append(stroke)
                self.rebuild_canvas()
                return True
        else:
            if hand_label:
                if self.redo_stacks[hand_label]:
                    stroke = self.redo_stacks[hand_label].pop()
                    self.undo_stacks[hand_label].append(stroke)
                    self.stroke_order.append(hand_label)
                    if hand_label in self.redo_order:
                        for idx in reversed(range(len(self.redo_order))):
                            if self.redo_order[idx] == hand_label:
                                self.redo_order.pop(idx)
                                break
                    self.rebuild_canvas()
                    return True
            else:
                if self.redo_order:
                    last_hand = self.redo_order.pop()
                    if self.redo_stacks[last_hand]:
                        stroke = self.redo_stacks[last_hand].pop()
                        self.undo_stacks[last_hand].append(stroke)
                        self.stroke_order.append(last_hand)
                        self.rebuild_canvas()
                        return True
        return False

    def clear(self, hand_label=None):
        """
        Resets either the entire canvas or a specific split screen side.
        """
        from src.utils import MODE_SHARED
        if self.mode == MODE_SHARED:
            self.current_strokes = {"Left": None, "Right": None}
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.canvas_image.fill(0)
            self.mask_image.fill(0)
        else:
            if hand_label:
                self.current_strokes[hand_label] = None
                self.undo_stacks[hand_label].clear()
                self.redo_stacks[hand_label].clear()
                self.stroke_order = [h for h in self.stroke_order if h != hand_label]
                self.redo_order = [h for h in self.redo_order if h != hand_label]
                self.rebuild_canvas()
            else:
                self.current_strokes = {"Left": None, "Right": None}
                self.undo_stacks["Left"].clear()
                self.undo_stacks["Right"].clear()
                self.redo_stacks["Left"].clear()
                self.redo_stacks["Right"].clear()
                self.stroke_order.clear()
                self.redo_order.clear()
                self.canvas_image.fill(0)
                self.mask_image.fill(0)

    def rebuild_canvas(self):
        """
        Clears the canvas images and redraws all strokes based on current mode and history stacks.
        """
        self.canvas_image.fill(0)
        self.mask_image.fill(0)
        
        from src.utils import MODE_SHARED
        if self.mode == MODE_SHARED:
            for stroke in self.undo_stack:
                stroke.draw(self.canvas_image, self.mask_image)
        else:
            for stroke in self.undo_stacks["Left"]:
                stroke.draw(self.canvas_image, self.mask_image)
            for stroke in self.undo_stacks["Right"]:
                stroke.draw(self.canvas_image, self.mask_image)

    def composite_frame(self, frame):
        """
        Efficiently blends the drawing canvas on top of the webcam feed frame.
        Use vectorized numpy operations for 60 FPS performance.
        """
        # Ensure mask is duplicated to 3 channels for logical mask selection
        mask_3d = cv2.merge([self.mask_image, self.mask_image, self.mask_image])
        
        # Blend: everywhere mask > 0, output canvas_image, otherwise output frame
        composited = np.where(mask_3d > 0, self.canvas_image, frame)
        return composited
