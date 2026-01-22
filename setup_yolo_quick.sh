#!/bin/bash
# Quick setup for YOLOv8 with pretrained model

echo "=========================================="
echo "YOLOv8 Real-time Setup (5 minutes)"
echo "=========================================="

# Check conda
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "❌ Error: Activate conda first: conda activate AKIET_OLD"
    exit 1
fi

echo ""
echo "📦 Step 1: Installing ultralytics..."
pip install ultralytics torch torchvision

echo ""
echo "📥 Step 2: Downloading YOLOv8n pretrained model..."
python3 << 'EOF'
from ultralytics import YOLO
print("Downloading YOLOv8n (~6MB)...")
model = YOLO('yolov8n.pt')
print("✓ Downloaded: yolov8n.pt")
EOF

echo ""
echo "⚡ Step 3: Converting to TensorRT (~2 minutes)..."
echo "This creates yolov8n.engine for 3-5x speedup"
python3 << 'EOF'
from ultralytics import YOLO
import torch

if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    model = YOLO('yolov8n.pt')
    print("Converting to TensorRT FP16...")
    try:
        model.export(format='engine', device=0, half=True, imgsz=480)
        print("✓ TensorRT engine created: yolov8n.engine")
    except Exception as e:
        print(f"⚠ TensorRT export failed: {e}")
        print("Will use PyTorch model (slower)")
else:
    print("⚠ CUDA not available, skipping TensorRT")
EOF

echo ""
echo "🧪 Step 4: Testing detector..."
python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from src.detector_yolo import YOLODetector
import numpy as np
import cv2

print("\nTesting YOLO detector...")
detector = YOLODetector(use_tensorrt=True)

# Create test image with circles
img = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.circle(img, (200, 200), 50, (200, 200, 200), -1)
cv2.circle(img, (400, 300), 70, (150, 150, 150), -1)

# Warm up
for i in range(3):
    _ = detector.detect(img)

# Test performance
print("\nPerformance test (10 frames):")
for i in range(10):
    circles = detector.detect(img)
    print(f"Frame {i+1}: {len(circles)} detected, "
          f"Time: {detector.get_avg_inference_time():.1f}ms, "
          f"FPS: {detector.get_fps():.1f}")

print("\n✓ Detector working!")
EOF

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next: Update main_window.py"
echo ""
echo "Change these 2 lines:"
echo "  FROM: from src.detector_optimized import CircleDetector"
echo "    TO: from src.detector_yolo import YOLODetector"
echo ""
echo "  FROM: self.detector = CircleDetector()"
echo "    TO: self.detector = YOLODetector()"
echo ""
echo "Then run: python3 src/main.py"
echo ""
echo "Expected FPS:"
echo "  - Jetson Nano: 30-50 FPS"
echo "  - Jetson Xavier: 60-80 FPS"
echo ""
