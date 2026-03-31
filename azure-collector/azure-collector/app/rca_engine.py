from neo4j import GraphDatabase
from datetime import datetime, timezone
 
 
class RCAEngine:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
 
    # -----------------------------------------
    # HELPER EXECUTE
    # -----------------------------------------
    def execute(self, query, params=None):
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]
 
    # -----------------------------------------
    # MAIN RCA FUNCTION (UPGRADED)
    # -----------------------------------------
    def analyze_path(self, vm, port):
 
        path = ["VM"]
        issues = []
        root_cause = []
        fixes = []
        confidence = 0
 
        # -----------------------------
        # 1. CHECK VM EXISTS
        # -----------------------------
        vm_check = self.execute(
            "MATCH (v:VM {name:$vm}) RETURN v",
            {"vm": vm}
        )
 
        if not vm_check:
            return {
                "vm": vm,
                "path": [],
                "issues": ["❌ VM not found"],
                "root_cause": "VM does not exist",
                "fix": "Verify VM name",
                "confidence": 100
            }
 
        # -----------------------------
        # 2. NSG CHECK (CORE DIFFERENTIATOR)
        # -----------------------------
        nsg_query = """
        MATCH (vm:VM {name: $vm})-[:HAS_NIC]->(nic)-[:SECURED_BY]->(nsg)
        OPTIONAL MATCH (nsg)-[:HAS_RULE]->(rule)
        RETURN nsg.name AS nsg, rule.port AS port, rule.access AS access
        """
 
        results = self.execute(nsg_query, {"vm": vm})
 
        path.append("NIC")
        path.append("NSG")
 
        port_allowed = False
 
        if not results:
            issues.append("✔ No NSG attached (open access)")
            port_allowed = True
        else:
            for r in results:
                rule_port = str(r.get("port")) if r.get("port") else ""
                rule_access = str(r.get("access")).lower() if r.get("access") else ""
 
                if rule_port == str(port) and rule_access == "allow":
                    port_allowed = True
                    break
 
            if port_allowed:
                issues.append(f"✔ NSG allows port {port}")
            else:
                issues.append(f"❌ NSG blocking port {port}")
                root_cause.append(f"NSG blocking port {port}")
                fixes.append(f"Allow inbound rule for port {port}")
                confidence += 50
 
        # -----------------------------
        # 3. METRICS CHECK (VM HEALTH)
        # -----------------------------
        path.append("Metrics")
 
        metrics = self.get_latest_metrics(vm)
 
        if not metrics:
            issues.append("❌ No metrics available")
            root_cause.append("Agent not sending metrics")
            fixes.append("Check CIP agent service")
            confidence += 30
        else:
            cpu = metrics.get("cpu") or 0
            net_in = metrics.get("network_in") or 0
            net_out = metrics.get("network_out") or 0
            timestamp = metrics.get("ts")
 
            # 🔥 Timestamp check (VM DOWN detection)
            if timestamp:
                if hasattr(timestamp, "to_native"):
                    timestamp = timestamp.to_native()
 
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
 
                now = datetime.now(timezone.utc)
                diff = (now - timestamp).total_seconds()
 
                if diff > 20:
                    issues.append("❌ VM not sending data (DOWN)")
                    root_cause.append("VM is DOWN")
                    fixes.append("Start VM or restart agent")
                    confidence += 70
 
            # CPU analysis
            if cpu > 80:
                issues.append("🔥 High CPU usage")
                root_cause.append("High CPU load on VM")
                fixes.append("Scale VM or reduce workload")
                confidence += 20
 
            # Network analysis
            if net_in == 0 and net_out == 0:
                issues.append("⚠ No network activity")
                root_cause.append("No incoming/outgoing traffic")
                fixes.append("Check application traffic or connectivity")
                confidence += 10
 
        # -----------------------------
        # FINAL RESULT
        # -----------------------------
        if not root_cause:
            root_cause = ["No issue detected"]
            fixes = ["System healthy"]
            confidence = 50
 
        return {
            "vm": vm,
            "path": path,
            "issues": issues,
            "root_cause": " | ".join(set(root_cause)),
            "fix": " | ".join(set(fixes)),
            "confidence": min(confidence, 100)
        }
 
    # -----------------------------------------
    # METRICS FETCH
    # -----------------------------------------
    def get_latest_metrics(self, vm):
 
        query = """
        MATCH (m:Metrics {vm: $vm})
        RETURN
            m.cpu AS cpu,
            m.network_in AS network_in,
            m.network_out AS network_out,
            m.timestamp AS ts
        ORDER BY ts DESC
        LIMIT 1
        """
 
        result = self.execute(query, {"vm": vm})
 
        if not result:
            return None
 
        return result[0]
 
    # -----------------------------------------
    # CLOSE
    # -----------------------------------------
    def close(self):
        self.driver.close()