class CalibrationManager:
    """
    Handles camera calibration and pixel-to-metric conversion.
    Currently implements a simple scale factor based approach.
    """
    def __init__(self, scale_factor=1.0):
        """
        :param scale_factor: Ratio of mm per pixel.
                             Example: if an object of 50mm takes 100 pixels, scale = 0.5
        """
        self.scale_factor = scale_factor # mm/pixel

    def set_scale_from_reference(self, reference_pixels, real_size_mm):
        """
        Calibrates the scale factor using a known reference object.
        :param reference_pixels: Diameter of the reference object in pixels.
        :param real_size_mm: Real diameter of the reference object in mm.
        """
        if reference_pixels > 0:
            self.scale_factor = real_size_mm / reference_pixels
            print(f"Calibration updated: Scale = {self.scale_factor:.4f} mm/px")

    def pixel_to_mm(self, pixels):
        """
        Converts pixel measurement to millimeters.
        """
        return pixels * self.scale_factor

    def mm_to_pixel(self, mm):
        """
        Converts millimeters to pixels (useful for drawing overlays).
        """
        return int(mm / self.scale_factor) if self.scale_factor > 0 else 0
