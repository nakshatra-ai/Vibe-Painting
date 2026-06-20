import { FilesetResolver, HandLandmarker } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.8/vision_bundle.mjs";

// ==========================================================================
// 1. Configs & Constants
// ==========================================================================
const FRAME_WIDTH = 1280;
const FRAME_HEIGHT = 720;
const EMA_ALPHA = 0.55;
const HOVER_LOCK_DURATION = 0.25; // seconds
const GRACE_PERIOD = 0.30; // seconds

// Gesture state constants
const GESTURE_IDLE = "Idle";
const GESTURE_DRAW = "Drawing";
const GESTURE_ERASE = "Eraser";
const GESTURE_PINCH = "Pinch";

// Colors
const COLOR_WHITE = "#FFFFFF";
const COLOR_BLACK = "#000000";

// ==========================================================================
// 2. Stroke Class
// ==========================================================================
class Stroke {
  constructor(color, thickness, isEraser = false) {
    this.points = []; // Array of {x, y}
    this.color = color;
    this.thickness = thickness;
    this.isEraser = isEraser;
  }

  draw(ctx) {
    if (this.points.length === 0) return;

    ctx.beginPath();
    ctx.lineWidth = this.thickness;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.globalCompositeOperation = this.isEraser ? "destination-out" : "source-over";
    ctx.strokeStyle = this.color;

    if (this.points.length === 1) {
      const pt = this.points[0];
      ctx.arc(pt.x, pt.y, this.thickness / 2, 0, Math.PI * 2);
      ctx.fillStyle = this.isEraser ? "rgba(0,0,0,1)" : this.color;
      ctx.fill();
    } else {
      ctx.moveTo(this.points[0].x, this.points[0].y);
      for (let i = 1; i < this.points.length; i++) {
        ctx.lineTo(this.points[i].x, this.points[i].y);
      }
      ctx.stroke();
    }
  }
}

// ==========================================================================
// 3. Canvas Manager Class
// ==========================================================================
class CanvasManager {
  constructor(width, height) {
    this.width = width;
    this.height = height;
    this.mode = "Shared"; // Shared or Split

    // Offscreen rendering layer
    this.offscreenCanvas = document.createElement("canvas");
    this.offscreenCanvas.width = width;
    this.offscreenCanvas.height = height;
    this.offscreenCtx = this.offscreenCanvas.getContext("2d");

    // Shared State
    this.undoStack = [];
    this.redoStack = [];
    this.activeColor = "#FF0000"; // Red
    this.activeThickness = 10;
    this.isEraser = false;

    // Split State (P1 = Left, P2 = Right)
    this.undoStacks = { Left: [], Right: [] };
    this.redoStacks = { Left: [], Right: [] };
    this.activeColors = { Left: "#FF0000", Right: "#0000FF" }; // P1: Red, P2: Blue
    this.activeThicknesses = { Left: 10, Right: 10 };
    this.isErasers = { Left: false, Right: false };

    this.strokeOrder = [];
    this.redoOrder = [];

    // Active stroke streams
    this.currentStrokes = { Left: null, Right: null };
  }

  setBrushColor(color, handLabel) {
    if (this.mode === "Shared") {
      this.activeColor = color;
      this.isEraser = false;
    } else if (handLabel) {
      this.activeColors[handLabel] = color;
      this.isErasers[handLabel] = false;
    }
    this.syncUI();
  }

  setBrushThickness(thickness, handLabel) {
    if (this.mode === "Shared") {
      this.activeThickness = thickness;
    } else if (handLabel) {
      this.activeThicknesses[handLabel] = thickness;
    }
    this.syncUI();
  }

  setEraserMode(enabled, handLabel) {
    if (this.mode === "Shared") {
      this.isEraser = enabled;
    } else if (handLabel) {
      this.isErasers[handLabel] = enabled;
    }
    this.syncUI();
  }

  getColor(handLabel) {
    return this.mode === "Shared" ? this.activeColor : this.activeColors[handLabel];
  }

  getThickness(handLabel) {
    return this.mode === "Shared" ? this.activeThickness : this.activeThicknesses[handLabel];
  }

  getEraserMode(handLabel) {
    return this.mode === "Shared" ? this.isEraser : this.isErasers[handLabel];
  }

  setMode(mode) {
    this.endStroke("Left");
    this.endStroke("Right");
    this.mode = mode;
    this.rebuildCanvas();
    this.syncUI();
  }

  startStroke(handLabel, forceEraser = false) {
    if (this.currentStrokes[handLabel]) {
      this.endStroke(handLabel);
    }

    const color = this.getColor(handLabel);
    const thickness = this.getThickness(handLabel);
    const isEraser = this.getEraserMode(handLabel) || forceEraser;

    this.currentStrokes[handLabel] = new Stroke(color, thickness, isEraser);
  }

