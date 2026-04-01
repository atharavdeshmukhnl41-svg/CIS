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
    # MAIN RCA FUNCTION (FIXED)
    # -----------------------------------------
    def analyze_path(self, vm, port):
 
        path = ["VM"]
        issues = []
 
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
        # 2. NSG CHECK
        # -----------------------------
        nsg_query = """
        MATCH (vm:VM {name: $vm})-[:HAS_NIC]->(nic)-[:SECURED_BY]->(nsg)
        OPTIONAL MATCH (nsg)-[:HAS_RULE]->(rule)
        RETURN rule.port AS port, rule.access AS access, rule.priority AS priority
        ORDER BY rule.priority ASC
        """
        
        results = self.execute(nsg_query, {"vm": vm})
        
        path.append("NIC")
        path.append("NSG")
        
        final_decision = None
        
        for r in results:
            rule_port = str(r.get("port") or "")
            rule_access = str(r.get("access") or "").lower()
        
            # ✅ FIRST MATCH ONLY (like Azure)
            if rule_port == str(port):
                final_decision = rule_access
                break
        
        # ✅ APPLY RESULT
        if final_decision == "allow":
            issues.append(f"✔ NSG allows port {port}")
        
        elif final_decision == "deny":
            issues.append(f"❌ NSG blocking port {port}")
        
        else:
            issues.append(f"✔ No NSG rule affecting port {port}")
 
        # -----------------------------
        # 3. METRICS CHECK (FIXED)
        # -----------------------------
        path.append("Metrics")
 
        metrics = self.get_latest_metrics(vm)
 
        is_vm_down = False
        cpu = 0
        net_in = 0
        net_out = 0
 
        if not metrics:
            is_vm_down = True
            issues.append("❌ No metrics available")
        else:
            cpu = float(metrics.get("cpu") or 0)
            net_in = float(metrics.get("network_in") or 0)
            net_out = float(metrics.get("network_out") or 0)
            ts = metrics.get("ts")
 
            try:
                if ts:
                    if hasattr(ts, "to_native"):
                        ts = ts.to_native()
 
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
 
                    now = datetime.now(timezone.utc)
                    diff = (now - ts).total_seconds()
 
                    # ✅ FIX: VM DOWN detection
                    if diff > 30:
                        is_vm_down = True
 
            except Exception:
                is_vm_down = True
 
        # -----------------------------
        # 4. ISSUE GENERATION (CLEAN)
        # -----------------------------
        if is_vm_down:
            issues.append("❌ VM not sending data (DOWN)")
            cpu = 0
            net_in = 0
            net_out = 0
        else:
            issues.append("✔ VM is running")
 
            # CPU check
            if cpu > 80:
                issues.append("🔥 High CPU usage")
            else:
                issues.append("✔ CPU normal")
 
            # Network check
            if net_in == 0 and net_out == 0:
                issues.append("⚠ No network activity")
            else:
                issues.append("✔ Network activity normal")
 
        # -----------------------------
        # 5. ROOT CAUSE ENGINE (PRIORITY FIX)
        # -----------------------------
        root_causes = []
        fixes = []
        confidence = 50
 
        for issue in issues:
 
            if "DOWN" in issue:
                root_causes = ["VM is DOWN"]
                fixes = ["Start VM or restart monitoring agent"]
                confidence = 95
                break
 
            elif "High CPU" in issue:
                root_causes.append("High CPU load on VM")
                fixes.append("Scale VM or reduce workload")
                confidence = 90
 
            elif "blocking" in issue:
                root_causes.append("Traffic blocked by NSG")
                fixes.append("Allow required port in NSG")
                confidence = 90
 
        if not root_causes:
            root_causes = ["System healthy"]
            fixes = ["No action needed"]
            confidence = 100
 
        return {
            "vm": vm,
            "path": path,
            "issues": issues,
            "root_cause": " | ".join(root_causes),
            "fix": " | ".join(fixes),
            "confidence": confidence
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