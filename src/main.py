import sys
import os
import cv2  # Import OpenCV first to trigger any environment variable changes it might make

# Add project root to sys.path to ensure 'src' module can be found
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# FIX: Conflict between OpenCV's Qt and PyQt5's Qt on Linux
# This tries to remove the OpenCV-bundled Qt from the plugin path if it exists
if "QT_QPA_PLATFORM_PLUGIN_PATH" in os.environ:
    os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH")

# Force X11/xcb if DISPLAY is set, otherwise use offscreen to prevent crash
if "DISPLAY" in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "xcb"
else:
    print("WARNING: 'DISPLAY' environment variable not set. Using 'offscreen' platform.")
    print("       UI will NOT be visible. Use 'ssh -X' or 'ssh -Y' to enable X11 forwarding.")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)

    # Optional: Set global styles later

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