  addPoint(x, y, handLabel) {
    let stroke = this.currentStrokes[handLabel];
    if (!stroke) {
      this.startStroke(handLabel);
      stroke = this.currentStrokes[handLabel];
    }

    // Bounding check for Split Screen
    if (this.mode === "Split") {
      const mid = this.width / 2;
      if (handLabel === "Left") {
        x = Math.max(0, Math.min(x, mid - 1));
      } else {
        x = Math.max(mid, Math.min(x, this.width - 1));
      }
    } else {
      x = Math.max(0, Math.min(x, this.width - 1));
    }
    y = Math.max(0, Math.min(y, this.height - 1));

    const newPt = { x, y };

    if (stroke.points.length > 0) {
      const lastPt = stroke.points[stroke.points.length - 1];
      const dist = Math.hypot(x - lastPt.x, y - lastPt.y);

      // Symmetrical interpolation for handwriting prediction
      if (dist > 8 && dist < 300) {
        const stepSize = dist > 30 ? 3 : 5;
        const numSteps = Math.floor(dist / stepSize);
        if (numSteps > 1) {
          for (let step = 1; step < numSteps; step++) {
            const t = step / numSteps;
            const ix = lastPt.x + t * (x - lastPt.x);
            const iy = lastPt.y + t * (y - lastPt.y);
            stroke.points.push({ x: ix, y: iy });
          }
        }
      }
    }

    stroke.points.push(newPt);
    stroke.draw(this.offscreenCtx);
  }

  endStroke(handLabel) {
    const stroke = this.currentStrokes[handLabel];
    if (stroke) {
      if (stroke.points.length > 0) {
        // Smooth line
        if (!stroke.isEraser && stroke.points.length > 3) {
          stroke.points = this.smoothPoints(stroke.points, 5);
        }

        if (this.mode === "Shared") {
          this.undoStack.push(stroke);
          this.redoStack = [];
        } else {
          this.undoStacks[handLabel].push(stroke);
          this.redoStacks[handLabel] = [];
          this.strokeOrder.push(handLabel);
          this.redoOrder = this.redoOrder.filter(h => h !== handLabel);
        }
        this.rebuildCanvas();
      }
      this.currentStrokes[handLabel] = null;
    }
  }

  smoothPoints(points, windowSize = 5) {
    if (points.length < windowSize) return points;
    const smoothed = [];
    const half = Math.floor(windowSize / 2);
    const n = points.length;

    for (let i = 0; i < n; i++) {
      if (i < half || i >= n - half) {
        smoothed.push(points[i]);
      } else {
        const window = points.slice(i - half, i + half + 1);
        const avgX = window.reduce((sum, p) => sum + p.x, 0) / windowSize;
        const avgY = window.reduce((sum, p) => sum + p.y, 0) / windowSize;
        smoothed.push({ x: avgX, y: avgY });
      }
    }
    return smoothed;
  }

  undo(handLabel) {
    this.endStroke("Left");
    this.endStroke("Right");

    if (this.mode === "Shared") {
      if (this.undoStack.length > 0) {
        const stroke = this.undoStack.pop();
        this.redoStack.push(stroke);
        this.rebuildCanvas();
        return true;
      }
    } else {
      if (handLabel) {
        if (this.undoStacks[handLabel].length > 0) {
          const stroke = this.undoStacks[handLabel].pop();
          this.redoStacks[handLabel].push(stroke);
          
          const idx = this.strokeOrder.lastIndexOf(handLabel);
          if (idx !== -1) this.strokeOrder.splice(idx, 1);
          this.redoOrder.push(handLabel);
          
          this.rebuildCanvas();
          return true;
        }
      } else if (this.strokeOrder.length > 0) {
        const lastHand = this.strokeOrder.pop();
        if (this.undoStacks[lastHand].length > 0) {
          const stroke = this.undoStacks[lastHand].pop();
          this.redoStacks[lastHand].push(stroke);
          this.redoOrder.push(lastHand);
          this.rebuildCanvas();
          return true;
        }
      }
    }
    return false;
  }

  redo(handLabel) {
    this.endStroke("Left");
    this.endStroke("Right");

    if (this.mode === "Shared") {
      if (this.redoStack.length > 0) {
        const stroke = this.redoStack.pop();
        this.undoStack.push(stroke);
        this.rebuildCanvas();
        return true;
      }
    } else {
      if (handLabel) {
        if (this.redoStacks[handLabel].length > 0) {
          const stroke = this.redoStacks[handLabel].pop();
          this.undoStacks[handLabel].push(stroke);
          this.strokeOrder.push(handLabel);
          
          const idx = this.redoOrder.lastIndexOf(handLabel);
          if (idx !== -1) this.redoOrder.splice(idx, 1);
          
          this.rebuildCanvas();
          return true;
        }
      } else if (this.redoOrder.length > 0) {
        const lastHand = this.redoOrder.pop();
        if (this.redoStacks[lastHand].length > 0) {
          const stroke = this.redoStacks[lastHand].pop();
          this.undoStacks[lastHand].push(stroke);
          this.strokeOrder.push(lastHand);
          this.rebuildCanvas();
          return true;
        }
      }
    }
    return false;
  }

