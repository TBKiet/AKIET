#!/bin/bash
# Debug camera V4L2 information

echo "=========================================="
echo "Camera V4L2 Debug Information"
echo "=========================================="

# List all video devices
echo -e "\n1. Video Devices:"
ls -l /dev/video* 2>/dev/null || echo "No video devices found"

# Check v4l2 info for video0
if [ -e /dev/video0 ]; then
    echo -e "\n2. Video0 Device Info:"
    v4l2-ctl --device=/dev/video0 --all 2>&1 | head -50

    echo -e "\n3. Supported Formats:"
    v4l2-ctl --device=/dev/video0 --list-formats-ext 2>&1 | head -30

    echo -e "\n4. Current Format:"
    v4l2-ctl --device=/dev/video0 --get-fmt-video

    echo -e "\n5. Try to set format to YUYV 640x480:"
    v4l2-ctl --device=/dev/video0 --set-fmt-video=width=640,height=480,pixelformat=YUYV
    v4l2-ctl --device=/dev/video0 --get-fmt-video

    echo -e "\n6. Try to reset camera controls:"
    v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=128
    v4l2-ctl --device=/dev/video0 --set-ctrl=contrast=128
    v4l2-ctl --device=/dev/video0 --set-ctrl=saturation=128

    echo -e "\n7. Check if camera module is IMX219 (Raspberry Pi Camera):"
    dmesg | grep -i imx219 | tail -5

    echo -e "\n8. Check camera module:"
    lsmod | grep -E 'video|camera|imx'

else
    echo "ERROR: /dev/video0 not found!"
fi

echo -e "\n=========================================="
echo "Recommendations:"
echo "=========================================="
echo "If this is Raspberry Pi Camera (CSI):"
echo "  - Use nvarguscamerasrc (needs GStreamer support)"
echo "  - Current OpenCV doesn't have GStreamer"
echo ""
echo "If this is USB Camera:"
echo "  - Check USB connection"
echo "  - Try different USB port"
echo "  - Check dmesg for errors: dmesg | tail -50"
echo ""
echo "To fix green screen:"
echo "  1. Reconnect camera"
echo "  2. Reboot system"
echo "  3. Check camera with: gst-launch-1.0 v4l2src ! xvimagesink"
