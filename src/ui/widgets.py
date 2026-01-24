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
                # Fix Qt compatibility
                try:
                    aspect_ratio = Qt.KeepAspectRatio
                    transform = Qt.FastTransformation
                except:
                    aspect_ratio = Qt.AspectRatioMode.KeepAspectRatio
                    transform = Qt.TransformationMode.FastTransformation

                pixmap = pixmap.scaled(self.size(), aspect_ratio, transform)

            self.setPixmap(pixmap)
            self.update()  # Single update, no repaint()

        except Exception as e:
            print(f"Error updating frame: {e}")

class SimulationWidget(QWidget):
    """
    Enhanced 2D top-down robot simulation with professional visuals.
    """
    def __init__(self):
        super().__init__()
        self.setMinimumSize(500, 500)  # Larger for better visibility
        self.setStyleSheet("background-color: #1a1a2e; border: 2px solid #16213e;")

        self.discs = []     # List of dicts: {'x': int, 'y': int, 'radius': int, 'size_class': str}
        self.robot_pos = (50, 450)  # Start position (bottom-left)
        self.robot_path = []
        self.robot_state = "Idle"  # Idle, Moving, Picking, Placing
        self.sorted_count = 0
        self.total_discs = 0

    def set_discs(self, discs):
        """Updates the list of discs to render."""
        self.discs = discs
        self.total_discs = len(discs)
        self.update()

    def set_robot_path(self, path):
        self.robot_path = path
        self.robot_state = "Moving"
        self.update()

    def set_robot_pos(self, x, y):
        self.robot_pos = (x, y)
        self.update()

    def set_robot_state(self, state):
        """Set robot state: Idle, Moving, Picking, Placing"""
        self.robot_state = state
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        # Enable antialiasing for smooth graphics
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
        except:
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            except:
                pass

        # Draw gradient background
        self._draw_gradient_background(painter)

        # Draw work zones (bins)
        self._draw_work_zones(painter)

        # Draw enhanced grid
        self._draw_enhanced_grid(painter)

        # Draw robot path with glow effect
        if self.robot_path:
            self._draw_path_with_glow(painter)

        # Draw discs with enhanced visuals
        for disc in self.discs:
            self._draw_enhanced_disc(painter, disc)

        # Draw robot with better styling
        self._draw_enhanced_robot(painter)

        # Draw status overlay
        self._draw_status_overlay(painter)

    def _draw_gradient_background(self, painter):
        """Draw beautiful gradient background"""
        from PyQt5.QtGui import QLinearGradient

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(26, 26, 46))      # Dark blue-gray
        gradient.setColorAt(1, QColor(22, 33, 62))      # Slightly lighter

        painter.fillRect(self.rect(), gradient)

    def _draw_work_zones(self, painter):
        """Draw sorting bins on the right side"""
        bin_width = 80
        bin_height = 100
        bin_x = self.width() - bin_width - 20
        bin_spacing = 20

        zones = [
            {"label": "Small\n(5cm)", "color": QColor(76, 175, 80), "y": 50},
            {"label": "Medium\n(7cm)", "color": QColor(255, 193, 7), "y": 50 + bin_height + bin_spacing},
            {"label": "Large\n(10cm)", "color": QColor(244, 67, 54), "y": 50 + 2*(bin_height + bin_spacing)}
        ]

        for zone in zones:
            # Draw bin background
            painter.setBrush(QColor(40, 40, 60, 100))
            painter.setPen(QPen(zone["color"], 2))
            painter.drawRect(bin_x, zone["y"], bin_width, bin_height)

            # Draw label
            painter.setPen(zone["color"])
            painter.setFont(QFont('Arial', 10, QFont.Bold))
            painter.drawText(bin_x, zone["y"], bin_width, bin_height,
                           Qt.AlignCenter, zone["label"])

    def _draw_enhanced_grid(self, painter):
        """Draw subtle grid with better styling"""
        painter.setPen(QPen(QColor(50, 50, 80, 80), 1))

        grid_spacing = 50
        for x in range(0, self.width(), grid_spacing):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid_spacing):
            painter.drawLine(0, y, self.width(), y)

        # Draw coordinate labels
        painter.setPen(QColor(100, 100, 120))
        painter.setFont(QFont('Arial', 8))
        for x in range(0, self.width(), grid_spacing * 2):
            painter.drawText(x + 2, 12, f"{x}")
        for y in range(0, self.height(), grid_spacing * 2):
            painter.drawText(2, y + 12, f"{y}")

    def _draw_path_with_glow(self, painter):
        """Draw robot path with glow effect"""
        if not self.robot_path:
            return

        # Glow effect (outer layer)
        painter.setPen(QPen(QColor(0, 255, 0, 50), 6))
        path_points = [QPoint(p[0], p[1]) for p in self.robot_path]
        painter.drawPolyline(path_points)

        # Main path
        try:
            pen_style = Qt.PenStyle.DashLine if hasattr(Qt, 'PenStyle') else Qt.DashLine
        except:
            pen_style = Qt.DashLine
        painter.setPen(QPen(QColor(0, 255, 0), 2, pen_style))
        painter.drawPolyline(path_points)

    def _draw_enhanced_disc(self, painter, disc):
        """Draw disc with gradient, shadow, and label"""
        x, y = disc['x'], disc['y']
        radius = disc.get('radius', 20)
        size_class = disc.get('size_class', 'Unknown')

        # Color mapping
        color_map = {
            'Small (5cm)': QColor(76, 175, 80),   # Green
            'Medium (7cm)': QColor(255, 193, 7),  # Yellow
            'Large (10cm)': QColor(244, 67, 54),  # Red
        }
        base_color = color_map.get(size_class, QColor(150, 150, 150))

        # Draw shadow
        shadow_offset = 3
        painter.setBrush(QColor(0, 0, 0, 80))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(x + shadow_offset, y + shadow_offset),
                          radius, radius)

        # Draw disc with radial gradient (3D effect)
        from PyQt5.QtGui import QRadialGradient
        gradient = QRadialGradient(x - radius//3, y - radius//3, radius * 1.5)
        gradient.setColorAt(0, base_color.lighter(150))
        gradient.setColorAt(0.7, base_color)
        gradient.setColorAt(1, base_color.darker(130))

        painter.setBrush(gradient)
        painter.setPen(QPen(Qt.white, 2))
        painter.drawEllipse(QPoint(x, y), radius, radius)

        # Draw size label
        painter.setPen(Qt.white)
        painter.setFont(QFont('Arial', 12, QFont.Bold))
        label = size_class[0]  # "S", "M", or "L"
        painter.drawText(x - 10, y - 5, 20, 20, Qt.AlignCenter, label)

        # Draw radius in mm (smaller text below)
        radius_mm = disc.get('radius_mm', 0)
        if radius_mm > 0:
            painter.setFont(QFont('Arial', 8))
            painter.drawText(x - 20, y + 15, 40, 15, Qt.AlignCenter,
                           f"{radius_mm:.0f}mm")

    def _draw_enhanced_robot(self, painter):
        """Draw robot with better styling and state indication"""
        x, y = self.robot_pos

        # State-based color
        state_colors = {
            'Idle': QColor(100, 200, 255),      # Cyan
            'Moving': QColor(0, 255, 0),        # Green
            'Picking': QColor(255, 165, 0),     # Orange
            'Placing': QColor(255, 100, 255)    # Magenta
        }
        robot_color = state_colors.get(self.robot_state, QColor(100, 200, 255))

        # Draw glow effect
        from PyQt5.QtGui import QRadialGradient
        glow = QRadialGradient(x, y, 25)
        glow.setColorAt(0, robot_color.lighter(120))
        glow.setColorAt(0.5, robot_color)
        glow.setColorAt(1, QColor(robot_color.red(), robot_color.green(),
                                  robot_color.blue(), 0))
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(x, y), 25, 25)

        # Draw robot body
        painter.setBrush(robot_color)
        painter.setPen(QPen(Qt.white, 2))
        painter.drawEllipse(QPoint(x, y), 15, 15)

        # Draw center dot
        painter.setBrush(Qt.white)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(x, y), 3, 3)

    def _draw_status_overlay(self, painter):
        """Draw status information overlay"""
        # Semi-transparent background
        painter.setBrush(QColor(0, 0, 0, 150))
        painter.setPen(Qt.NoPen)
        painter.drawRect(10, 10, 200, 100)

        # Status text
        painter.setPen(Qt.white)
        painter.setFont(QFont('Arial', 10, QFont.Bold))

        y_offset = 30
        painter.drawText(20, y_offset, "Robot Simulation")

        y_offset += 20
        painter.setFont(QFont('Arial', 9))
        painter.drawText(20, y_offset, f"State: {self.robot_state}")

        y_offset += 18
        painter.drawText(20, y_offset, f"Position: ({self.robot_pos[0]}, {self.robot_pos[1]})")

        y_offset += 18
        painter.drawText(20, y_offset, f"Discs: {self.sorted_count}/{self.total_discs}")

        # Progress bar
        if self.total_discs > 0:
            y_offset += 20
            progress = self.sorted_count / self.total_discs
            bar_width = 160
            painter.setBrush(QColor(50, 50, 50))
            painter.drawRect(20, y_offset, bar_width, 10)
            painter.setBrush(QColor(0, 255, 0))
            painter.drawRect(20, y_offset, int(bar_width * progress), 10)