  clear(handLabel) {
    this.currentStrokes = { Left: null, Right: null };
    if (this.mode === "Shared") {
      this.undoStack = [];
      this.redoStack = [];
    } else if (handLabel) {
      this.undoStacks[handLabel] = [];
      this.redoStacks[handLabel] = [];
      this.strokeOrder = this.strokeOrder.filter(h => h !== handLabel);
      this.redoOrder = this.redoOrder.filter(h => h !== handLabel);
    } else {
      this.undoStacks = { Left: [], Right: [] };
      this.redoStacks = { Left: [], Right: [] };
      this.strokeOrder = [];
      this.redoOrder = [];
    }
    this.rebuildCanvas();
  }

  rebuildCanvas() {
    this.offscreenCtx.clearRect(0, 0, this.width, this.height);
    if (this.mode === "Shared") {
      this.undoStack.forEach(s => s.draw(this.offscreenCtx));
    } else {
      // Re-draw both players in order
      this.undoStacks.Left.forEach(s => s.draw(this.offscreenCtx));
      this.undoStacks.Right.forEach(s => s.draw(this.offscreenCtx));
    }
  }

  syncUI() {
    // Mode UI Container class
    const container = document.getElementById("app-container");
    container.className = this.mode === "Shared" ? "mode-shared" : "mode-split";

    // Update Shared Active Colors
    document.querySelectorAll(".shared-dock .btn-color").forEach(btn => {
      const active = btn.getAttribute("data-val") === this.activeColor && !this.isEraser;
      btn.classList.toggle("active", active);
    });
    document.querySelector(".shared-dock [data-val='eraser']").classList.toggle("active", this.isEraser);
    document.getElementById("slider-shared").value = this.activeThickness;
    document.getElementById("size-val-shared").textContent = this.activeThickness;
    document.getElementById("tool-shared").textContent = this.isEraser ? "Eraser" : "Brush";

    // Update Split P1 UI
    document.querySelectorAll(".p1-dock .btn-color").forEach(btn => {
      const active = btn.getAttribute("data-val") === this.activeColors.Left && !this.isErasers.Left;
      btn.classList.toggle("active", active);
    });
    document.querySelector(".p1-dock [data-val='eraser']").classList.toggle("active", this.isErasers.Left);
    document.getElementById("slider-p1").value = this.activeThicknesses.Left;
    document.getElementById("size-val-p1").textContent = this.activeThicknesses.Left;

    // Update Split P2 UI
    document.querySelectorAll(".p2-dock .btn-color").forEach(btn => {
      const active = btn.getAttribute("data-val") === this.activeColors.Right && !this.isErasers.Right;
      btn.classList.toggle("active", active);
    });
    document.querySelector(".p2-dock [data-val='eraser']").classList.toggle("active", this.isErasers.Right);
    document.getElementById("slider-p2").value = this.activeThicknesses.Right;
    document.getElementById("size-val-p2").textContent = this.activeThicknesses.Right;
  }
}

// ==========================================================================
// 4. Variables & Setup
// ==========================================================================
const video = document.getElementById("webcam");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

// Ensure canvas matches 16:9 HD standard internal resolution
canvas.width = FRAME_WIDTH;
canvas.height = FRAME_HEIGHT;

const canvasManager = new CanvasManager(FRAME_WIDTH, FRAME_HEIGHT);

// State tracking
let tracker = null;
let stream = null;
let animationFrameId = null;

const prevGestures = { Left: GESTURE_IDLE, Right: GESTURE_IDLE };
const prevInUiZone = { Left: false, Right: false };
const handLostTimes = { Left: null, Right: null };
const lastTrackedPositions = { Left: null, Right: null };
const velocities = { Left: { x: 0, y: 0 }, Right: { x: 0, y: 0 } };

const consecutiveCounts = { Left: 0, Right: 0 };
const pendingGestures = { Left: GESTURE_IDLE, Right: GESTURE_IDLE };
const currentStates = { Left: GESTURE_IDLE, Right: GESTURE_IDLE };

const prevCoords = { Left: { x: null, y: null }, Right: { x: null, y: null } };

// Pinch sizing variables
const startPinchX = { Left: null, Right: null };
const startBrushSize = { Left: 10, Right: 10 };
const smoothBrushSize = { Left: 10.0, Right: 10.0 };

// Button Hover triggers
const hoverStates = {
  Left: { btn: null, time: 0.0, triggered: false },
  Right: { btn: null, time: 0.0, triggered: false }
};

let prevTime = performance.now();

// ==========================================================================
// 5. Utility draw functions
// ==========================================================================
function drawStartupMessage(message, color = "#FFFFFF") {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#121218"; // Dark slate
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "#FF8C00"; // Orange
  ctx.font = "bold 38px 'Outfit', sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("AIR CANVAS PRO", canvas.width / 2, 280);

  ctx.fillStyle = color;
  ctx.font = "500 18px 'Outfit', sans-serif";
  ctx.fillText(message, canvas.width / 2, 380);
}

function getSmoothedCoordinates(x, y, handLabel) {
  const prev = prevCoords[handLabel];
  if (prev.x === null || prev.y === null) {
    prev.x = x;
    prev.y = y;
  } else {
    prev.x = EMA_ALPHA * x + (1 - EMA_ALPHA) * prev.x;
    prev.y = EMA_ALPHA * y + (1 - EMA_ALPHA) * prev.y;
  }
  return { x: Math.round(prev.x), y: Math.round(prev.y) };
}

