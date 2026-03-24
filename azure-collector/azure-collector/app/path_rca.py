from neo4j import GraphDatabase
from app.config import *


class PathRCA:

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def analyze_path(self, vm_name, port):
        """
        Analyze network path for a VM to detect connectivity issues.
        
        RCA Flow:
        1. Validate topology
        2. Check route table
        3. Check NSG rules (priority-based)
        4. Check VM health
        
        Returns:
        {
            "status": "SUCCESS" or "FAIL",
            "reason": "...",
            "details": {...}
        }
        """
        try:
            # Step 1: Validate topology
            topology_result = self._validate_topology(vm_name)
            if topology_result["status"] == "FAIL":
                return topology_result
            
            # Step 2: Check route table
            route_result = self._check_routes(vm_name)
            if route_result["status"] == "FAIL":
                return route_result
            
            # Step 3: Check NSG rules
            nsg_result = self._check_nsg_rules(vm_name, port)
            if nsg_result["status"] == "FAIL":
                return nsg_result
            
            # Step 4: Check VM health
            health_result = self._check_vm_health(vm_name)
            if health_result["status"] == "FAIL":
                return health_result
            
            # Success
            return {
                "status": "SUCCESS",
                "reason": "Network path is clear",
                "details": {
                    "path": topology_result["details"]["path"],
                    "vm_health": health_result["details"]
                }
            }
            
        except Exception as e:
            return {
                "status": "FAIL",
                "reason": f"Analysis failed: {str(e)}",
                "details": {}
            }

    def _validate_topology(self, vm_name):
        """Validate basic network topology exists."""
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
                return {
                    "status": "FAIL",
                    "reason": "VM not found in topology",
                    "details": {}
                }
            
            rec = records[0]
            
            if not rec["nic"]:
                return {
                    "status": "FAIL", 
                    "reason": "No NIC attached to VM",
                    "details": {"path": ["VM"]}
                }
            
            if not rec["subnet"]:
                return {
                    "status": "FAIL",
                    "reason": "NIC not associated with subnet", 
                    "details": {"path": ["VM", "NIC"]}
                }
            
            path = ["VM", "NIC", "SUBNET"]
            if rec["vnet"]:
                path.append("VNET")
            
            return {
                "status": "SUCCESS",
                "reason": "Topology validated",
                "details": {"path": path}
            }

    def _check_routes(self, vm_name):
        """Check for blackhole routes."""
        query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (nic)-[:IN_SUBNET]->(subnet)
        OPTIONAL MATCH (rt:RouteTable)-[:ASSOCIATED_WITH]->(subnet)
        OPTIONAL MATCH (rt)-[:HAS_ROUTE]->(route)
        RETURN route
        """
        
        with self.driver.session() as session:
            routes = []
            for record in session.run(query, vm_name=vm_name):
                route = record["route"]
                if route:
                    routes.append({
                        "prefix": route.get("prefix"),
                        "next_hop": route.get("next_hop")
                    })
            
            # Check for blackhole default route
            for route in routes:
                if route["prefix"] == "0.0.0.0/0" and route["next_hop"] in ["None", "Blackhole"]:
                    return {
                        "status": "FAIL",
                        "reason": "Blackhole route detected in route table",
                        "details": {"route": route}
                    }
            
            return {
                "status": "SUCCESS",
                "reason": "No blackhole routes found",
                "details": {"routes": routes}
            }

    def _check_nsg_rules(self, vm_name, port):
        """Check NSG rules for port blocking."""
        query = """
        MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
        OPTIONAL MATCH (nic)-[:SECURED_BY]->(nsg)
        OPTIONAL MATCH (nsg)-[:HAS_RULE]->(rule)
        RETURN rule
        """
        
        with self.driver.session() as session:
            rules = []
            for record in session.run(query, vm_name=vm_name):
                rule = record["rule"]
                if rule:
                    rules.append({
                        "name": rule.get("name"),
                        "port": str(rule.get("port", "")),
                        "access": rule.get("access"),
                        "priority": int(rule.get("priority", 9999))
                    })
            
            if not rules:
                return {
                    "status": "SUCCESS",
                    "reason": "No NSG rules found",
                    "details": {"rules": []}
                }
            
            # Sort by priority (lower number = higher priority)
            rules.sort(key=lambda x: x["priority"])
            
            port_str = str(port)
            
            for rule in rules:
                # Check if rule applies to this port
                if rule["port"] == port_str or rule["port"] == "*":
                    if rule["access"] == "Deny":
                        return {
                            "status": "FAIL",
                            "reason": f"Port {port} blocked by NSG rule '{rule['name']}' (priority {rule['priority']})",
                            "details": {"blocking_rule": rule}
                        }
                    elif rule["access"] == "Allow":
                        # Allow rule found, stop checking (higher priority rules already checked)
                        break
            
            return {
                "status": "SUCCESS",
                "reason": "No blocking NSG rules found",
                "details": {"rules": rules}
            }

    def _check_vm_health(self, vm_name):
        """Check VM power state."""
        query = """
        MATCH (vm:VM {name:$vm_name})
        RETURN vm.power_state AS state
        """
        
        with self.driver.session() as session:
            result = session.run(query, vm_name=vm_name)
            record = result.single()
            
            if not record:
                return {
                    "status": "FAIL",
                    "reason": "VM not found",
                    "details": {}
                }
            
            state = record.get("state", "").lower()
            
            if state != "running":
                return {
                    "status": "FAIL",
                    "reason": f"VM is in '{state}' state",
                    "details": {"power_state": state}
                }
            
            return {
                "status": "SUCCESS",
                "reason": "VM is running",
                "details": {"power_state": state}
            }

    def close(self):
        self.driver.close()