# 🎨 Air Canvas Pro

✨ No mouse. No stylus. Just your hands and a little computer vision magic.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Hand%20Tracking-orange)
![Status](https://img.shields.io/badge/Status-Active-success)

---

## Draw in the air. No mouse. No stylus. Just vibes.

Wave your hands in front of your webcam and watch lines appear on the screen. No fancy hardware, no expensive stylus—just standard computer vision and python math working together to track your fingers in real-time.

---

## ✨ Feature Highlights

*   **👥 Split-Screen Mode**: Draw with a friend (or play tic-tac-toe) in real-time with isolated brushes, canvas states, and independent undo/redo.
*   **⚡ Anti-Jitter Smoothing**: Powered by Exponential Moving Average (EMA) and velocity tracking so your lines stay smooth, even if your hands shake a bit.
*   **🤏 Pinch-to-Resize Brush**: Pinch your index and thumb together, then slide left/right to scale your brush size (2px to 50px) on the fly.

---

## 🚀 Little Quality-of-Life Touches

*   **🎛️ Hover-to-Click Toolbar**: Hover your finger over toolbar buttons for 0.25 seconds to trigger actions. Standard mouse clicks also work as a backup.
*   **🎚️ Bottom Sliders**: Slide your finger along the bottom scale to change brush sizes manually, or drag it with your mouse.
*   **⏱️ 300ms Grace Period**: If the webcam loses tracking for a split second, the engine predicts where your hand went so your lines don't break.
*   **🔌 Zero-leak Exit**: Press `Q` to quit, `ESC` to drop out of fullscreen, or just click the `X` window button. Everything cleans up nicely without leaving background processes running.

---

## 🖐️ Gesture Controls

No hand gymnastics here. We kept the gestures simple and intuitive:

| Gesture | Mode | Action | Telemetry Color |
| :--- | :---: | :--- | :--- |
| 🤏 **Thumb + Index Pinch** | `BRUSH SIZE` | Slide hand left/right to dynamically scale brush | Cyan / Magenta |
| ✊ **Closed Fist** | `ERASE` | Rub out canvas strokes in real-time | Orange |
| 👆 **Index Finger Raised** | `DRAW` | Draw continuously in the air | Green |
| 🖐️ **Open Palm** | `PAUSE` | Pause drawing/erasing (default safety state) | Gray |

*Note: Any unrecognized hand posture automatically defaults to `PAUSE` mode to prevent accidental stray lines.*

---

## 🛠️ Tech Stack

*   🐍 **Python 3.9+** — The backbone of the project.
*   👋 **MediaPipe Hands** — Google's hand tracking engine (handles the heavy lifting of finding landmarks).
*   🎥 **OpenCV** — Grabs webcam frames and draws overlays without needing a heavy UI framework.
*   📊 **NumPy** — Handles the linear algebra, smoothing math, and coordinates.

---

## 📂 Project Structure

Where everything lives:

*   [main.py](file:///c:/Users/Sawmiyaa/OneDrive/Documents/Air%20canvas/main.py) — Main runtime entry point and camera processing loop
*   [requirements.txt](file:///c:/Users/Sawmiyaa/OneDrive/Documents/Air%20canvas/requirements.txt) — Project package requirements
*   `src/` — Application source folder
    *   [app_context.py](file:///c:/Users/Sawmiyaa/OneDrive/Documents/Air%20canvas/src/app_context.py) — Global window state and configuration management
    *   [buttons.py](file:///c:/Users/Sawmiyaa/OneDrive/Documents/Air%20canvas/src/buttons.py) — Toolbar buttons, click detection, and hover lock systems
    *   [canvas_manager.py](file:///c:/Users/Sawmiyaa/OneDrive/Documents/Air%20canvas/src/canvas_manager.py) — Canvas layers, drawing lines, and history stacks (undo/redo)
    *   [gui.py](file:///c:/Users/Sawmiyaa/OneDrive/Documents/Air%20canvas/src/gui.py) — Glassmorphic GUI overlays, feedback text, and loading screens
    *   [hand_tracker.py](file:///c:/Users/Sawmiyaa/OneDrive/Documents/Air%20canvas/src/hand_tracker.py) — MediaPipe integration, hand detection, and gesture pipeline
    *   [utils.py](file:///c:/Users/Sawmiyaa/OneDrive/Documents/Air%20canvas/src/utils.py) — Global dimensions, coordinates, and styling constants

---

## ⚙️ Setup

Grab dependencies first:

```bash
pip install -r requirements.txt
```

---

## 🎮 Running the Project

Start the application from your terminal:

```bash
python main.py
```

> 💡 **Note**: The very first launch might take a couple of seconds while it downloads and initializes the hand-tracking model. Once loaded, you'll see a webcam window feed and can start drawing.

---

## ⌨️ Keyboard Shortcuts

For when you don't feel like using gestures:

| Key | Action |
| :---: | :--- |
| **`Q`** / **`q`** | Exit the application completely |
| **`ESC`** | Exit fullscreen mode only |
| **`F`** / **`f`** | Toggle Fullscreen mode |
| **`M`** / **`m`** | Switch drawing mode (Shared Canvas <-> Split-Screen) |
| **`C`** / **`c`** | Clear active canvas |
| **`U`** / **`u`** | Undo last stroke |
| **`R`** / **`r`** | Redo last undone stroke |
| **`E`** / **`e`** | Toggle Eraser mode |
| **`1`, `2`, `3`, `4`**| Switch colors (Red, Green, Blue, Yellow) |
| **`[`** / **`]`** | Decrease / Increase brush thickness by 2px |

---

## 🔮 Future Ideas

*   🤖 **Auto-Shape Snap**: Snap messy hand-drawn circles and squares into clean vectors.
*   💾 **Save Masterpieces**: A quick shortcut to export your canvas to a `.png` or `.jpg`.
*   🎨 **Floating Color Wheel**: Open a full HSV color picker directly on your hand.

---

🎨 **Go turn your webcam into a paintbrush.**

*Built with coffee, computer vision, and questionable amounts of debugging.*