function resetCoordsFilter(handLabel) {
  if (handLabel) {
    prevCoords[handLabel] = { x: null, y: null };
  } else {
    prevCoords.Left = { x: null, y: null };
    prevCoords.Right = { x: null, y: null };
  }
}

// ==========================================================================
// 6. MediaPipe Gesture Detection
// ==========================================================================
function getFingersUp(landmarks, handednessLabel) {
  const fingers = [0, 0, 0, 0, 0];
  const tipIds = [4, 8, 12, 16, 20];
  const pipIds = [3, 6, 10, 14, 18];

  // Thumb: Horizontal comparison (un-mirrored space)
  if (handednessLabel === "Right") {
    fingers[0] = landmarks[tipIds[0]].x < landmarks[pipIds[0]].x ? 1 : 0;
  } else {
    fingers[0] = landmarks[tipIds[0]].x > landmarks[pipIds[0]].x ? 1 : 0;
  }

  // Vertical comparisons (y decreases upwards in browser)
  for (let i = 1; i < 5; i++) {
    fingers[i] = landmarks[tipIds[i]].y < landmarks[pipIds[i]].y ? 1 : 0;
  }

  return fingers;
}

function detectGesture(landmarks, handednessLabel) {
  const fingers = getFingersUp(landmarks, handednessLabel);

  // 1. Pinch Size Adjustment (highest priority)
  const thumbTip = landmarks[4];
  const indexTip = landmarks[8];
  // Convert relative coordinates back to screen pixels
  const pinchDist = Math.hypot((indexTip.x - thumbTip.x) * FRAME_WIDTH, (indexTip.y - thumbTip.y) * FRAME_HEIGHT);

  const indexKnuckle = landmarks[5];
  const indexExtDist = Math.hypot((indexTip.x - indexKnuckle.x) * FRAME_WIDTH, (indexTip.y - indexKnuckle.y) * FRAME_HEIGHT);

  // Check pinch criteria
  if (pinchDist < 38 && indexExtDist > 42 && fingers[2] === 0 && fingers[3] === 0 && fingers[4] === 0) {
    return GESTURE_PINCH;
  }

  // 2. Closed Fist (all 5 fingers folded) = Eraser
  if (fingers[0] === 0 && fingers[1] === 0 && fingers[2] === 0 && fingers[3] === 0 && fingers[4] === 0) {
    return GESTURE_ERASE;
  }

  // 3. Index Finger Only = Drawing
  if (fingers[0] === 0 && fingers[1] === 1 && fingers[2] === 0 && fingers[3] === 0 && fingers[4] === 0) {
    return GESTURE_DRAW;
  }

  // 4. Open Palm = Pause (Idle)
  if (fingers[0] === 1 && fingers[1] === 1 && fingers[2] === 1 && fingers[3] === 1 && fingers[4] === 1) {
    return GESTURE_IDLE;
  }

  // Default
  return GESTURE_IDLE;
}

// ==========================================================================
// 7. Interactive GUI Bounding Boxes & Hovers
// ==========================================================================
function getActiveButtons() {
  const selectQuery = canvasManager.mode === "Shared" ? ".shared-dock .btn" : ".split-dock .btn";
  return Array.from(document.querySelectorAll(selectQuery));
}

function checkButtonHovers(indexX, indexY, handLabel, dt) {
  const canvasRect = canvas.getBoundingClientRect();
  
  // Map drawing coordinates to DOM client space
  const screenX = canvasRect.left + (indexX / FRAME_WIDTH) * canvasRect.width;
  const screenY = canvasRect.top + (indexY / FRAME_HEIGHT) * canvasRect.height;

  // Real-time hover slider checks
  const sliderSelector = canvasManager.mode === "Shared" ? "#slider-shared" : (handLabel === "Left" ? "#slider-p1" : "#slider-p2");
  const sliderEl = document.querySelector(sliderSelector);
  if (sliderEl) {
    const sRect = sliderEl.getBoundingClientRect();
    // Allow horizontal adjustment when hovering the track
    if (screenX >= sRect.left && screenX <= sRect.right && screenY >= sRect.top - 8 && screenY <= sRect.bottom + 8) {
      const percentage = Math.max(0, Math.min(1, (screenX - sRect.left) / sRect.width));
      const min = parseFloat(sliderEl.min);
      const max = parseFloat(sliderEl.max);
      const newVal = Math.round(min + percentage * (max - min));
      canvasManager.setBrushThickness(newVal, handLabel);
      return; // Skip button hovers if sliding
    }
  }

  // Button hover lock loops
  const buttons = getActiveButtons();
  let hoveredBtn = null;

  for (const btn of buttons) {
    // If in Split mode, players can only hover their own side
    if (canvasManager.mode === "Split") {
      const btnHand = btn.getAttribute("data-player");
      if (btnHand && btnHand !== handLabel) continue;
    }

    const rect = btn.getBoundingClientRect();
    if (screenX >= rect.left && screenX <= rect.right && screenY >= rect.top && screenY <= rect.bottom) {
      hoveredBtn = btn;
      break;
    }
  }

  const hState = hoverStates[handLabel];
  if (hoveredBtn) {
    if (hState.btn === hoveredBtn) {
      if (!hState.triggered) {
        hState.time += dt;
        if (hState.time >= HOVER_LOCK_DURATION) {
          hoveredBtn.click();
          hState.triggered = true;
        }
      }
    } else {
      hState.btn = hoveredBtn;
      hState.time = 0.0;
      hState.triggered = false;
    }
  } else {
    hState.btn = null;
    hState.time = 0.0;
    hState.triggered = false;
  }
}

