class PriorityEngine:
 
    def calculate_priority(self, root_cause, affected_vms, confidence):
 
        vm_count = len(affected_vms)
 
        # ----------------------------
        # CRITICAL CONDITIONS
        # ----------------------------
        if "DOWN" in root_cause and vm_count >= 1:
            return "CRITICAL"
 
        if "blocked" in root_cause.lower() and vm_count >= 2:
            return "CRITICAL"
 
        # ----------------------------
        # HIGH
        # ----------------------------
        if "High CPU" in root_cause:
            return "HIGH"
 
        if vm_count >= 3:
            return "HIGH"
 
        # ----------------------------
        # MEDIUM
        # ----------------------------
        if "blocked" in root_cause.lower():
            return "MEDIUM"
 
        # ----------------------------
        # LOW
        # ----------------------------
        return "LOW"