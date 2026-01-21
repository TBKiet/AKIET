#!/bin/bash
# Script to fix OpenCV + PyQt5 conflict on Jetson

echo "==================================================="
echo "Fixing OpenCV + PyQt5 Qt Plugin Conflict"
echo "==================================================="

# Check current environment
echo ""
echo "Current environment: $(conda info --envs | grep '*' | awk '{print $1}')"
echo ""

# Option 1: Remove opencv-python and install opencv-python-headless
echo "Option 1: Installing opencv-python-headless (no Qt conflicts)"
echo "-----------------------------------------------------------"
pip uninstall opencv-python opencv-contrib-python -y
pip install opencv-python-headless==4.9.0.80

echo ""
echo "Option 2: If Option 1 doesn't work, manually remove cv2 Qt plugins"
echo "-----------------------------------------------------------"
CV2_QT_PATH="$CONDA_PREFIX/lib/python3.8/site-packages/cv2/qt"
if [ -d "$CV2_QT_PATH" ]; then
    echo "Backing up and removing: $CV2_QT_PATH"
    mv "$CV2_QT_PATH" "$CV2_QT_PATH.backup"
    echo "Done! Backed up to: $CV2_QT_PATH.backup"
else
    echo "cv2/qt directory not found (this is good!)"
fi

echo ""
echo "==================================================="
echo "Fix applied! Now test with:"
echo "  python3 test_qt_display.py"
echo "==================================================="
