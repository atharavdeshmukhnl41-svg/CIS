from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "Iwillwin$123"  # change this

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def create_full_graph(tx, vm, location, subnet, vnet, nsg):
    tx.run("""
        MERGE (v:VM {name: $vm})
        SET v.location = $location

        MERGE (s:Subnet {name: $subnet})
        MERGE (vn:VNet {name: $vnet})

        MERGE (v)-[:IN_SUBNET]->(s)
        MERGE (s)-[:IN_VNET]->(vn)

        FOREACH (_ IN CASE WHEN $nsg IS NOT NULL THEN [1] ELSE [] END |
            MERGE (n:NSG {name: $nsg})
            MERGE (s)-[:PROTECTED_BY]->(n)
        )
    """, vm=vm, location=location, subnet=subnet, vnet=vnet, nsg=nsg)


def load_full_graph(data):
    with driver.session() as session:
        for item in data:
            session.execute_write(
                create_full_graph,
                item["vm"],
                item["location"],
                item["subnet"],
                item["vnet"],
                item["nsg"]
            )


def close():
    driver.close()