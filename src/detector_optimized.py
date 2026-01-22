import cv2
import numpy as np

class CircleDetector:
    """
    Optimized circle detector with strict parameters to reduce false positives
    """
    def __init__(self, use_gpu=False):
        self.use_gpu = use_gpu
        # Performance tracking
        self.last_detection_time = 0

    def detect(self, image):
        """
        Detects circles in the given image with optimized parameters.
        :param image: BGR image (numpy array).
        :return: List of tuples (x, y, radius). Returns empty list if no circles found.
        """
        if image is None or image.size == 0:
            return []

        # Convert to Grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter (better edge preservation than Gaussian)
        gray_filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # Apply Hough Circle Transform with STRICTER parameters
        # Higher param1 = stricter edge detection (reduce false positives)
        # Higher param2 = stricter circle detection (reduce false positives)
        circles = cv2.HoughCircles(
            gray_filtered,
            cv2.HOUGH_GRADIENT,
            dp=1.2,              # Inverse ratio of accumulator resolution
            minDist=60,          # Minimum distance between circle centers (increased)
            param1=100,          # Canny edge detector high threshold (increased from 50)
            param2=50,           # Accumulator threshold (increased from 30)
            minRadius=15,        # Minimum circle radius (increased from 10)
            maxRadius=150        # Maximum circle radius (increased from 100)
        )

        detected_circles = []
        if circles is not None:
            circles = np.uint16(np.around(circles))

            # Additional filtering: check circularity
            for circle in circles[0, :]:
                x, y, radius = int(circle[0]), int(circle[1]), int(circle[2])

                # Skip circles too close to edge
                h, w = image.shape[:2]
                if x - radius < 5 or x + radius > w - 5 or \
                   y - radius < 5 or y + radius > h - 5:
                    continue

                # Verify circle by checking edge pixels
                if self._verify_circle(gray_filtered, x, y, radius):
                    detected_circles.append((x, y, radius))

        return detected_circles

    def _verify_circle(self, gray, x, y, radius):
        """
        Verify if detected circle is actually circular by sampling edge pixels
        """
        # Sample points around the circle perimeter
        num_samples = 12
        edge_threshold = 30
        valid_edges = 0

        for i in range(num_samples):
            angle = 2 * np.pi * i / num_samples
            px = int(x + radius * np.cos(angle))
            py = int(y + radius * np.sin(angle))

            # Check if point is within image bounds
            if 0 <= px < gray.shape[1] and 0 <= py < gray.shape[0]:
                # Check edge strength at this point
                if gray[py, px] > edge_threshold:
                    valid_edges += 1

        # Require at least 60% of sampled points to be edges
        return valid_edges >= (num_samples * 0.6)
