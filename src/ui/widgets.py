from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
import cv2
import numpy as np

class CameraWidget(QLabel):
    """
    Widget to display the camera feed and overlays.
    """
    def __init__(self):
        super().__init__()
        self.setMinimumSize(320, 240)  # Smaller for tiny display
        self.setStyleSheet("background-color: black;")
        # Fix Qt compatibility
        try:
            self.setAlignment(Qt.AlignCenter)
        except:
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Waiting for Camera...")
        self.setScaledContents(False)

    def update_frame(self, frame_bgr):
        """
        Updates the displayed image from an OpenCV BGR frame.
        Simplified to avoid memory corruption.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return

        try:
            # Clear text on first frame
            if self.text():
                self.setText("")

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w

            # Create QImage with explicit copy
            q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

            # Create pixmap without scaling (faster, safer)
            pixmap = QPixmap.fromImage(q_img)

            # Simple scale to fit
            if pixmap.width() > self.width() or pixmap.height() > self.height():
                pixmap = pixmap.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatio if hasattr(Qt, 'AspectRatioMode') else Qt.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation if hasattr(Qt, 'TransformationMode') else Qt.FastTransformation  # Fast, not smooth
                )

            self.setPixmap(pixmap)
            self.update()  # Single update, no repaint()

        except Exception as e:
            print(f"Error updating frame: {e}")

class SimulationWidget(QWidget):
    """
    Widget to visualize the 2D top-down simulation.
    """
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)
        self.setStyleSheet("background-color: #222; border: 2px solid #444;")
        self.discs = []     # List of dicts: {'x': int, 'y': int, 'radius': int, 'color': QColor}
        self.robot_pos = (50, 350) # Default start position
        self.robot_path = [] # List of (x, y) tuples

    def set_discs(self, discs):
        """
        Updates the list of discs to render.
        """
        self.discs = discs
        self.update()

    def set_robot_path(self, path):
        self.robot_path = path
        self.update()

    def set_robot_pos(self, x, y):
        self.robot_pos = (x, y)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Coordinate Grid
        self._draw_grid(painter)

        # Draw Discs
        for disc in self.discs:
            painter.setBrush(disc.get('color', QColor("gray")))
            painter.setPen(QPen(Qt.white, 2))
            # Transform or just use raw coordinates (assuming 1:1 mapping for simplicity now)
            radius = disc.get('radius', 10)
            painter.drawEllipse(QPoint(disc['x'], disc['y']), radius, radius)

        # Draw Robot Path
        if self.robot_path:
            painter.setPen(QPen(QColor(0, 255, 0), 2, Qt.PenStyle.DashLine if hasattr(Qt, 'PenStyle') else Qt.DashLine))
            path_points = [QPoint(p[0], p[1]) for p in self.robot_path]
            painter.drawPolyline(path_points)

        # Draw Robot
        painter.setBrush(QColor("cyan"))
        painter.setPen(Qt.black)
        painter.drawEllipse(QPoint(self.robot_pos[0], self.robot_pos[1]), 15, 15)

    def _draw_grid(self, painter):
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        for x in range(0, self.width(), 50):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 50):
            painter.drawLine(0, y, self.width(), y)
