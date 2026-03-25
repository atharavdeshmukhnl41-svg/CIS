from fastapi import FastAPI
from app.rca_engine import RCAEngine
from app.dependency_mapper import DependencyMapper
 
app = FastAPI()
 
engine = RCAEngine()
mapper = DependencyMapper()
 
# =========================
# VM RCA
# =========================
@app.get("/rca/vm")
def vm_rca(name: str, port: int):
 
    result = engine.analyze_path(name, port)
 
    return result
 
 
# =========================
# APPLICATION RCA
# =========================
@app.get("/rca/app")
def app_rca(name: str, port: int):
 
    apps = mapper.map_application(name)
 
    if not apps:
        return {"error": "No application mapping found"}
 
    output = []
 
    for app_data in apps:
 
        app_result = {
            "app": app_data["app"],
            "load_balancer": app_data["lb"],
            "vms": []
        }
 
        for vm in app_data["vms"]:
 
            vm_result = engine.analyze_path(vm, port)
            db_ok, db_msg = engine.check_database(vm)
 
            app_result["vms"].append({
                "vm": vm,
                "rca": vm_result,
                "database": db_msg
            })
 
        output.append(app_result)
 
    return output
 
 
# =========================
# METRICS
# =========================
@app.get("/metrics")
def metrics(vm: str):
 
    data = engine.get_metrics(vm)
 
    if not data:
        return {"error": "No metrics found"}
 
    return data