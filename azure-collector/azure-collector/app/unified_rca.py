from app.rca_engine import RCAEngine


class UnifiedRCA:

    def __init__(self):
        self.engine = RCAEngine()

    def analyze(self, vm_name, port):
        result = {
            "vm": vm_name,
            "issues": []
        }

        # 1. Metrics Check
        health = self.engine.analyze_vm_health(vm_name)

        if "error" in health:
            result["issues"].append(health["error"])
        else:
            if health["cpu"] is None:
                result["issues"].append("VM is STOPPED or no metrics available")
            elif health["status"] == "High CPU":
                result["issues"].append("High CPU usage")

        # 2. NSG Check
        nsg = self.engine.check_port_reachability(vm_name, port)

        if nsg["status"] == "Deny":
            result["issues"].append(f"Port {port} BLOCKED by NSG")

        # 3. Path Check
        path_issue = self.engine.detect_break_point(vm_name, port)

        if path_issue["break_point"]:
            result["issues"].append(
                f"Break at {path_issue['break_point']}: {path_issue['details']}"
            )

        return result

    def close(self):
        self.engine.close()