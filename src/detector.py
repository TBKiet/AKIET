import cv2
import numpy as np

class CircleDetector:
    """
    Detects circular objects using OpenCV Hough Circle Transform.
    """
    def __init__(self, use_gpu=False):
        # NOTE: Full GPU support (cv2.cuda) requires custom OpenCV build.
        # We stick to CPU for standard compatibility.
        self.use_gpu = use_gpu

    def detect(self, image):
        """
        Detects circles in the given image.
        :param image: BGR image (numpy array).
        :return: List of tuples (x, y, radius). Returns empty list if no circles found.
        """
        if image is None:
            return []

        # Convert to Grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian Blur to reduce noise
        gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        # Apply Hough Circle Transform
        # param1: Higher threshold of the two passed to the Canny edge detector
        # param2: Accumulator threshold for the circle centers at the detection stage
        circles = cv2.HoughCircles(
            gray_blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=10,
            maxRadius=100
        )

        detected_circles = []
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                # i = [x, y, radius]
                detected_circles.append((int(i[0]), int(i[1]), int(i[2])))

        return detected_circles
