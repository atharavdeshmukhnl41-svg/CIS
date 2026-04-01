class RemediationEngine:
 
    def get_steps(self, root_cause):
 
        steps = []
 
        root = root_cause.lower()
 
        # ---------------------------
        # VM DOWN
        # ---------------------------
        if "vm is down" in root:
            steps = [
                "1. Check if VM is stopped in Azure Portal",
                "2. Start the VM",
                "3. Verify CIP agent is running",
                "4. Check network connectivity",
                "5. Confirm metrics are flowing"
            ]
 
        # ---------------------------
        # NSG BLOCK
        # ---------------------------
        elif "blocked" in root:
            steps = [
                "1. Go to Azure NSG settings",
                "2. Check inbound security rules",
                "3. Add rule to allow required port",
                "4. Set correct priority (lower = higher priority)",
                "5. Save and test connectivity"
            ]
 
        # ---------------------------
        # HIGH CPU
        # ---------------------------
        elif "high cpu" in root:
            steps = [
                "1. Check running processes (top/htop)",
                "2. Identify high CPU consuming app",
                "3. Restart or optimize application",
                "4. Scale VM if needed",
                "5. Monitor CPU trend"
            ]
 
        # ---------------------------
        # NO METRICS
        # ---------------------------
        elif "metrics" in root:
            steps = [
                "1. Check CIP agent service status",
                "2. Restart agent",
                "3. Verify ngrok/API connectivity",
                "4. Check logs for errors",
                "5. Ensure metrics API reachable"
            ]
 
        # ---------------------------
        # DEFAULT
        # ---------------------------
        else:
            steps = [
                "1. Validate infrastructure configuration",
                "2. Check logs",
                "3. Verify connectivity",
                "4. Re-run RCA"
            ]
 
        return steps