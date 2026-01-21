#!/usr/bin/env python3
"""
Test script to check OpenCV GStreamer support on Jetson
"""
import cv2

print("="*60)
print("OpenCV Build Information Check")
print("="*60)

# Check OpenCV version
print(f"\nOpenCV Version: {cv2.__version__}")

# Check GStreamer support
build_info = cv2.getBuildInformation()
has_gstreamer = 'GStreamer' in build_info and 'YES' in build_info

print(f"GStreamer Support: {has_gstreamer}")

if has_gstreamer:
    print("\n✓ OpenCV has GStreamer support!")
else:
    print("\n✗ OpenCV does NOT have GStreamer support!")
    print("\nTo fix this with conda:")
    print("  conda install -c conda-forge opencv")
    print("\nOr use system OpenCV:")
    print("  1. Exit conda: conda deactivate")
    print("  2. Install: sudo apt-get install python3-opencv")
    print("  3. Link to conda env:")
    print("     ln -s /usr/lib/python3/dist-packages/cv2 $CONDA_PREFIX/lib/python3.X/site-packages/")

print("\n" + "="*60)
print("Available Capture Backends")
print("="*60)

backends = [
    (cv2.CAP_GSTREAMER, "GStreamer"),
    (cv2.CAP_V4L2, "V4L2"),
    (cv2.CAP_FFMPEG, "FFmpeg"),
]

for backend_id, backend_name in backends:
    print(f"{backend_name}: {backend_id}")

print("\n" + "="*60)
print("Testing Camera Access")
print("="*60)

# Test 1: V4L2 direct
print("\n1. Testing V4L2 direct (device 0)...")
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"   ✓ V4L2 works! Frame shape: {frame.shape}")
    else:
        print("   ✗ V4L2 opened but cannot read frame")
    cap.release()
else:
    print("   ✗ V4L2 failed to open")

# Test 2: GStreamer test pattern
print("\n2. Testing GStreamer test pattern...")
test_pipeline = "videotestsrc pattern=0 ! video/x-raw,width=640,height=480 ! videoconvert ! appsink"
cap = cv2.VideoCapture(test_pipeline, cv2.CAP_GSTREAMER)
if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"   ✓ GStreamer works! Frame shape: {frame.shape}")
    else:
        print("   ✗ GStreamer opened but cannot read frame")
    cap.release()
else:
    print("   ✗ GStreamer test pattern failed")

# Test 3: V4L2 via GStreamer
print("\n3. Testing V4L2 via GStreamer...")
v4l2_pipeline = "v4l2src device=/dev/video0 ! video/x-raw,width=640,height=480 ! videoconvert ! appsink"
cap = cv2.VideoCapture(v4l2_pipeline, cv2.CAP_GSTREAMER)
if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"   ✓ V4L2+GStreamer works! Frame shape: {frame.shape}")
    else:
        print("   ✗ V4L2+GStreamer opened but cannot read frame")
    cap.release()
else:
    print("   ✗ V4L2+GStreamer failed")

print("\n" + "="*60)
print("Recommendations")
print("="*60)

if has_gstreamer:
    print("\n✓ You have GStreamer support. Camera should work with proper pipeline.")
else:
    print("\n⚠️  Install OpenCV with GStreamer support:")
    print("\n   Option 1: conda-forge (recommended for conda users)")
    print("   $ conda install -c conda-forge opencv")
    print("\n   Option 2: Use system OpenCV and symlink to conda")
    print("   $ sudo apt-get install python3-opencv")
    print("   $ python -c \"import sys; print(sys.path)\"  # Find site-packages")
    print("   $ ln -s /usr/lib/python3/dist-packages/cv2 <conda-site-packages>/")

print("\n")
