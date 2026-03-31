from fastapi import APIRouter
from app.alert_engine import AlertEngine
 
router = APIRouter()
 
engine = AlertEngine()
 
# =========================
# TRIGGER ALERT CHECK
# =========================
@router.get("/alerts/check")
def check_alert(vm: str):
    result = engine.evaluate_vm(vm)
 
    if not result:
        return {"status": "No alerts"}
 
    return result
 
 
# =========================
# GET ALERTS FROM DB
# =========================
@router.get("/alerts")
def get_alerts():
    from neo4j import GraphDatabase
    from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
 
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )
 
    query = """
    MATCH (vm:VM)-[:HAS_ALERT]->(a)
    RETURN vm.name AS vm, a.issues AS issues, a.path AS path
    ORDER BY a.timestamp DESC
    """
 
    with driver.session() as session:
        result = session.run(query)
 
        alerts = []
        for r in result:
            alerts.append({
                "vm": r["vm"],
                "issues": r["issues"],
                "path": r["path"]
            })
 
        return alerts