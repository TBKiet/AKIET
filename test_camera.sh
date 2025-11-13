#!/bin/bash
# Script test camera pipeline cho JetBot 2GB

WIDTH=320
HEIGHT=240
EXPECTED_SIZE=$((WIDTH * HEIGHT * 4))

echo "Testing GStreamer camera pipeline..."
echo "Expected frame size: $EXPECTED_SIZE bytes (${WIDTH}x${HEIGHT} RGBA)"
echo ""

# Test 1: Kiểm tra camera có hoạt động không
echo "Test 1: Checking camera device..."
if ! ls /dev/video* > /dev/null 2>&1; then
    echo "ERROR: No camera device found!"
    exit 1
fi
echo "✓ Camera device found"

# Test 2: Test pipeline với fakesink
echo ""
echo "Test 2: Testing pipeline with fakesink (5 seconds)..."
timeout 5 gst-launch-1.0 \
    nvarguscamerasrc sensor-mode=0 num-buffers=10 ! \
    "video/x-raw(memory:NVMM),width=${WIDTH},height=${HEIGHT},framerate=15/1,format=NV12" ! \
    nvvidconv ! "video/x-raw,format=BGRx" ! \
    videoconvert ! "video/x-raw,format=RGBA,width=${WIDTH},height=${HEIGHT}" ! \
    fakesink

if [ $? -eq 0 ] || [ $? -eq 124 ]; then
    echo "✓ Pipeline works"
else
    echo "✗ Pipeline failed"
    exit 1
fi

# Test 3: Test output size
echo ""
echo "Test 3: Testing actual output size..."
TEMP_FILE=$(mktemp)

timeout 3 gst-launch-1.0 \
    nvarguscamerasrc sensor-mode=0 num-buffers=2 ! \
    "video/x-raw(memory:NVMM),width=${WIDTH},height=${HEIGHT},framerate=15/1,format=NV12" ! \
    nvvidconv ! "video/x-raw,format=BGRx" ! \
    videoconvert ! "video/x-raw,format=RGBA,width=${WIDTH},height=${HEIGHT}" ! \
    fdsink sync=false fd=1 > "$TEMP_FILE" 2>/dev/null

ACTUAL_SIZE=$(stat -f%z "$TEMP_FILE" 2>/dev/null || stat -c%s "$TEMP_FILE" 2>/dev/null)
rm -f "$TEMP_FILE"

echo "Expected size per frame: $EXPECTED_SIZE bytes"
echo "Actual output size: $ACTUAL_SIZE bytes"

# Check if size is multiple of expected (should be 2 frames)
if [ $((ACTUAL_SIZE % EXPECTED_SIZE)) -eq 0 ]; then
    NUM_FRAMES=$((ACTUAL_SIZE / EXPECTED_SIZE))
    echo "✓ Output size is correct ($NUM_FRAMES frames captured)"
else
    echo "✗ Output size mismatch! This indicates stride padding issue."
    ACTUAL_FRAME_SIZE=$((ACTUAL_SIZE / 2))
    ACTUAL_STRIDE=$((ACTUAL_FRAME_SIZE / HEIGHT))
    echo "  Actual frame size: $ACTUAL_FRAME_SIZE bytes"
    echo "  Calculated stride: $ACTUAL_STRIDE bytes (expected: $((WIDTH * 4)))"
    exit 1
fi

echo ""
echo "All tests passed! ✓"
echo ""
echo "You can now run: dotnet run"
