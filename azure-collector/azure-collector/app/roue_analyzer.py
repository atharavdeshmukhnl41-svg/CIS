class RouteAnalyzer:

    def analyze(self, routes, port):
        """
        Detect routing issues
        """

        if not routes:
            return {
                "status": "NO_ROUTE",
                "issue": "No route table associated"
            }

        for route in routes:
            next_hop = route.get("next_hop")

            # Blackhole
            if next_hop in ["None", "Blackhole"]:
                return {
                    "status": "FAIL",
                    "issue": "Blackhole route detected"
                }

            # Internet route missing
            if route.get("prefix") == "0.0.0.0/0":
                if next_hop not in ["Internet", "VirtualAppliance"]:
                    return {
                        "status": "FAIL",
                        "issue": "Default route misconfigured"
                    }

        return {
            "status": "OK",
            "issue": None
        }