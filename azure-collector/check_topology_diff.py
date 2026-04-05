from neo4j import GraphDatabase

# Connect to Neo4j
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

query = """
MATCH (vm:VM {name:$vm_name})-[:HAS_NIC]->(nic)
OPTIONAL MATCH (lb:LoadBalancer)-[:BALANCES]->(nic)
OPTIONAL MATCH (nic)-[:HAS_PUBLIC_IP]->(pip)
OPTIONAL MATCH (nic)-[:SECURED_BY]->(nsg)
OPTIONAL MATCH (nic)-[:IN_SUBNET]->(subnet)-[:USES_ROUTE_TABLE]->(rt)
RETURN {
    vm_name: vm.name,
    power_state: vm.power_state,
    has_load_balancer: lb IS NOT NULL,
    load_balancer_name: lb.name,
    has_public_ip: pip IS NOT NULL,
    public_ip: pip.name,
    has_nsg: nsg IS NOT NULL,
    nsg_name: nsg.name,
    has_route_table: rt IS NOT NULL,
    route_table: rt.name
}
"""

with driver.session() as session:
    print("=" * 60)
    print("CIP VM Topology")
    print("=" * 60)
    result = session.run(query, {"vm_name": "CIP"})
    for row in result:
        data = row.data()
        for key, value in data.items():
            print(f"{key}: {value}")
    
    print("\n" + "=" * 60)
    print("CIP1 VM Topology")
    print("=" * 60)
    result = session.run(query, {"vm_name": "cip1"})
    for row in result:
        data = row.data()
        for key, value in data.items():
            print(f"{key}: {value}")

driver.close()