// ==========================================================================
// 8. Main Application Loop
// ==========================================================================
function loop(timestamp) {
  const dt = (timestamp - prevTime) / 1000;
  prevTime = timestamp;

  if (!video.videoWidth) {
    animationFrameId = requestAnimationFrame(loop);
    return;
  }

  // 1. Draw mirrored video feed frame
  ctx.save();
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  ctx.restore();

  // 2. Perform Hand Landmarking
  const results = tracker.detectForVideo(video, timestamp);
  
  // Map active hands
  const detectedHands = {};
  if (results.landmarks) {
    results.landmarks.forEach((lms, idx) => {
      const handedness = results.handednesses[idx][0].categoryName;
      let label = handedness; // Left or Right

      // In Split Screen, split strictly by screen X
      if (canvasManager.mode === "Split") {
        // Mirrored coordinate check
        const rawIndexX = (1 - lms[8].x) * canvas.width;
        label = rawIndexX < canvas.width / 2 ? "Left" : "Right";
      }
      
      detectedHands[label] = { landmarks: lms, rawLabel: handedness };
    });
  }

  // Reset coordinate smoothing if no hands detected
  if (Object.keys(detectedHands).length === 0) {
    resetCoordsFilter();
  }

  const handStates = { Left: GESTURE_IDLE, Right: GESTURE_IDLE };
  const cursorsToRender = {};

  // 3. Process each hand stream
  for (const handLabel of ["Left", "Right"]) {
    const isDetected = !!detectedHands[handLabel];
    let indexX = 0;
    let indexY = 0;
    let rawGesture = GESTURE_IDLE;

    if (isDetected) {
      handLostTimes[handLabel] = null;
      
      const payload = detectedHands[handLabel];
      const lms = payload.landmarks;
      
      rawGesture = detectGesture(lms, payload.rawLabel);
      
      // Calculate mirrored x coordinate
      const rawX = (1 - lms[8].x) * canvas.width;
      const rawY = lms[8].y * canvas.height;

      const smoothed = getSmoothedCoordinates(rawX, rawY, handLabel);
      indexX = smoothed.x;
      indexY = smoothed.y;

      // Track velocity vector
      if (lastTrackedPositions[handLabel] && dt > 0) {
        const prevPos = lastTrackedPositions[handLabel];
        velocities[handLabel].x = (indexX - prevPos.x) / dt;
        velocities[handLabel].y = (indexY - prevPos.y) / dt;
      }
      lastTrackedPositions[handLabel] = { x: indexX, y: indexY };
    } else {
      rawGesture = GESTURE_IDLE;
    }

    // Gesture Debouncing state machine (grace periods + counters)
    let activeGesture = GESTURE_IDLE;
    if (!isDetected && (prevGestures[handLabel] === GESTURE_DRAW || prevGestures[handLabel] === GESTURE_ERASE)) {
      if (handLostTimes[handLabel] === null) {
        handLostTimes[handLabel] = timestamp / 1000;
      }
      const elapsed = (timestamp / 1000) - handLostTimes[handLabel];
      if (elapsed <= GRACE_PERIOD) {
        // Continue drawing using predictive velocities
        activeGesture = prevGestures[handLabel];
        const vel = velocities[handLabel];
        const lastPos = lastTrackedPositions[handLabel];
        if (lastPos) {
          indexX = Math.max(0, Math.min(canvas.width - 1, lastPos.x + vel.x * elapsed));
          indexY = Math.max(0, Math.min(canvas.height - 1, lastPos.y + vel.y * elapsed));
        }
      } else {
        activeGesture = GESTURE_IDLE;
        currentStates[handLabel] = GESTURE_IDLE;
        consecutiveCounts[handLabel] = 0;
      }
    } else {
      // Standard asymmetric stabilization filters (5 frames enter, 8 frames exit)
      if (rawGesture === currentStates[handLabel]) {
        consecutiveCounts[handLabel] = 0;
        pendingGestures[handLabel] = rawGesture;
      } else {
        if (rawGesture === pendingGestures[handLabel]) {
          consecutiveCounts[handLabel]++;
        } else {
          pendingGestures[handLabel] = rawGesture;
          consecutiveCounts[handLabel] = 1;
        }

        const threshold = currentStates[handLabel] === GESTURE_DRAW ? 8 : 5;
        if (consecutiveCounts[handLabel] >= threshold) {
          currentStates[handLabel] = pendingGestures[handLabel];
          consecutiveCounts[handLabel] = 0;
        }
      }
      activeGesture = currentStates[handLabel];
    }

    handStates[handLabel] = activeGesture;

    // Suppress drawing inside top bar (y < 45) or bottom bar (y > 675)
    const isInUiZone = indexY < 45 || indexY > 675;

    // Start/Commit stroke transitions
    if (activeGesture === GESTURE_DRAW && !isInUiZone) {
      if (prevGestures[handLabel] !== GESTURE_DRAW || prevInUiZone[handLabel]) {
        canvasManager.startStroke(handLabel, false);
      }
      if (indexX > 0 || indexY > 0) {
        canvasManager.addPoint(indexX, indexY, handLabel);
      }
    } else if (activeGesture === GESTURE_ERASE && !isInUiZone) {
      if (prevGestures[handLabel] !== GESTURE_ERASE || prevInUiZone[handLabel]) {
        canvasManager.startStroke(handLabel, true);
      }
      if (indexX > 0 || indexY > 0) {
        canvasManager.addPoint(indexX, indexY, handLabel);
      }
    } else {
      if ((prevGestures[handLabel] === GESTURE_DRAW || prevGestures[handLabel] === GESTURE_ERASE) && !prevInUiZone[handLabel]) {
        canvasManager.endStroke(handLabel);
      }
    }

    prevInUiZone[handLabel] = isInUiZone;

    // Pinch Brush Sizing scaling
    if (activeGesture === GESTURE_PINCH && isDetected) {
      if (startPinchX[handLabel] === null) {
        startPinchX[handLabel] = indexX;
        startBrushSize[handLabel] = canvasManager.getThickness(handLabel);
        smoothBrushSize[handLabel] = startBrushSize[handLabel];
      } else {
        const dx = indexX - startPinchX[handLabel];
        const targetSize = Math.max(2, Math.min(50, startBrushSize[handLabel] + dx * 0.15));
        
        smoothBrushSize[handLabel] = 0.25 * targetSize + 0.75 * smoothBrushSize[handLabel];
        canvasManager.setBrushThickness(Math.round(smoothBrushSize[handLabel]), handLabel);
      }
    } else {
      startPinchX[handLabel] = null;
    }

    // Check button hovers in UI zones (when drawing/pointing)
    if (isInUiZone && activeGesture === GESTURE_DRAW && (indexX > 0 || indexY > 0)) {
      checkButtonHovers(indexX, indexY, handLabel, dt);
    } else {
      hoverStates[handLabel].btn = null;
      hoverStates[handLabel].time = 0.0;
      hoverStates[handLabel].triggered = false;
    }

    // Save cursor metadata for drawing
    if (isDetected || ((activeGesture === GESTURE_DRAW || activeGesture === GESTURE_ERASE || activeGesture === GESTURE_PINCH) && lastTrackedPositions[handLabel])) {
      cursorsToRender[handLabel] = { x: indexX, y: indexY, state: activeGesture };
    }

    prevGestures[handLabel] = activeGesture;
  }

  // 4. Render committed canvas layer
  ctx.drawImage(canvasManager.offscreenCanvas, 0, 0);

  // 5. Render Split Divider line
  if (canvasManager.mode === "Split") {
    ctx.beginPath();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(80, 80, 80, 0.6)";
    ctx.moveTo(canvas.width / 2, 45);
    ctx.lineTo(canvas.width / 2, canvas.height - 45);
    ctx.stroke();

    ctx.fillStyle = "rgba(255, 0, 255, 0.7)";
    ctx.font = "500 12px 'Outfit', sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("PLAYER 1", 20, 650);

    ctx.fillStyle = "rgba(0, 255, 255, 0.7)";
    ctx.fillText("PLAYER 2", canvas.width / 2 + 20, 650);
  }

  // 6. Draw Custom cursors
  for (const [handLabel, cursor] of Object.entries(cursorsToRender)) {
    const cx = cursor.x;
    const cy = cursor.y;
    const state = cursor.state;

    const brushSize = canvasManager.getThickness(handLabel);
    const radius = Math.max(5, Math.floor(brushSize / 2));
    const isEraser = canvasManager.getEraserMode(handLabel);
    const color = canvasManager.getColor(handLabel);

    const borderClr = handLabel === "Right" ? varP2Accent() : varP1Accent();
    const textClr = borderClr;
    const labelChar = handLabel === "Right" ? "R" : "L";

    const isInUi = cy < 45 || cy > 675;

    if (isInUi && state === GESTURE_DRAW) {
      // Draw standard pointer cursor inside menus
      ctx.beginPath();
      ctx.lineWidth = 2;
      ctx.strokeStyle = borderClr;
      ctx.arc(cx, cy, 10, 0, Math.PI * 2);
      ctx.stroke();

      ctx.beginPath();
      ctx.fillStyle = borderClr;
      ctx.arc(cx, cy, 2, 0, Math.PI * 2);
      ctx.fill();

      // Render circular hover loader
      const hState = hoverStates[handLabel];
      if (hState.btn && !hState.triggered) {
        const progress = Math.min(1.0, hState.time / HOVER_LOCK_DURATION);
        ctx.beginPath();
        ctx.lineWidth = 2;
        ctx.strokeStyle = borderClr;
        ctx.arc(cx, cy, 15, -Math.PI / 2, -Math.PI / 2 + progress * Math.PI * 2);
        ctx.stroke();
      }
    } else {
      // Draw state-specific cursors
      if (state === GESTURE_DRAW) {
        if (isEraser) {
          ctx.beginPath();
          ctx.lineWidth = 2;
          ctx.strokeStyle = COLOR_WHITE;
          ctx.arc(cx, cy, radius, 0, Math.PI * 2);
          ctx.stroke();

          ctx.beginPath();
          ctx.lineWidth = 1;
          ctx.strokeStyle = borderClr;
          ctx.arc(cx, cy, radius + 2, 0, Math.PI * 2);
          ctx.stroke();
        } else {
          ctx.beginPath();
          ctx.fillStyle = color;
          ctx.arc(cx, cy, radius, 0, Math.PI * 2);
          ctx.fill();

          ctx.beginPath();
          ctx.lineWidth = 1;
          ctx.strokeStyle = borderClr;
          ctx.arc(cx, cy, radius + 3, 0, Math.PI * 2);
          ctx.stroke();
        }
      } else if (state === GESTURE_ERASE) {
        const eraserSize = radius * 2 + 8;
        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = COLOR_WHITE;
        ctx.arc(cx, cy, eraserSize, 0, Math.PI * 2);
        ctx.stroke();

        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = borderClr;
        ctx.arc(cx, cy, eraserSize + 3, 0, Math.PI * 2);
        ctx.stroke();

        ctx.beginPath();
        ctx.fillStyle = borderClr;
        ctx.arc(cx, cy, 3, 0, Math.PI * 2);
        ctx.fill();
      } else if (state === GESTURE_PINCH) {
        ctx.beginPath();
        ctx.fillStyle = color;
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.fill();

        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = COLOR_WHITE;
        ctx.arc(cx, cy, radius + 4, 0, Math.PI * 2);
        ctx.stroke();

        ctx.fillStyle = COLOR_WHITE;
        ctx.font = "500 11px 'Outfit', sans-serif";
        ctx.textAlign = "left";
        ctx.fillText(`SIZE: ${brushSize}px`, cx + 15, cy + 4);
      } else {
        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = borderClr;
        ctx.arc(cx, cy, 5, 0, Math.PI * 2);
        ctx.stroke();

        ctx.beginPath();
        ctx.fillStyle = borderClr;
        ctx.arc(cx, cy, 1, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Label character
    ctx.fillStyle = textClr;
    ctx.font = "bold 12px 'Outfit', sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(labelChar, cx + 12, cy - 12);
  }

  // 7. Update bottom status bar labels
  updateStatusBarTexts(handStates);

  animationFrameId = requestAnimationFrame(loop);
}

// Helpers to read CSS variables for colors dynamically
function varP1Accent() { return getComputedStyle(document.documentElement).getPropertyValue('--p1-accent').trim(); }
function varP2Accent() { return getComputedStyle(document.documentElement).getPropertyValue('--p2-accent').trim(); }

function getFriendlyModeLabel(state) {
  if (state === GESTURE_DRAW) return "DRAW MODE";
  if (state === GESTURE_ERASE) return "ERASER MODE";
  if (state === GESTURE_PINCH) return "BRUSH SIZE MODE";
  return "PAUSE MODE";
}

function updateStatusBarTexts(handStates) {
  const getLabelClass = (state) => {
    if (state === GESTURE_DRAW) return "value mode-draw";
    if (state === GESTURE_ERASE) return "value mode-erase";
    if (state === GESTURE_PINCH) return "value mode-pinch";
    return "value mode-pause";
  };

  const lStateElShared = document.getElementById("l-state-shared");
  const rStateElShared = document.getElementById("r-state-shared");
  if (lStateElShared && rStateElShared) {
    lStateElShared.textContent = getFriendlyModeLabel(handStates.Left);
    lStateElShared.className = getLabelClass(handStates.Left);
    rStateElShared.textContent = getFriendlyModeLabel(handStates.Right);
    rStateElShared.className = getLabelClass(handStates.Right);
  }

  const lStateElSplit = document.getElementById("l-state-split");
  const rStateElSplit = document.getElementById("r-state-split");
  if (lStateElSplit && rStateElSplit) {
    lStateElSplit.textContent = getFriendlyModeLabel(handStates.Left);
    lStateElSplit.className = getLabelClass(handStates.Left);
    rStateElSplit.textContent = getFriendlyModeLabel(handStates.Right);
    rStateElSplit.className = getLabelClass(handStates.Right);
  }
}

// ==========================================================================
// 9. Init & Lifecycle Actions
// ==========================================================================
async function init() {
  try {
    drawStartupMessage("Initializing Camera...");
    
    // Request Camera Stream
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: 1280,
        height: 720,
        facingMode: "user"
      }
    });
    
    video.srcObject = stream;
    // Wait for video to load metadata before executing MediaPipe loader
    await new Promise((resolve) => {
      video.onloadedmetadata = () => resolve();
    });
    
    drawStartupMessage("Loading Hand Tracking...");

    // Initialize MediaPipe vision bundle resolver
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.8/wasm"
    );

    // Create Hand Landmarker Instance
    tracker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
        delegate: "GPU"
      },
      runningMode: "VIDEO",
      numHands: 2
    });

    // Start drawing frame updates
    canvasManager.syncUI();
    prevTime = performance.now();
    animationFrameId = requestAnimationFrame(loop);

  } catch (err) {
    console.error(err);
    let errorMsg = "Unable to access webcam.";
    if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
      errorMsg = "Camera not detected.";
    } else if (err.message && err.message.includes("HandLandmarker")) {
      errorMsg = "Hand tracking initialization failed.";
    }
    
    drawStartupMessage(errorMsg + " Please check connections and refresh.", "#FF3C3C");
  }
}

