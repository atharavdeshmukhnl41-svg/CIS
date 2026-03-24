from neo4j import GraphDatabase
from app.config import *


class RCAEngine:
    def __init__(self):
        # ✅ MUST EXIST
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        if self.driver:
            self.driver.close()

    # -----------------------------------
    # GET NSG RULES
    # -----------------------------------
    def get_nsg_rules(self, vm_name):
        query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (nic)-[:SECURED_BY]->(nsg)
        OPTIONAL MATCH (nsg)-[:HAS_RULE]->(rule)
        RETURN rule
        """

        rules = []

        with self.driver.session() as session:
            result = session.run(query, vm_name=vm_name)

            for r in result:
                rule = r["rule"]
                if rule:
                    rules.append({
                        "name": rule.get("name"),
                        "port": str(rule.get("port")),
                        "access": rule.get("access"),
                        "priority": int(rule.get("priority") or 9999)
                    })

        return rules

    # -----------------------------------
    # GET ROUTES
    # -----------------------------------
    def get_routes(self, vm_name):
        query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (nic)-[:IN_SUBNET]->(subnet)
        OPTIONAL MATCH (rt:RouteTable)-[:ASSOCIATED_WITH]->(subnet)
        OPTIONAL MATCH (rt)-[:HAS_ROUTE]->(route)
        RETURN route
        """

        routes = []

        with self.driver.session() as session:
            result = session.run(query, vm_name=vm_name)

            for r in result:
                route = r["route"]
                if route:
                    routes.append({
                        "prefix": route.get("prefix"),
                        "next_hop": route.get("next_hop")
                    })

        return routes

    # -----------------------------------
    # VM HEALTH
    # -----------------------------------
    def analyze_vm_health(self, vm_name):
        query = """
        MATCH (vm:VM {name:$vm_name})
        RETURN vm.power_state AS state
        """

        with self.driver.session() as session:
            result = session.run(query, vm_name=vm_name)
            record = result.single()

            if not record:
                return {"status": "UNKNOWN"}

            state = record.get("state")

            if not state or state.lower() != "running":
                return {"status": "STOPPED"}

        return {"status": "RUNNING"}

    # -----------------------------------
    # MAIN RCA LOGIC (FINAL)
    # -----------------------------------
    def analyze_path(self, vm_name, port):
        issues = []
        path = []

        # ---------------------------
        # BASIC TOPOLOGY
        # ---------------------------

        # ---------------------------
        # BASIC TOPOLOGY
        # ---------------------------
        query = """
        MATCH (vm:VM {name:$vm_name})
        OPTIONAL MATCH (vm)-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (nic)-[:IN_SUBNET]->(subnet)
        OPTIONAL MATCH (subnet)-[:IN_VNET]->(vnet)
        RETURN vm, nic, subnet, vnet
        """

        with self.driver.session() as session:
            records = list(session.run(query, vm_name=vm_name))

            if not records:
                return {"vm": vm_name, "path": [], "issues": ["VM not found"]}

            rec = records[0]

            if not rec["nic"]:
                return {"vm": vm_name, "path": ["VM"], "issues": ["No NIC attached"]}

            if not rec["subnet"]:
                return {"vm": vm_name, "path": ["VM", "NIC"], "issues": ["NIC not in subnet"]}

            path.extend(["VM", "NIC", "Subnet", "VNet"])

        # ---------------------------
        # ROUTE CHECK (FIRST PRIORITY)
        # ---------------------------
        routes = self.get_routes(vm_name)

        if routes:
            path.append("RouteTable")

            for route in routes:
                if route["prefix"] == "0.0.0.0/0" and route["next_hop"] in ["None", "Blackhole"]:
                    return {
                        "vm": vm_name,
                        "path": path,
                        "issues": ["Blackhole route detected"]
                    }

        # ---------------------------
        # PUBLIC / PRIVATE
        # ---------------------------
        query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (pip:PublicIP)-[:ATTACHED_TO]->(nic)
        RETURN pip
        """

        has_public = False

        with self.driver.session() as session:
            for r in session.run(query, vm_name=vm_name):
                if r["pip"]:
                    has_public = True
                    break

        path.append("PublicIP" if has_public else "Private")

        # ---------------------------
        # NSG CHECK
        # ---------------------------
        rules = self.get_nsg_rules(vm_name)

        if rules:
            path.append("NSG")

            port = str(port)
            rules = sorted(rules, key=lambda x: x["priority"])

            for rule in rules:
                if rule["port"] == port or rule["port"] == "*":
                    if rule["access"] == "Deny":
                        return {
                            "vm": vm_name,
                            "path": path,
                            "issues": [f"Blocked by NSG rule: {rule['name']}"]
                        }
                    else:
                        break

        # ---------------------------
        # VM HEALTH
        # ---------------------------
        health = self.analyze_vm_health(vm_name)

        if health["status"] == "STOPPED":
            issues.append("VM is stopped")

        # ---------------------------
        # FINAL
        # ---------------------------
        return {
            "vm": vm_name,
            "path": path,
            "issues": issues if issues else ["No issues detected"]
        }