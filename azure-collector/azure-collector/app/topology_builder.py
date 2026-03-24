class TopologyBuilder:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.node_ids = set()   # ✅ FIX (must exist)

    # -----------------------------------
    # ADD NODE
    # -----------------------------------
    def add_node(self, node_id, label, name, extra=None):
        if not node_id or node_id in self.node_ids:
            return

        node = {
            "id": node_id,
            "label": label,
            "name": name
        }

        if extra:
            node.update(extra)

        self.nodes.append(node)
        self.node_ids.add(node_id)

    # -----------------------------------
    # ADD EDGE
    # -----------------------------------
    def add_edge(self, source, target, rel):
        if not source or not target:
            return

        self.edges.append({
            "source": source,
            "target": target,
            "type": rel
        })

    # -----------------------------------
    # BUILD TOPOLOGY
    # -----------------------------------
    def build(self, vms, nics, vnets, nsgs, public_ips, route_tables):

        # ---------------------------
        # NIC + SUBNET
        # ---------------------------
        for nic in nics:
            self.add_node(nic.id, "NIC", nic.name)

            if nic.ip_configurations:
                ip_conf = nic.ip_configurations[0]

                if ip_conf.subnet:
                    subnet_id = ip_conf.subnet.id
                    subnet_name = subnet_id.split("/")[-1]

                    self.add_node(subnet_id, "SUBNET", subnet_name)
                    self.add_edge(nic.id, subnet_id, "IN_SUBNET")

            # NIC → NSG
            if nic.network_security_group:
                self.add_edge(nic.id, nic.network_security_group.id, "SECURED_BY")

        # ---------------------------
        # VNET + SUBNET
        # ---------------------------
        for vnet in vnets:
            self.add_node(vnet.id, "VNET", vnet.name)

            for subnet in vnet.subnets:
                self.add_node(subnet.id, "SUBNET", subnet.name)
                self.add_edge(subnet.id, vnet.id, "IN_VNET")

        # ---------------------------
        # VM → NIC
        # ---------------------------
        for vm in vms:
            self.add_node(vm.id, "VM", vm.name)

            if vm.network_profile:
                for nic in vm.network_profile.network_interfaces:
                    self.add_edge(vm.id, nic.id, "HAS_NIC")

        # ---------------------------
        # NSG + RULES
        # ---------------------------
        from app.nsg_parser import parse_nsg_rules

        for nsg in nsgs:
            self.add_node(nsg.id, "NSG", nsg.name)

            rules = parse_nsg_rules(nsg)

            for rule in rules:
                rule_id = f"{nsg.id}/rule/{rule['name']}"

                self.add_node(
                    rule_id,
                    "RULE",
                    rule["name"],
                    {
                        "port": str(rule.get("port")),
                        "access": rule.get("access"),
                        "priority": int(rule.get("priority") or 9999)
                    }
                )

                self.add_edge(nsg.id, rule_id, "HAS_RULE")

        # ---------------------------
        # PUBLIC IP → NIC
        # ---------------------------
        for pip in public_ips:
            self.add_node(pip.id, "PublicIP", pip.name)

            if pip.ip_configuration:
                self.add_edge(pip.id, pip.ip_configuration.id, "ATTACHED_TO")

        # ---------------------------
        # ROUTE TABLE + ROUTES
        # ---------------------------
        for rt in route_tables:
            self.add_node(rt.id, "RouteTable", rt.name)

            # RouteTable → Subnet
            if hasattr(rt, "subnets") and rt.subnets:
                for subnet in rt.subnets:
                    self.add_edge(rt.id, subnet.id, "ASSOCIATED_WITH")

            # Routes
            if rt.routes:
                for route in rt.routes:
                    route_id = f"{rt.id}/route/{route.name}"

                    self.add_node(
                        route_id,
                        "ROUTE",
                        route.name,
                        {
                            "prefix": route.address_prefix,
                            "next_hop": route.next_hop_type
                        }
                    )

                    self.add_edge(rt.id, route_id, "HAS_ROUTE")

        # ---------------------------
        # FINAL
        # ---------------------------
        return {
            "nodes": self.nodes,
            "edges": self.edges
        }