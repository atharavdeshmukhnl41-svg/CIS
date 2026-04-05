#!/usr/bin/env python3
"""
Load sample topology data into Neo4j for testing
"""

from neo4j import GraphDatabase
import os

# Neo4j connection
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USERNAME = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

def load_sample_data():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

    try:
        with driver.session() as session:
            # Clear existing data
            session.run("MATCH (n) DETACH DELETE n")
            print("✅ Cleared existing data")

            # Create sample VMs
            session.run("""
            CREATE (vm1:VM {
                name: 'web-server-01',
                resource_group: 'prod-rg',
                location: 'eastus',
                provisioning_state: 'Succeeded',
                type: 'Microsoft.Compute/virtualMachines'
            })
            """)

            session.run("""
            CREATE (vm2:VM {
                name: 'app-server-01',
                resource_group: 'prod-rg',
                location: 'eastus',
                provisioning_state: 'Succeeded',
                type: 'Microsoft.Compute/virtualMachines'
            })
            """)

            # Create sample NSG
            session.run("""
            CREATE (nsg:NSG {
                name: 'prod-nsg',
                resource_group: 'prod-rg',
                location: 'eastus',
                provisioning_state: 'Succeeded',
                type: 'Microsoft.Network/networkSecurityGroups'
            })
            """)

            # Create sample Route Table
            session.run("""
            CREATE (rt:RouteTable {
                name: 'prod-rt',
                resource_group: 'prod-rg',
                location: 'eastus',
                provisioning_state: 'Succeeded',
                type: 'Microsoft.Network/routeTables'
            })
            """)

            # Create relationships
            session.run("""
            MATCH (vm1:VM {name: 'web-server-01'}), (nsg:NSG {name: 'prod-nsg'})
            CREATE (vm1)-[:SECURED_BY]->(nsg)
            """)

            session.run("""
            MATCH (vm2:VM {name: 'app-server-01'}), (nsg:NSG {name: 'prod-nsg'})
            CREATE (vm2)-[:SECURED_BY]->(nsg)
            """)

            session.run("""
            MATCH (vm1:VM {name: 'web-server-01'}), (rt:RouteTable {name: 'prod-rt'})
            CREATE (vm1)-[:USES_ROUTE_TABLE]->(rt)
            """)

            # Add some NSG rules
            session.run("""
            MATCH (nsg:NSG {name: 'prod-nsg'})
            CREATE (nsg)-[:HAS_RULE]->(:Rule {
                name: 'allow-ssh',
                access: 'Allow',
                priority: 100,
                port: 22
            })
            """)

            session.run("""
            MATCH (nsg:NSG {name: 'prod-nsg'})
            CREATE (nsg)-[:HAS_RULE]->(:Rule {
                name: 'deny-http',
                access: 'Deny',
                priority: 200,
                port: 80
            })
            """)

            # Add a blackhole route to demonstrate failure detection
            session.run("""
            MATCH (rt:RouteTable {name: 'prod-rt'})
            CREATE (rt)-[:HAS_ROUTE]->(:Route {
                name: 'blackhole-route',
                address_prefix: '0.0.0.0/0',
                next_hop: 'None'
            })
            """)

            # Add some sample metrics
            session.run("""
            CREATE (:Metrics {
                vm: 'web-server-01',
                cpu: 85.5,
                network_in: 1024.5,
                network_out: 2048.2,
                timestamp: datetime()
            })
            """)

            session.run("""
            CREATE (:Metrics {
                vm: 'app-server-01',
                cpu: 0.0,
                network_in: 0.0,
                network_out: 0.0,
                timestamp: datetime()
            })
            """)

            print("✅ Sample topology data loaded successfully!")
            print("📊 Created:")
            print("   - 2 VMs (web-server-01, app-server-01)")
            print("   - 1 NSG with rules (blocking port 80)")
            print("   - 1 Route Table with blackhole route")
            print("   - Sample metrics data")

    except Exception as e:
        print(f"❌ Error loading sample data: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    load_sample_data()