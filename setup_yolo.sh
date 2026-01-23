#!/bin/bash
# Setup script for YOLOv5 detector on Jetson

echo "=========================================="
echo "Setting up YOLOv5 + TensorRT for Jetson"
echo "=========================================="

# Check if conda env is active
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "Error: Please activate conda environment first"
    echo "Run: conda activate AKIET_OLD"
    exit 1
fi

echo ""
echo "Step 1: Cloning YOLOv5 repository..."
if [ ! -d "yolov5" ]; then
    git clone https://github.com/ultralytics/yolov5
    cd yolov5
    pip install -r requirements.txt
    cd ..
else
    echo "✓ YOLOv5 directory already exists"
fi

echo ""
echo "Step 2: Downloading YOLOv5n model..."
python3 << EOF
import torch
print("PyTorch CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("CUDA device:", torch.cuda.get_device_name(0))

# Download YOLOv5n
import sys
sys.path.insert(0, 'yolov5')
from models.common import DetectMultiBackend

model = DetectMultiBackend('yolov5n.pt', device='0' if torch.cuda.is_available() else 'cpu')
print("✓ YOLOv5n downloaded")
EOF

echo ""
echo "Step 3: Converting to TensorRT (optional, may take 2-3 minutes)..."
echo "Run manually: cd yolov5 && python export.py --weights yolov5n.pt --include engine --device 0"

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