// ==========================================================================
// 10. Event Handlers & Button Listeners
// ==========================================================================
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch((err) => {
      console.error(`Error attempting to enable full-screen mode: ${err.message}`);
    });
  } else {
    document.exitFullscreen();
  }
}

// UI range slider inputs listeners
document.getElementById("slider-shared").addEventListener("input", (e) => {
  canvasManager.setBrushThickness(parseInt(e.target.value));
});
document.getElementById("slider-p1").addEventListener("input", (e) => {
  canvasManager.setBrushThickness(parseInt(e.target.value), "Left");
});
document.getElementById("slider-p2").addEventListener("input", (e) => {
  canvasManager.setBrushThickness(parseInt(e.target.value), "Right");
});

// Event Delegation for Button actions
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".btn");
  if (!btn) return;

  const type = btn.getAttribute("data-type");
  const val = btn.getAttribute("data-val");
  const player = btn.getAttribute("data-player"); // Left or Right or null

  if (type === "color") {
    canvasManager.setBrushColor(val, player);
  } else if (type === "toggle" && val === "eraser") {
    const isEraser = canvasManager.getEraserMode(player);
    canvasManager.setEraserMode(!isEraser, player);
  } else if (type === "action") {
    switch (val) {
      case "undo":
        canvasManager.undo(player);
        break;
      case "redo":
        canvasManager.redo(player);
        break;
      case "clear":
        canvasManager.clear(player);
        break;
      case "toggle_mode":
        const nextMode = canvasManager.mode === "Shared" ? "Split" : "Shared";
        canvasManager.setMode(nextMode);
        break;
      case "fullscreen":
        toggleFullscreen();
        break;
      case "exit":
        // Shut down the application session
        if (stream) {
          stream.getTracks().forEach(track => track.stop());
        }
        if (tracker) {
          tracker.close();
        }
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId);
        }
        drawStartupMessage("Air Canvas Pro Session Ended.", "#8A8A93");
        break;
    }
  }
});

