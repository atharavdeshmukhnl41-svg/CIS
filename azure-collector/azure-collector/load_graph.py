import json
from app.neo4j_loader import Neo4jLoader

def main():
    with open("topology.json") as f:
        topology = json.load(f)

    loader = Neo4jLoader()
    loader.load_topology(topology)
    loader.close()

    print("Loaded into Neo4j!")

if __name__ == "__main__":
    main()