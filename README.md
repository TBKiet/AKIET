# Computer Vision System for Object Sorting & Robot Simulation

**Academic Innovation Project**

## Overview

This project demonstrates a complete "Perception – Measurement – Planning – Visualization" pipeline using a single camera. It runs on Python and provides a simulation of a robot arm sorting objects based on size.

## Features

- **Object Detection**: Detects circular objects (discs) using OpenCV.
- **Metric Measurement**: Calibrates camera to measure real-world diameter (mm).
- **Classification**: Sorts objects into Small, Medium, Large.
- **Robot Simulation**: Simulates robot path planning (Bezier curves) to picked objects.
- **Interactive UI**: Real-time camera feed + Top-down 2D simulation view.

## Tech Stack

- **Language**: Python 3.8+
- **Vision**: OpenCV (Hough Transform)
- **UI**: PyQt6
- **Planning**: Bezier Curves (NumPy/SciPy)

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python src/main.py
   ```

## Structure

- `src/camera.py`: Camera handling
- `src/detector.py`: Image processing
- `src/calibration.py`: Pixel-to-mm conversion
- `src/planner.py`: Path planning algorithms
- `src/ui/`: PyQt6 interface