// Global Keyboard event listeners
window.addEventListener("keydown", (e) => {
  const key = e.key.toLowerCase();
  
  if (key === "escape") {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    }
  } else if (key === "q") {
    // Quit application
    const exitBtn = document.querySelector(".btn[data-val='exit']");
    if (exitBtn) exitBtn.click();
  } else if (key === "f") {
    toggleFullscreen();
  } else if (key === "m") {
    const nextMode = canvasManager.mode === "Shared" ? "Split" : "Shared";
    canvasManager.setMode(nextMode);
  } else if (key === "c") {
    canvasManager.clear();
  } else if (key === "u") {
    canvasManager.undo();
  } else if (key === "r") {
    canvasManager.redo();
  } else if (key === "e") {
    if (canvasManager.mode === "Shared") {
      const isEraser = canvasManager.getEraserMode();
      canvasManager.setEraserMode(!isEraser);
    } else {
      // Toggle for both hands if active
      ["Left", "Right"].forEach(h => {
        const isEraser = canvasManager.getEraserMode(h);
        canvasManager.setEraserMode(!isEraser, h);
      });
    }
  } else if (["1", "2", "3", "4"].includes(key)) {
    const colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00"];
    const colorHex = colors[parseInt(key) - 1];
    if (canvasManager.mode === "Shared") {
      canvasManager.setBrushColor(colorHex);
    } else {
      canvasManager.setBrushColor(colorHex, "Left");
      canvasManager.setBrushColor(colorHex, "Right");
    }
  } else if (key === "[") {
    if (canvasManager.mode === "Shared") {
      const nextSize = Math.max(2, canvasManager.activeThickness - 2);
      canvasManager.setBrushThickness(nextSize);
    } else {
      ["Left", "Right"].forEach(h => {
        const nextSize = Math.max(2, canvasManager.activeThicknesses[h] - 2);
        canvasManager.setBrushThickness(nextSize, h);
      });
    }
  } else if (key === "]") {
    if (canvasManager.mode === "Shared") {
      const nextSize = Math.min(50, canvasManager.activeThickness + 2);
      canvasManager.setBrushThickness(nextSize);
    } else {
      ["Left", "Right"].forEach(h => {
        const nextSize = Math.min(50, canvasManager.activeThicknesses[h] + 2);
        canvasManager.setBrushThickness(nextSize, h);
      });
    }
  }
});

// Run Init immediately
init();
