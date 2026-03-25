class AIExplainer:
 
    def generate_explanation(self, result):
 
        issues = result.get("issues", [])
 
        # Normalize issues
        issues = [i.replace("❌ ", "") for i in issues]
 
        if not issues or issues == ["No issues detected"]:
            return {
                "summary": "System is healthy",
                "fix": "No action required"
            }
 
        summary_parts = []
        fix_parts = []
 
        for issue in issues:
 
            # NSG
            if "NSG" in issue or "Blocked by NSG" in issue:
                summary_parts.append("Traffic blocked by NSG")
                fix_parts.append("Allow required port in NSG rules")
 
            # Load Balancer
            elif "Load Balancer" in issue:
                summary_parts.append("Load Balancer misconfiguration")
                fix_parts.append("Add or correct LB rule and backend pool")
 
            # Route
            elif "Blackhole" in issue:
                summary_parts.append("Invalid route configuration")
                fix_parts.append("Fix route table next hop settings")
 
            # Outbound
            elif "No outbound internet" in issue:
                summary_parts.append("No outbound connectivity")
                fix_parts.append("Attach NAT Gateway or Public IP")
 
            else:
                summary_parts.append(issue)
                fix_parts.append("Investigate configuration")
 
        return {
            "summary": " | ".join(set(summary_parts)),
            "fix": " | ".join(set(fix_parts))
        }