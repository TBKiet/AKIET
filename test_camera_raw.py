#!/usr/bin/env python3
"""
Direct camera test - shows raw camera feed without PyQt
"""
import cv2
import numpy as np

print("Opening camera...")
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

if not cap.isOpened():
    print("ERROR: Cannot open camera!")
    exit(1)

# Try to set resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Camera opened successfully!")
print(f"Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
print("\nPress 'q' to quit, 's' to save a frame")
print("Check if camera is covered or pointing at green object!")
print("-" * 60)

frame_count = 0
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame")
        break

    frame_count += 1

    # Resize if too large
    h, w = frame.shape[:2]
    if h > 480 or w > 640:
        scale = min(640 / w, 480 / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        frame = cv2.resize(frame, (new_w, new_h))

    # Calculate color statistics
    b_mean, g_mean, r_mean = frame.mean(axis=(0,1))

    # Add info overlay
    info_frame = frame.copy()
    cv2.putText(info_frame, f"Frame: {frame_count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(info_frame, f"BGR Mean: {b_mean:.0f}, {g_mean:.0f}, {r_mean:.0f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    # Warning if mostly green
    if g_mean > 100 and g_mean > b_mean + 50 and g_mean > r_mean + 50:
        cv2.putText(info_frame, "WARNING: VERY GREEN!", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(info_frame, "Check camera lens/position", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # Show frame
    cv2.imshow('Raw Camera Test - Press Q to quit', info_frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        filename = f'/tmp/camera_test_{frame_count}.jpg'
        cv2.imwrite(filename, frame)
        print(f"Saved: {filename}")

cap.release()
cv2.destroyAllWindows()
print("\nCamera test finished.")
