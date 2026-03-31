class MetricsAnalyzer:
 
    def analyze(self, metrics):
 
        if not metrics:
            return ["❌ No metrics found"]
 
        # 🔥 CRITICAL
        if metrics.get("status") == "vm_down":
            return ["❌ VM is DOWN"]
 
        cpu = metrics.get("cpu", 0)
        net_in = metrics.get("network_in", 0)
        net_out = metrics.get("network_out", 0)
 
        issues = []
 
        if cpu > 80:
            issues.append("🔥 High CPU usage")
 
        if net_in == 0 and net_out == 0:
            issues.append("⚠ No network activity")
 
        if cpu < 5 and net_in == 0 and net_out == 0:
            issues.append("💤 VM idle")
 
        if not issues:
            issues.append("✔ System healthy")
 
        return issues