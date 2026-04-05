from neo4j import GraphDatabase
from datetime import datetime, timezone
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
 

class RCAEngine:
 
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
 
    def execute(self, query, params=None):
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [r.data() for r in result]
 
    def analyze_path(self, vm, port):
        resolved_vm = self._resolve_vm(vm)
        if not resolved_vm:
            return {
                "vm": vm,
                "path": [],
                "issues": ["❌ VM not found"],
                "root_cause": "VM does not exist",
                "impact": "No impact analysis available",
                "fix": "Verify VM name",
                "confidence": 100,
                "details": {}
            }
 
        context = self._fetch_network_context(resolved_vm, port)
        vm = resolved_vm
        issues = []
        impact_components = set()
        context["metrics_issue"] = False
 
        # Load Balancer and Public IP
        if context["lb_present"]:
            issues.append(f"✔ Traffic via Load Balancer: {context['lb_name']}")
            if context["lb_missing_backend"]:
                issues.append("❌ Load Balancer backend pool missing or VM not attached")
                impact_components.update(["Load Balancer", "VM"])
            if context["lb_rule_missing"]:
                issues.append(f"❌ Load Balancer has no listener for port {port}")
                impact_components.update(["Load Balancer", "VM"])
        else:
            issues.append("⚠ No Load Balancer")
 
        if context["pip_present"]:
            issues.append(f"✔ Public IP: {context['pip_name']}")
        else:
            if context["lb_present"]:
                issues.append("⚠ No Public IP (Load Balancer path expected)")
            else:
                issues.append("❌ No Public IP attached")
                impact_components.add("VM")
 
        # NSG checks
        if context["nsg_present"]:
            if context["nsg_blocked"]:
                issues.append(f"❌ NSG blocks port {port} (priority {context['nsg_blocking_priority']})")
                impact_components.update(["VM"])
            else:
                issues.append(f"✔ NSG allows port {port}")
        else:
            issues.append("✔ No NSG (open)")
 
        # Route table checks
        if context["route_table_present"]:
            issues.append("✔ Route Table attached")
            if context["blackhole_route"]:
                issues.append("❌ Blackhole route blocking internet")
                impact_components.update(["Load Balancer", "VM"])
        else:
            issues.append("⚠ No Route Table attached")
            if context["pip_present"] or context["lb_present"]:
                impact_components.update(["VM"])
 
        # Internet reachability
        if context["nsg_blocked"]:
            issues.append("❌ Traffic blocked by NSG")
        elif context["blackhole_route"]:
            issues.append("❌ Internet blocked by route table")
        elif context["lb_present"]:
            issues.append("✔ Internet reachable via Load Balancer")
        elif context["pip_present"]:
            issues.append("✔ Internet reachable via Public IP")
        else:
            issues.append("❌ No Internet entry point")
            impact_components.update(["VM"])
 
        # Metrics and VM health
        metrics = self.get_latest_metrics(vm)
        metrics_issue = False
        cpu = 0
 
        if not metrics:
            metrics_issue = True
            issues.append("⚠ No metrics available from the VM monitoring agent")
        else:
            cpu = float(metrics.get("cpu") or 0)
            ts = metrics.get("ts")
            metrics_age = None
            try:
                if ts:
                    if hasattr(ts, "to_native"):
                        ts = ts.to_native()
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    metrics_age = int((datetime.now(timezone.utc) - ts).total_seconds())
                    if metrics_age > 120:
                        metrics_issue = True
                        issues.append(f"⚠ Metrics stale ({metrics_age}s since last report)")
                else:
                    metrics_issue = True
                    issues.append("⚠ Metric timestamp missing from the latest record")
            except Exception:
                metrics_issue = True
                issues.append("⚠ Unable to validate metric timestamp")
 
            if not metrics_issue:
                if cpu > 80:
                    issues.append("🔥 High CPU usage")
                    impact_components.add("VM")
                else:
                    issues.append("✔ CPU normal")
 
        if metrics_issue:
            context["metrics_issue"] = True
            if not metrics:
                issues.append("⚠ VM state unknown because no metric data is available")
            else:
                issues.append("⚠ VM state may be unreliable due to metric reporting issues")
        else:
            if context["vm_state"] != "running":
                issues.append(f"❌ VM power state is {context['vm_state']}")
                impact_components.add("VM")
            else:
                issues.append("✔ VM running")
 
        path = self._build_path_flow(context)
 
        # Root cause derivation
        root_cause, fix, confidence = self._derive_root_cause(context, metrics_issue, issues, port)
        impact = self._format_impact(impact_components)
 
        return {
            "vm": vm,
            "path": path,
            "issues": issues,
            "root_cause": root_cause,
            "impact": impact,
            "fix": fix,
            "confidence": confidence,
            "details": {
                "failure_point": context["failure_point"],
                "lb_name": context["lb_name"],
                "pip_name": context["pip_name"],
                "nsg_name": context["nsg_name"]
            }
        }
 
    def _fetch_network_context(self, vm, port):
        context = {
            "pip_present": False,
            "pip_name": None,
            "lb_present": False,
            "lb_name": None,
            "lb_missing_backend": False,
            "lb_rule_missing": False,
            "nsg_present": False,
            "nsg_name": None,
            "nsg_blocked": False,
            "nsg_blocking_priority": None,
            "route_table_present": False,
            "blackhole_route": False,
            "vm_state": "running",
            "failure_point": "Unknown"
        }
 
        # Public IP / Load Balancer / NIC / NSG / Routes
        query = """
        MATCH (vm:VM {name:$vm})-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (nic)-[:HAS_PUBLIC_IP]->(pip)
        OPTIONAL MATCH (lb:LoadBalancer)-[:BALANCES]->(nic)
        OPTIONAL MATCH (nic)-[:SECURED_BY]->(nsg)
        OPTIONAL MATCH (nsg)-[:HAS_RULE]->(rule)
        OPTIONAL MATCH (nic)-[:IN_SUBNET]->(subnet)-[:USES_ROUTE_TABLE]->(rt)
        OPTIONAL MATCH (rt)-[:HAS_ROUTE]->(route)
        RETURN pip.name AS pip_name,
               lb.name AS lb_name,
               nsg.name AS nsg_name,
               nsg.resource_group AS nsg_rg,
               collect(distinct rule) AS nsg_rules,
               rt.name AS rt_name,
               collect(distinct route) AS routes,
               vm.power_state AS vm_state
        """
 
        rows = self.execute(query, {"vm": vm})
        if not rows:
            return context
 
        row = rows[0]
        context["pip_present"] = bool(row.get("pip_name"))
        context["pip_name"] = row.get("pip_name")
        context["lb_present"] = bool(row.get("lb_name"))
        context["lb_name"] = row.get("lb_name")
        context["nsg_present"] = bool(row.get("nsg_name"))
        context["nsg_name"] = row.get("nsg_name")
        context["route_table_present"] = bool(row.get("rt_name"))
        vm_state = row.get("vm_state") or row.get("state") or "unknown"
        vm_state = str(vm_state).lower()
        if "powerstate/" in vm_state:
            vm_state = vm_state.split("/")[-1]
        context["vm_state"] = vm_state
 
        # NSG rule evaluation
        if row.get("nsg_rules"):
            rules = [r for r in row["nsg_rules"] if r]
            rules = sorted(rules, key=lambda r: int(r.get("priority", 9999)))
            for rule in rules:
                port_value = str(rule.get("port", ""))
                if port_value == str(port) or port_value == "*":
                    if rule.get("access", "").lower() == "deny":
                        context["nsg_blocked"] = True
                        context["nsg_blocking_priority"] = rule.get("priority")
                        context["failure_point"] = "NSG"
                    break
 
        # Route evaluation
        routes = [r for r in (row.get("routes") or []) if r]
        for route in routes:
            prefix = route.get("address_prefix") or route.get("prefix")
            hop = route.get("next_hop") or route.get("hop")
            if str(prefix) == "0.0.0.0/0" and hop in ["None", "Blackhole", None, "null"]:
                context["blackhole_route"] = True
                context["failure_point"] = "RouteTable"
 
        # Load Balancer backend and rule checks
        if context["lb_present"]:
            lb_query = """
            MATCH (lb:LoadBalancer {name:$lb_name})
            OPTIONAL MATCH (lb)-[:HAS_BACKEND|BALANCES]->(nic)<-[:HAS_NIC]-(vm:VM {name:$vm})
            OPTIONAL MATCH (lb)-[:HAS_RULE]->(rule)
            RETURN COUNT(DISTINCT nic) AS backend_count,
                   collect(distinct rule) AS lb_rules
            """
            lb_rows = self.execute(lb_query, {"lb_name": context["lb_name"], "vm": vm})
            if lb_rows:
                lb_row = lb_rows[0]
                backend_count = int(lb_row.get("backend_count") or 0)
                lb_rules = [r for r in (lb_row.get("lb_rules") or []) if r]
                if backend_count == 0:
                    context["lb_missing_backend"] = True
                    context["failure_point"] = "LoadBalancer"
                if lb_rules:
                    if not any(str(rule.get("frontend_port", "")) == str(port) or str(rule.get("backend_port", "")) == str(port) for rule in lb_rules):
                        context["lb_rule_missing"] = True
                        context["failure_point"] = "LoadBalancer"
                else:
                    context["lb_rule_missing"] = True
                    context["failure_point"] = "LoadBalancer"
 
        return context
 
    def _resolve_vm(self, vm):
        query = """
        MATCH (v:VM)
        WHERE toLower(coalesce(v.name, '')) = toLower($vm)
           OR toLower(coalesce(v.label, '')) = toLower($vm)
           OR toLower(toString(coalesce(v.id, ''))) = toLower($vm)
        RETURN coalesce(v.name, v.label) AS vm_name
        LIMIT 1
        """
        rows = self.execute(query, {"vm": vm})
        if rows:
            return rows[0].get("vm_name")
        return None
 
    def _build_path_flow(self, context):
        path = []
        if context["pip_present"]:
            path.append({"name": "PublicIP", "status": "success", "details": context["pip_name"]})
        if context["lb_present"]:
            lb_status = "error" if (context["lb_missing_backend"] or context["lb_rule_missing"]) else "success"
            path.append({"name": "LoadBalancer", "status": lb_status, "details": context["lb_name"]})
        path.append({"name": "NIC", "status": "success"})
        vm_status = "error" if context["vm_state"] != "running" else "success"
        path.append({"name": "VM", "status": vm_status, "details": context["vm_state"]})
        nsg_status = "error" if context["nsg_blocked"] else ("warning" if not context["nsg_present"] else "success")
        path.append({"name": "NSG", "status": nsg_status, "details": context["nsg_name"]})
        route_status = "error" if context["blackhole_route"] else ("warning" if not context["route_table_present"] else "success")
        path.append({"name": "RouteTable", "status": route_status})
        const_metrics_status = "error" if context.get("metrics_issue") or context["vm_state"] != "running" else "success"
        path.append({"name": "Metrics", "status": const_metrics_status})
        return path
 
    def _derive_root_cause(self, context, metrics_issue, issues, port):
        if context["nsg_blocked"] and context["blackhole_route"]:
            return (
                "Traffic blocked due to NSG and invalid routing",
                "Allow required port in NSG and correct the route table next hop",
                95
            )
 
        if context["lb_present"] and context["lb_missing_backend"] and context["lb_rule_missing"]:
            return (
                "Load Balancer backend pool and listener rule misconfiguration",
                "Attach VM NIC to the LB backend pool and configure the LB listener for port {port}".format(port=port),
                92
            )
 
        if context["blackhole_route"]:
            return (
                "Route table misconfiguration",
                "Fix the route table default route so traffic is forwarded correctly",
                94
            )
 
        if context["lb_present"] and context["lb_missing_backend"]:
            return (
                "Load Balancer backend pool misconfiguration",
                "Add the VM NIC to the Load Balancer backend pool",
                90
            )
 
        if context["lb_present"] and context["lb_rule_missing"]:
            return (
                "Load Balancer listener missing for port {port}".format(port=port),
                "Create or update the Load Balancer rule for port {port}".format(port=port),
                90
            )
 
        if context["nsg_blocked"]:
            return (
                "Traffic blocked by NSG",
                "Allow the required port in NSG rules",
                90
            )
 
        if not context["pip_present"] and not context["lb_present"]:
            return (
                "No external ingress path",
                "Attach a Public IP or configure a Load Balancer for inbound traffic",
                88
            )
 
        if metrics_issue and context["vm_state"] == "running":
            return (
                "Monitoring telemetry is stale or unavailable",
                "Check the VM monitoring agent and metric ingest pipeline. Ensure the agent is reporting fresh CPU/network metrics and that they are ingested into Neo4j.",
                85
            )
 
        if context["vm_state"] != "running":
            return (
                "VM is not in a running power state",
                "Confirm the Azure VM is started, healthy, and its power state is correctly reflected in topology metadata",
                87
            )
 
        if metrics_issue:
            return (
                "Monitoring agent or VM telemetry issue",
                "Ensure the VM monitoring agent is connected and metric ingest is functioning",
                85
            )
 
        return (
            "System healthy",
            "No action needed",
            100
        )
 
    def _format_impact(self, components):
        if not components:
            return "No broad impact detected"
        ordered = [c for c in ["Load Balancer", "VM", "NIC", "NSG", "RouteTable", "Public IP"] if c in components]
        return " + ".join(ordered)
 
    def get_latest_metrics(self, vm):
 
        result = self.execute("""
        MATCH (m:Metrics)
        WHERE toLower(m.vm) = toLower($vm)
        RETURN m.cpu AS cpu,
               m.network_in AS network_in,
               m.network_out AS network_out,
               m.timestamp AS ts
        ORDER BY ts DESC LIMIT 1
        """, {"vm": vm})
 
        return result[0] if result else None
 
    def close(self):
        self.driver.close()
        self.driver.close()