#!/usr/bin/env python3
"""
Quick test to diagnose YOLOv5 speed issues
"""
import sys
import time
import numpy as np
import cv2

sys.path.insert(0, 'yolov5')

import torch
from models.common import DetectMultiBackend
from utils.torch_utils import select_device

print("="*60)
print("YOLOv5 Speed Test")
print("="*60)

# Setup
device = select_device('0')
img_size = 480

print(f"\n1. Loading model...")
model = DetectMultiBackend('yolov5n.pt', device=device)
print(f"   Model loaded on: {device}")

# Try FP16
try:
    model.half()
    use_half = True
    print(f"   Using FP16: Yes")
except:
    use_half = False
    print(f"   Using FP16: No")

# Create test image
test_img = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.circle(test_img, (200, 200), 50, (255, 255, 255), -1)
cv2.circle(test_img, (400, 300), 80, (255, 255, 255), -1)

print(f"\n2. Testing preprocessing...")
times_preprocess = []
for i in range(10):
    start = time.time()

    # Preprocess (như trong detector_yolo.py)
    img = cv2.resize(test_img, (img_size, img_size))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.transpose((2, 0, 1))
    img = np.ascontiguousarray(img)
    img_tensor = torch.from_numpy(img).to(device)
    img_tensor = img_tensor.half() if use_half else img_tensor.float()
    img_tensor /= 255.0
    if img_tensor.ndimension() == 3:
        img_tensor = img_tensor.unsqueeze(0)

    elapsed = time.time() - start
    times_preprocess.append(elapsed * 1000)

avg_preprocess = np.mean(times_preprocess[3:])
print(f"   Preprocessing: {avg_preprocess:.1f}ms")

print(f"\n3. Testing inference...")
# Warmup
for i in range(5):
    with torch.no_grad():
        _ = model(img_tensor)

# Test
times_inference = []
for i in range(10):
    start = time.time()
    with torch.no_grad():
        pred = model(img_tensor)
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    elapsed = time.time() - start
    times_inference.append(elapsed * 1000)
    print(f"   Frame {i+1}: {elapsed*1000:.1f}ms")

avg_inference = np.mean(times_inference[3:])
print(f"\n   Average inference: {avg_inference:.1f}ms")

print(f"\n4. Testing full pipeline...")
times_full = []
for i in range(10):
    start = time.time()

    # Full pipeline
    img = cv2.resize(test_img, (img_size, img_size))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.transpose((2, 0, 1))
    img = np.ascontiguousarray(img)
    img_tensor = torch.from_numpy(img).to(device)
    img_tensor = img_tensor.half() if use_half else img_tensor.float()
    img_tensor /= 255.0
    if img_tensor.ndimension() == 3:
        img_tensor = img_tensor.unsqueeze(0)

    with torch.no_grad():
        pred = model(img_tensor)
    torch.cuda.synchronize() if torch.cuda.is_available() else None

    elapsed = time.time() - start
    times_full.append(elapsed * 1000)

avg_full = np.mean(times_full[3:])
fps = 1000 / avg_full

print(f"   Full pipeline: {avg_full:.1f}ms")
print(f"   Expected FPS: {fps:.1f}")

print(f"\n" + "="*60)
print(f"SUMMARY:")
print(f"  Preprocessing: {avg_preprocess:.1f}ms")
print(f"  Inference:     {avg_inference:.1f}ms")
print(f"  Full pipeline: {avg_full:.1f}ms")
print(f"  FPS:           {fps:.1f}")
print("="*60)

if fps < 10:
    print("\n⚠️  WARNING: FPS is very low!")
    print("   Possible issues:")
    print("   - Model not using GPU properly")
    print("   - FP16 not working")
    print("   - Preprocessing bottleneck")
elif fps < 20:
    print("\n✓ FPS is acceptable but could be better")
    print("  Consider:")
    print("  - Export to TensorRT for 2-3x speedup")
    print("  - Reduce image size further (480 -> 416)")
else:
    print("\n✓ FPS is good!")
