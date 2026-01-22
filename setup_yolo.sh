#!/bin/bash
# Setup script for YOLO detector on Jetson

echo "=========================================="
echo "Setting up YOLOv8 + TensorRT for Jetson"
echo "=========================================="

# Check if conda env is active
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "Error: Please activate conda environment first"
    echo "Run: conda activate AKIET_OLD"
    exit 1
fi

echo ""
echo "Step 1: Installing ultralytics..."
pip install ultralytics

echo ""
echo "Step 2: Downloading YOLOv8n model..."
python3 << EOF
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
print("✓ YOLOv8n downloaded")
EOF

echo ""
echo "Step 3: Converting to TensorRT (this may take 2-3 minutes)..."
python3 << EOF
from ultralytics import YOLO
import torch

print("PyTorch CUDA available:", torch.cuda.is_available())
print("CUDA device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None")

model = YOLO('yolov8n.pt')
print("Exporting to TensorRT...")
model.export(format='engine', device=0, half=True)
print("✓ TensorRT engine created: yolov8n.engine")
EOF

echo ""
echo "Step 4: Testing detector..."
python3 src/detector_yolo.py

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update main_window.py to use YOLODetector"
echo "2. Run: python3 src/main.py"
echo ""
echo "For custom disc detection model:"
echo "1. Collect disc images"
echo "2. Label with YOLO format"
echo "3. Train: yolo train data=disc.yaml model=yolov8n.pt epochs=100"
echo "4. Use trained model in detector_yolo.py"
echo ""
