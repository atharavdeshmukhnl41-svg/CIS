class AIExplainer:

    def generate_explanation(self, result):
        issues = result.get("issues", [])

        if "No issues detected" in issues:
            return {
                "summary": "System is healthy",
                "fix": "No action required"
            }

        if any("NSG" in i for i in issues):
            return {
                "summary": "Traffic blocked by NSG",
                "fix": "Update NSG rules"
            }

        if any("VM is stopped" in i for i in issues):
            return {
                "summary": "VM is not running",
                "fix": "Start the VM"
            }

        if any("No NIC" in i for i in issues):
            return {
                "summary": "VM network misconfigured",
                "fix": "Attach NIC to VM"
            }

        return {
            "summary": "Multiple issues detected",
            "fix": "Check network configuration"
        }