#!/bin/bash
# Test script to dump first bytes from camera

echo "Testing BGRx format..."
timeout 2 gst-launch-1.0 nvarguscamerasrc num-buffers=1 ! \
  video/x-raw\(memory:NVMM\),width=320,height=240,framerate=30/1 ! \
  nvvidconv ! video/x-raw,format=BGRx ! \
  fdsink fd=1 2>/dev/null | head -c 100 | od -A x -t x1z -v

echo ""
echo "Testing RGBA format..."
timeout 2 gst-launch-1.0 nvarguscamerasrc num-buffers=1 ! \
  video/x-raw\(memory:NVMM\),width=320,height=240,framerate=30/1 ! \
  nvvidconv ! video/x-raw,format=RGBA ! \
  fdsink fd=1 2>/dev/null | head -c 100 | od -A x -t x1z -v

