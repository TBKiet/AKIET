#!/usr/bin/env python3
"""
Simple test to verify PyQt5 can display images from OpenCV
"""
import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt

def main():
    app = QApplication(sys.argv)

    # Create a simple test image (red square on blue background)
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    test_img[:, :] = (255, 0, 0)  # Blue background (BGR)
    cv2.rectangle(test_img, (200, 150), (440, 330), (0, 0, 255), -1)  # Red square
    cv2.putText(test_img, "Test Image", (220, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    print(f"Test image shape: {test_img.shape}, dtype: {test_img.dtype}")

    # Convert BGR to RGB
    test_rgb = cv2.cvtColor(test_img, cv2.COLOR_BGR2RGB)
    test_rgb = np.ascontiguousarray(test_rgb)

    h, w, ch = test_rgb.shape
    bytes_per_line = ch * w

    # Create QImage
    q_img = QImage(test_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
    print(f"QImage created: size={q_img.size()}, isNull={q_img.isNull()}")

    # Create window
    window = QMainWindow()
    window.setWindowTitle("PyQt5 Image Display Test")
    window.resize(700, 550)

    # Create label
    label = QLabel()
    label.setMinimumSize(640, 480)
    label.setStyleSheet("background-color: black; border: 2px solid white;")
    label.setAlignment(Qt.AlignCenter)

    # Set pixmap
    pixmap = QPixmap.fromImage(q_img)
    print(f"Pixmap created: size={pixmap.size()}, isNull={pixmap.isNull()}")

    label.setPixmap(pixmap)
    print(f"Pixmap set in label: {not label.pixmap().isNull() if label.pixmap() else 'None'}")

    window.setCentralWidget(label)
    window.show()

    print("\nWindow displayed. You should see:")
    print("- A blue background")
    print("- A red square in the center")
    print("- White text saying 'Test Image'")
    print("\nIf you see a blank/green screen, there's a Qt rendering issue.")
    print("Press Ctrl+C to exit\n")

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
