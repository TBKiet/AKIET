class SpatialReasoner:
    """
    Analyzes list of detected discs to find spatial relationships, e.g., stacking.
    """

    @staticmethod
    def detect_stacks(discs, threshold_px=20):
        """
        Groups discs that share a similar center point (indicating a stack).
        :param discs: List of Disc objects.
        :param threshold_px: Max distance in pixels to consider centers 'same'.
        """
        stacks = []
        processed_indices = set()

        for i, d1 in enumerate(discs):
            if i in processed_indices:
                continue

            stack_group = [d1]
            processed_indices.add(i)

            for j, d2 in enumerate(discs):
                if i == j or j in processed_indices:
                    continue

                # Calculate distance between centers
                dist = ((d1.x - d2.x)**2 + (d1.y - d2.y)**2)**0.5

                if dist < threshold_px:
                    stack_group.append(d2)
                    processed_indices.add(j)

            # If we found related items (or just want to track everything as stacks of 1)
            stacks.append(stack_group)

        return stacks
