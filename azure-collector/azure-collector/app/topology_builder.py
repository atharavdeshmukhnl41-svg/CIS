class TopologyBuilder:
 
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.node_ids = set()
 
    # =========================
    # ADD NODE
    # =========================
    def add_node(self, node_id, label, name, properties=None):
    
        if not node_id:
            return
    
        # 🔥 FIX: allow update instead of skip
        existing = next((n for n in self.nodes if n["id"] == node_id), None)
    
        if existing:
            if properties:
                existing.update(properties)
            return
    
        node = {
            "id": node_id,
            "label": label,
            "name": name
        }
    
        if properties:
            node.update(properties)
    
        self.nodes.append(node)
        self.node_ids.add(node_id)
    # =========================
    # ADD EDGE
    # =========================
    def add_edge(self, source, target, rel_type):
 
        if not source or not target:
            return
 
        self.edges.append({
            "source": source,
            "target": target,
            "type": rel_type
        })
 
    # =========================
    # BUILD TOPOLOGY (FINAL)
    # =========================
    def build(self,
              vms,
              nics,
              subnets,
              vnets,
              nsgs,
              public_ips,
              route_tables,
              load_balancers,
              nat_gateways,
              databases
              ):
 
        # =========================
        # VM NODES
        # =========================
        for vm in vms:
            self.add_node(vm.id, "VM", vm.name, {
                "power_state": getattr(vm, "power_state", "running")
            })
 
        # =========================
        # VM → NIC MAP (FINAL FIX)
        # =========================
        vm_nic_map = {}
 
        for vm in vms:
            try:
                if vm.network_profile and vm.network_profile.network_interfaces:
                    for nic_ref in vm.network_profile.network_interfaces:
 
                        full_id = nic_ref.id.lower().strip()
                        nic_name = full_id.split("/")[-1]
 
                        vm_nic_map[full_id] = vm.id
                        vm_nic_map[nic_name] = vm.id
 
            except Exception:
                pass
 
        # =========================
        # NIC
        # =========================
        for nic in nics:
 
            self.add_node(nic.id, "NIC", nic.name)
 
            nic_id = nic.id.lower().strip()
            nic_name = nic.name.lower().strip()
 
            vm_id = vm_nic_map.get(nic_id)
 
            if not vm_id:
                vm_id = vm_nic_map.get(nic_name)
 
            if vm_id:
                self.add_edge(vm_id, nic.id, "HAS_NIC")
 
            # NIC → SUBNET + PUBLIC IP
            if nic.ip_configurations:
                for ip in nic.ip_configurations:
 
                    if ip.subnet and ip.subnet.id:
                        self.add_edge(nic.id, ip.subnet.id, "IN_SUBNET")
 
                    if ip.public_ip_address and ip.public_ip_address.id:
                        self.add_edge(nic.id, ip.public_ip_address.id, "HAS_PUBLIC_IP")
 
            # NIC → NSG
            try:
                nsg = getattr(nic, "network_security_group", None)
                if nsg and nsg.id:
                    self.add_node(nsg.id, "NSG", nsg.id.split("/")[-1])
                    self.add_edge(nic.id, nsg.id, "SECURED_BY")
            except Exception:
                pass
 
        # =========================
        # SUBNET
        # =========================
        for subnet in subnets:
 
            self.add_node(subnet.id, "Subnet", subnet.name)
 
            if "/subnets/" in subnet.id:
                vnet_id = subnet.id.split("/subnets/")[0]
                self.add_edge(subnet.id, vnet_id, "IN_VNET")
 
            try:
                nsg = getattr(subnet, "network_security_group", None)
                if nsg and nsg.id:
                    self.add_node(nsg.id, "NSG", nsg.id.split("/")[-1])
                    self.add_edge(subnet.id, nsg.id, "SECURED_BY")
            except Exception:
                pass
 
        # =========================
        # VNET
        # =========================
        for vnet in vnets:
            self.add_node(vnet.id, "VNet", vnet.name)
        # =========================

        # NSG RULES (FINAL REAL FIX)

        # =========================

        for nsg in nsgs:

        

            self.add_node(nsg.id, "NSG", nsg.name)

        

            # Combine both rule types

            all_rules = []

        

            if hasattr(nsg, "security_rules") and nsg.security_rules:

                all_rules.extend(nsg.security_rules)

        

            if hasattr(nsg, "default_security_rules") and nsg.default_security_rules:

                all_rules.extend(nsg.default_security_rules)

        

            for rule in all_rules:

        

                rule_id = f"{nsg.id}-{rule.name}"

        

                # ----------------------------

                # PORT FIX (HANDLE ALL CASES)

                # ----------------------------

                port = "*"

        

                if hasattr(rule, "destination_port_range") and rule.destination_port_range:

                    port = rule.destination_port_range

        

                elif hasattr(rule, "destination_port_ranges") and rule.destination_port_ranges:

                    port = ",".join(rule.destination_port_ranges)

        

                # ----------------------------

                # PRIORITY FIX

                # ----------------------------

                priority = getattr(rule, "priority", 1000)

        

                # ----------------------------

                # ACCESS FIX

                # ----------------------------

                access = getattr(rule, "access", "Deny")

        

                # ----------------------------

                # PROTOCOL (OPTIONAL BUT GOOD)

                # ----------------------------

                protocol = getattr(rule, "protocol", "*")

        

                # ----------------------------

                # ADD NODE

                # ----------------------------

                self.add_node(rule_id, "RULE", rule.name, {

                    "port": str(port),

                    "access": access,

                    "priority": priority,

                    "protocol": protocol

                })

        

                self.add_edge(nsg.id, rule_id, "HAS_RULE")



        # =========================
        # PUBLIC IP
        # =========================
        for pip in public_ips:
            self.add_node(pip.id, "PublicIP", pip.name)
 
        # =========================
        # ROUTE TABLE
        # =========================
        for rt in route_tables:
 
            self.add_node(rt.id, "RouteTable", rt.name)
 
            try:
                if rt.subnets:
                    for subnet in rt.subnets:
                        self.add_edge(rt.id, subnet.id, "ASSOCIATED_WITH")
            except Exception:
                pass
 
            if rt.routes:
                for route in rt.routes:
 
                    route_id = f"{rt.id}-{route.name}"
 
                    self.add_node(route_id, "Route", route.name, {
                        "next_hop": route.next_hop_type
                    })
 
                    self.add_edge(rt.id, route_id, "HAS_ROUTE")
 
        # =========================
        # LOAD BALANCER (FINAL FIX)
        # =========================
        for lb in load_balancers:
        
            self.add_node(lb.id, "LoadBalancer", lb.name)
        
            # BACKEND POOL → NIC FIX
            try:
                if lb.backend_address_pools:
                    for pool in lb.backend_address_pools:
        
                        if hasattr(pool, "backend_ip_configurations") and pool.backend_ip_configurations:
        
                            for ip_config in pool.backend_ip_configurations:
        
                                # CRITICAL FIX: extract NIC ID correctly
                                if hasattr(ip_config, "id") and ip_config.id:
        
                                    # Example format:
                                    # /subscriptions/.../networkInterfaces/<nic-name>/ipConfigurations/<name>
        
                                    parts = ip_config.id.split("/ipConfigurations/")
        
                                    if len(parts) > 0:
                                        nic_id = parts[0]
        
                                        self.add_edge(lb.id, nic_id, "HAS_BACKEND")
        
            except Exception:
                pass
        
            # LB RULES (KEEP SAME)
            if lb.load_balancing_rules:
                for rule in lb.load_balancing_rules:
        
                    rule_id = f"{lb.id}-{rule.name}"
        
                    self.add_node(rule_id, "LBRule", rule.name, {
                        "port": str(rule.frontend_port)
                    })
        
                    self.add_edge(lb.id, rule_id, "HAS_RULE")
 
        # =========================
        # NAT GATEWAY
        # =========================
        for nat in nat_gateways:
 
            self.add_node(nat.id, "NATGateway", nat.name)
 
            try:
                if nat.subnets:
                    for subnet in nat.subnets:
                        self.add_edge(nat.id, subnet.id, "ASSOCIATED_WITH")
            except Exception:
                pass

        # =========================
        # DATABASE NODES (NEW SAFE)
        # =========================
        for db in databases:
        
            self.add_node(db["id"], "Database", db["name"])
        
        # =========================
        # VM → DB (AUTO LINK SIMPLE LOGIC)
        # =========================
        # NOTE: simple assumption → same resource group
        for vm in vms:
            for db in databases:
        
                if vm.id.split("/resourceGroups/")[1].split("/")[0] == db["id"].split("/resourceGroups/")[1].split("/")[0]:
        
                    self.add_edge(vm.id, db["id"], "CONNECTS_TO")

        return {
            "nodes": self.nodes,
            "edges": self.edges
        }