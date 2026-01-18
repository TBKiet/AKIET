from dataclasses import dataclass

@dataclass
class Disc:
    x: int
    y: int
    radius_px: int
    radius_mm: float = 0.0
    size_label: str = "Unknown"

class Classifier:
    """
    Classifies discs based on their measured radius in millimeters.
    """

    # Target Radius constants (in mm)
    # 5cm diameter -> 25mm radius
    # 7cm diameter -> 35mm radius
    # 10cm diameter -> 50mm radius

    # Boundaries (midpoints)
    LIMIT_S_M = 30.0   # Midpoint between 25 and 35
    LIMIT_M_L = 42.5   # Midpoint between 35 and 50

    @staticmethod
    def classify(radius_mm):
        """
        Classify based on target sizes: 5cm (S), 7cm (M), 10cm (L).
        Input is radius in millimeters.
        """
        if radius_mm < Classifier.LIMIT_S_M:
            return "Small (5cm)"
        elif radius_mm < Classifier.LIMIT_M_L:
            return "Medium (7cm)"
        else:
            return "Large (10cm)"
