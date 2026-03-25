from app.azure_metrics import AzureMetricsCollector

from neo4j import GraphDatabase

from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

 

def main():

 

    vm_name = input("Enter VM name: ")

 

    collector = AzureMetricsCollector()

 

    print(f"\nCollecting metrics for VM: {vm_name}")

 

    collector.collect_and_store(vm_name)

 

    print("\n===== METRICS =====\n")

 

    driver = GraphDatabase.driver(

        NEO4J_URI,

        auth=(NEO4J_USER, NEO4J_PASSWORD)

    )

 

    with driver.session() as session:

 

        result = session.run("""

        MATCH (vm:VM {name:$vm})-[:HAS_METRIC]->(m)

        RETURN m.cpu AS cpu,

               m.network_in AS net_in,

               m.network_out AS net_out

        """, vm=vm_name)

 

        record = result.single()

 

        if record:

            print("CPU:", record["cpu"])

            print("Network In:", record["net_in"])

            print("Network Out:", record["net_out"])

        else:

            print("❌ No metrics found in DB")

 

    driver.close()

 

 

if __name__ == "__main__":

    main()

