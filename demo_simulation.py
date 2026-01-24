#!/usr/bin/env python3
"""
Demo script to showcase the enhanced robot simulation
Tests all Phase 1 visual improvements
"""
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtCore import QTimer
from src.ui.widgets import SimulationWidget
from src.planner import PathPlanner

class SimulationDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Simulation - Phase 1 Demo")
        self.resize(600, 700)

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Add simulation widget
        self.sim = SimulationWidget()
        layout.addWidget(self.sim)

        # Add control buttons
        btn_layout = QHBoxLayout()

        btn_demo1 = QPushButton("Demo 1: Single Disc")
        btn_demo1.clicked.connect(self.demo_single_disc)
        btn_layout.addWidget(btn_demo1)

        btn_demo2 = QPushButton("Demo 2: Multiple Discs")
        btn_demo2.clicked.connect(self.demo_multiple_discs)
        btn_layout.addWidget(btn_demo2)

        btn_demo3 = QPushButton("Demo 3: Sorting Animation")
        btn_demo3.clicked.connect(self.demo_sorting)
        btn_layout.addWidget(btn_demo3)

        layout.addLayout(btn_layout)

        # Animation setup
        self.planner = PathPlanner()
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self._animate)
        self.anim_path = []
        self.anim_idx = 0

        # Auto-start with demo 2
        QTimer.singleShot(500, self.demo_multiple_discs)

    def demo_single_disc(self):
        """Demo with one large disc"""
        discs = [
            {
                'x': 200,
                'y': 200,
                'radius': 40,
                'size_class': 'Large (10cm)',
                'radius_mm': 50
            }
        ]
        self.sim.set_discs(discs)
        self.sim.total_discs = 1
        self.sim.sorted_count = 0

        # Animate to disc
        self._animate_to_disc(discs[0])

    def demo_multiple_discs(self):
        """Demo with multiple discs of different sizes"""
        discs = [
            {'x': 100, 'y': 100, 'radius': 20, 'size_class': 'Small (5cm)', 'radius_mm': 25},
            {'x': 250, 'y': 150, 'radius': 30, 'size_class': 'Medium (7cm)', 'radius_mm': 35},
            {'x': 180, 'y': 280, 'radius': 40, 'size_class': 'Large (10cm)', 'radius_mm': 50},
            {'x': 320, 'y': 220, 'radius': 25, 'size_class': 'Small (5cm)', 'radius_mm': 25},
            {'x': 150, 'y': 380, 'radius': 35, 'size_class': 'Medium (7cm)', 'radius_mm': 35},
        ]
        self.sim.set_discs(discs)
        self.sim.total_discs = 5
        self.sim.sorted_count = 2

        # Animate to largest disc
        largest = max(discs, key=lambda d: d['radius'])
        self._animate_to_disc(largest)

    def demo_sorting(self):
        """Demo sorting sequence"""
        discs = [
            {'x': 120, 'y': 150, 'radius': 25, 'size_class': 'Small (5cm)', 'radius_mm': 25},
            {'x': 200, 'y': 200, 'radius': 35, 'size_class': 'Medium (7cm)', 'radius_mm': 35},
            {'x': 280, 'y': 150, 'radius': 40, 'size_class': 'Large (10cm)', 'radius_mm': 50},
        ]
        self.sim.set_discs(discs)
        self.sim.total_discs = 3
        self.sim.sorted_count = 0

        # Animate through all discs
        self.sorting_queue = discs.copy()
        self.current_sort_idx = 0
        self._sort_next_disc()

    def _sort_next_disc(self):
        """Sort next disc in queue"""
        if self.current_sort_idx < len(self.sorting_queue):
            disc = self.sorting_queue[self.current_sort_idx]
            self._animate_to_disc(disc, callback=self._on_sort_complete)
        else:
            self.sim.set_robot_state("Idle")
            print("✓ Sorting complete!")

    def _on_sort_complete(self):
        """Called when one disc is sorted"""
        self.current_sort_idx += 1
        self.sim.sorted_count = self.current_sort_idx

        # Wait a bit, then sort next
        QTimer.singleShot(500, self._sort_next_disc)

    def _animate_to_disc(self, disc, callback=None):
        """Animate robot to disc"""
        start = (50, 450)
        target = (disc['x'], disc['y'])

        path = self.planner.generate_path(start, target, num_points=100)
        self.sim.set_robot_path(path)
        self.sim.set_robot_state("Moving")

        self.anim_path = path
        self.anim_idx = 0
        self.anim_callback = callback
        self.anim_timer.start(16)  # 60 FPS

    def _animate(self):
        """Animation loop with easing"""
        if self.anim_idx < len(self.anim_path):
            # Ease-in-out
            progress = self.anim_idx / len(self.anim_path)
            if progress < 0.5:
                eased = 2 * progress * progress
            else:
                eased = 1 - 2 * (1 - progress) * (1 - progress)

            eased_idx = int(eased * len(self.anim_path))
            eased_idx = min(eased_idx, len(self.anim_path) - 1)

            x, y = self.anim_path[eased_idx]
            self.sim.set_robot_pos(x, y)
            self.anim_idx += 1
        else:
            self.anim_timer.stop()
            self.sim.set_robot_state("Picking")

            # Call callback if exists
            if hasattr(self, 'anim_callback') and self.anim_callback:
                callback = self.anim_callback
                self.anim_callback = None
                QTimer.singleShot(300, callback)

if __name__ == "__main__":
    print("="*60)
    print("Robot Simulation - Phase 1 Visual Enhancements Demo")
    print("="*60)
    print("\nFeatures demonstrated:")
    print("  ✓ Gradient background (dark blue theme)")
    print("  ✓ Color-coded discs (Green/Yellow/Red)")
    print("  ✓ 3D disc appearance with gradients & shadows")
    print("  ✓ Work zones (sorting bins)")
    print("  ✓ Status overlay with progress bar")
    print("  ✓ Enhanced grid with coordinates")
    print("  ✓ Glowing robot with state colors")
    print("  ✓ Smooth ease-in-out animation (60 FPS)")
    print("\nControls:")
    print("  - Click buttons to switch demos")
    print("  - Watch the robot animate smoothly!")
    print("="*60)

    app = QApplication(sys.argv)
    demo = SimulationDemo()
    demo.show()
    sys.exit(app.exec_())
