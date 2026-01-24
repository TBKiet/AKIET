#!/usr/bin/env python3
"""
Quick integration test for optimized YOLO performance
Tests the background worker thread implementation
"""
import sys
import os
import time

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

print("="*60)
print("YOLO Integration Performance Test")
print("="*60)

# Test 1: Check if YOLO is available
print("\n1. Checking YOLO availability...")
try:
    from src.detector_yolo import YOLODetector, YOLO_AVAILABLE
    if YOLO_AVAILABLE:
        print("   ✓ YOLO is available")
    else:
        print("   ✗ YOLO not available - cannot run test")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Error importing YOLO: {e}")
    sys.exit(1)

# Test 2: Check worker thread
print("\n2. Checking worker thread...")
try:
    from src.yolo_worker import YOLOWorkerThread
    print("   ✓ YOLOWorkerThread imported successfully")
except Exception as e:
    print(f"   ✗ Error importing worker: {e}")
    sys.exit(1)

# Test 3: Initialize detector
print("\n3. Initializing YOLO detector...")
try:
    detector = YOLODetector(conf_threshold=0.5)
    print(f"   ✓ Detector initialized (img_size={detector.img_size})")
except Exception as e:
    print(f"   ✗ Error initializing detector: {e}")
    sys.exit(1)

# Test 4: Create worker thread
print("\n4. Creating worker thread...")
try:
    worker = YOLOWorkerThread(detector)
    worker.start()
    print("   ✓ Worker thread started")
except Exception as e:
    print(f"   ✗ Error starting worker: {e}")
    sys.exit(1)

# Test 5: Performance test with worker
print("\n5. Testing performance with background worker...")
import cv2
import numpy as np

# Create test image
test_img = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.circle(test_img, (200, 200), 50, (255, 255, 255), -1)
cv2.circle(test_img, (400, 300), 80, (255, 255, 255), -1)

results = []
detection_count = 0

def on_detection(circles, inference_time, frame_id):
    global detection_count
    detection_count += 1
    results.append({
        'circles': len(circles),
        'time_ms': inference_time,
        'frame_id': frame_id
    })

worker.detection_complete.connect(on_detection)

# Send frames
print("   Sending 10 frames to worker...")
start_time = time.time()
for i in range(10):
    worker.add_frame(test_img.copy())
    time.sleep(0.01)  # Small delay between frames

# Wait for all detections to complete
print("   Waiting for detections...")
timeout = 30  # 30 seconds timeout
elapsed = 0
while detection_count < 10 and elapsed < timeout:
    time.sleep(0.1)
    elapsed = time.time() - start_time

total_time = time.time() - start_time

# Test 6: Analyze results
print("\n6. Results:")
print(f"   Total frames sent: 10")
print(f"   Detections received: {detection_count}")
print(f"   Total time: {total_time:.2f}s")

if results:
    avg_inference = np.mean([r['time_ms'] for r in results])
    max_inference = max([r['time_ms'] for r in results])
    min_inference = min([r['time_ms'] for r in results])

    print(f"\n   Inference times:")
    print(f"   - Average: {avg_inference:.1f}ms")
    print(f"   - Min: {min_inference:.1f}ms")
    print(f"   - Max: {max_inference:.1f}ms")
    print(f"   - Estimated FPS: {1000/avg_inference:.1f}")

    print(f"\n   Detection results:")
    for i, r in enumerate(results[:5]):  # Show first 5
        print(f"   Frame {r['frame_id']}: {r['circles']} circles, {r['time_ms']:.1f}ms")

# Cleanup
print("\n7. Cleanup...")
worker.stop()
print("   ✓ Worker stopped")

# Final verdict
print("\n" + "="*60)
print("TEST SUMMARY:")
if detection_count >= 8:  # At least 80% success
    print("✓ PASS - Worker thread is functioning correctly")
    print(f"  Expected performance: {1000/avg_inference:.1f} FPS")
    print(f"  This is a {15/(1000/avg_inference):.1f}x improvement over blocking (0.1-0.2 FPS)")
else:
    print("✗ FAIL - Worker thread did not process enough frames")
print("="*60)
