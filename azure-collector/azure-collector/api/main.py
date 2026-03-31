from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from datetime import datetime, timezone
 
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from app.rca_engine import RCAEngine
from app.dependency_mapper import DependencyMapper
from app.metrics_analyzer import MetricsAnalyzer
 
# =========================
# INIT
# =========================
app = FastAPI()
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)
 
# =========================
# INGEST METRICS
# =========================
@app.post("/agent/metrics")
def ingest_metrics(data: dict):
 
    print("🔥 Incoming Metrics:", data)
 
    query = """
    MERGE (m:Metrics {vm: $vm})
    SET
        m.cpu = $cpu,
        m.network_in = $network_in,
        m.network_out = $network_out,
        m.timestamp = datetime({timezone: 'UTC'})
    """
 
    try:
        with driver.session() as session:
            result = session.run(query, {
                "vm": data.get("vm"),
                "cpu": float(data.get("cpu", 0)),
                "network_in": float(data.get("network_in", 0)),
                "network_out": float(data.get("network_out", 0))
            })
            result.consume()
 
        print("✅ Stored in Neo4j")
        return {"status": "stored"}
 
    except Exception as e:
        print("❌ DB WRITE ERROR:", str(e))
        return {"error": str(e)}
 
# =========================
# GET METRICS (FINAL FIX)
# =========================
@app.get("/metrics")
def get_metrics(vm: str):
 
    query = """
    MATCH (m:Metrics {vm: $vm})
    RETURN m.cpu AS cpu,
           m.network_in AS network_in,
           m.network_out AS network_out,
           m.timestamp AS timestamp
    ORDER BY m.timestamp DESC
    LIMIT 1
    """
 
    try:
        with driver.session(default_access_mode="READ") as session:
            result = session.run(query, {"vm": vm}).data()
 
        if not result:
            return {
                "cpu": 0,
                "network_in": 0,
                "network_out": 0,
                "status": "no_data"
            }
 
        data = result[0]
 
        cpu = float(data.get("cpu") or 0)
        net_in = float(data.get("network_in") or 0)
        net_out = float(data.get("network_out") or 0)
 
        last_time = data.get("timestamp")
 
        # 🔥 FIXED timestamp handling
        if last_time:
            if hasattr(last_time, "to_native"):
                last_time = last_time.to_native()
 
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
 
            now = datetime.now(timezone.utc)
            diff = (now - last_time).total_seconds()
 
            print("DEBUG TIME DIFF:", diff)
 
            # 🔥 FINAL LOGIC
            if diff > 20:
                return {
                    "cpu": 0,
                    "network_in": 0,
                    "network_out": 0,
                    "status": "vm_down"
                }
 
        return {
            "cpu": cpu,
            "network_in": net_in,
            "network_out": net_out,
            "status": "running"
        }
 
    except Exception as e:
        print("❌ METRICS ERROR:", str(e))
        return {
            "cpu": 0,
            "network_in": 0,
            "network_out": 0,
            "status": "error"
        }
 
# =========================
# VM RCA
# =========================
@app.get("/rca/vm")
def vm_rca(name: str, port: int):
    return RCAEngine().analyze_path(name, port)
 
# =========================
# APP RCA
# =========================
@app.get("/rca/app")
def app_rca(name: str, port: int):
 
    mapper = DependencyMapper()
    engine = RCAEngine()
 
    apps = mapper.map_application(name)
 
    if not apps:
        return {"error": "No application mapping found"}
 
    results = []
 
    for app in apps:
        for vm in app.get("vms", []):
            r = engine.analyze_path(vm, port)
 
            results.append({
                "app": app["app"],
                "vm": vm,
                "issues": r.get("issues", []),
                "path": r.get("path", [])
            })
 
    return results
 
# =========================
# ALERTS (FIXED)
# =========================
@app.get("/alerts")
def get_alerts(vm: str):
 
    analyzer = MetricsAnalyzer()
 
    # 🔥 ALWAYS fetch fresh metrics
    metrics = get_metrics(vm)
 
    alerts = analyzer.analyze(metrics)
 
    return {"vm": vm, "alerts": alerts}
 
# =========================
# TOPOLOGY (FINAL FIX)
# =========================
@app.get("/topology")
def get_topology():
 
    nodes = []
    edges = []
 
    try:
        with driver.session() as session:
 
            node_result = session.run("""
            MATCH (n)
            RETURN id(n) AS id,
                   labels(n) AS labels,
                   n.name AS name
            """)
 
            for r in node_result:
                nodes.append({
                    "id": r["id"],
                    "label": r["name"] if r["name"] else "Unknown",
                    "group": r["labels"][0] if r["labels"] else "Node"
                })
 
            edge_result = session.run("""
            MATCH (a)-[r]->(b)
            RETURN id(a) AS source,
                   id(b) AS target,
                   type(r) AS type
            """)
 
            for r in edge_result:
                edges.append({
                    "from": r["source"],
                    "to": r["target"],
                    "label": r["type"]
                })
 
        return {"nodes": nodes, "edges": edges}
 
    except Exception as e:
        return {"error": str(e)}