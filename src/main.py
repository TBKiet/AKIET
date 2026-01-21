import sys
import os

# CRITICAL: Handle Qt plugin conflicts BEFORE importing anything
# Remove OpenCV's Qt plugin path if it exists
if "QT_QPA_PLATFORM_PLUGIN_PATH" in os.environ:
    del os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"]

# Set Qt platform BEFORE importing PyQt or OpenCV
if "DISPLAY" in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "xcb"
else:
    print("WARNING: 'DISPLAY' environment variable not set. Using 'offscreen' platform.")
    print("       UI will NOT be visible. Use 'ssh -X' or 'ssh -Y' to enable X11 forwarding.")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Add project root to sys.path to ensure 'src' module can be found
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import PyQt5 FIRST, before OpenCV
from PyQt5.QtWidgets import QApplication

# Now import OpenCV (it won't override Qt settings)
import cv2

from src.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)

    # Optional: Set global styles later

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
