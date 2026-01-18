import numpy as np

class PathPlanner:
    """
    Simulates a robot arm path using Quadratic Bezier curves.
    """
    def __init__(self):
        self.path = []

    def generate_path(self, start_pos, target_pos, num_points=50):
        """
        Generates a curved path from start to target.
        :param start_pos: (x, y) tuple
        :param target_pos: (x, y) tuple
        :param num_points: Number of points in the generated path
        :return: List of (x, y) points
        """
        start_x, start_y = start_pos
        end_x, end_y = target_pos

        # Determine a control point to create a curve
        # Simple heuristic: Midpoint with some offset
        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2

        # Offset to create 'arc' effect
        # We offset perpendicular to the line connecting start and end
        dx = end_x - start_x
        dy = end_y - start_y

        # Perpendicular vector (-dy, dx)
        control_x = mid_x - dy * 0.3
        control_y = mid_y + dx * 0.3

        t = np.linspace(0, 1, num_points)

        # Quadratic Bezier Formula: B(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
        # P0 = start, P1 = control, P2 = end

        path = []
        for time in t:
            x = (1 - time)**2 * start_x + 2 * (1 - time) * time * control_x + time**2 * end_x
            y = (1 - time)**2 * start_y + 2 * (1 - time) * time * control_y + time**2 * end_y
            path.append((int(x), int(y)))

        return path
