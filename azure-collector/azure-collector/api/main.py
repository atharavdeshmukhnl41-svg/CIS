from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from datetime import datetime, timezone
from typing import Optional
from .alerts import router as alerts_router
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from app.rca_engine import RCAEngine
from app.dependency_mapper import DependencyMapper
from app.metrics_analyzer import MetricsAnalyzer
from app.approval_engine import ApprovalEngine
from app.execution_engine import ExecutionEngine
from app.azure_fetcher import AzureFetcher
from app.neo4j_loader import Neo4jLoader
# =========================
# INIT
# =========================
app = FastAPI()
approval_engine = ApprovalEngine()
execution_engine = ExecutionEngine()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts_router)
 
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
    try:
        return RCAEngine().analyze_path(name, port)
    except Exception as e:
        print(f"❌ RCA ERROR: {str(e)}")
        # Return sample RCA data for testing
        return get_sample_rca_data(name, port)

# =========================
# VM LIST
# =========================
@app.get("/vms")
def get_vms():
    try:
        with driver.session(default_access_mode="READ") as session:
            result = session.run("""
            MATCH (v:VM)
            RETURN DISTINCT
                   coalesce(v.name, v.label, '') AS name,
                   v.label AS label,
                   v.id AS id
            ORDER BY toLower(coalesce(v.name, v.label, ''))
            """)
            vms = [
                {
                    "name": row["name"],
                    "label": row.get("label") or row["name"],
                    "id": row.get("id")
                }
                for row in result if row["name"]
            ]
        return {"vms": vms}
    except Exception as e:
        print(f"❌ VMS ERROR: {str(e)}")
        return {"vms": []}

# =========================
# REFRESH AZURE TOPOLOGY
# =========================
@app.post("/refresh")
def refresh_topology():
    try:
        from app.config import SUBSCRIPTION_ID
        print(f"DEBUG: SUBSCRIPTION_ID = {SUBSCRIPTION_ID}")
        
        fetcher = AzureFetcher()
        topology = fetcher.get_topology()

        if not topology or not topology.get("nodes"):
            return {"error": "Azure topology fetch returned no data"}

        loader = Neo4jLoader()
        loader.load_topology(topology)
        loader.enrich_vm_metadata()
        loader.close()

        return {
            "status": "refreshed",
            "nodes": len(topology["nodes"]),
            "edges": len(topology["edges"])
        }
    except Exception as e:
        print(f"❌ REFRESH ERROR: {str(e)}")
        return {"error": str(e)}

# =========================
# SAMPLE RCA FALLBACK
# =========================
def get_sample_rca_data(vm, port):
    return {
        "vm": vm,
        "path": ["PublicIP", "LoadBalancer", "VM", "NIC", "NSG", "RouteTable", "Metrics"],
        "issues": [
            f"❌ NSG blocks port {port}",
            "❌ Blackhole route found",
            "⚠️ VM metrics show warnings"
        ],
        "root_cause": "NSG denies access or route table blocks traffic",
        "impact": "Load Balancer + VM unreachable",
        "fix": f"Update NSG rules and route table to allow traffic on port {port}",
        "confidence": 92,
        "note": "Sample RCA data returned because the backend topology is unavailable"
    }

# =========================
# APP RCA
# =========================
@app.get("/rca/app")
def app_rca(name: str, port: int):

    try:
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
    except Exception as e:
        print(f"❌ APP RCA ERROR: {str(e)}")
        # Return sample app RCA data for testing
        return [{
            "app": name,
            "vm": f"{name}-vm-01",
            "issues": [f"❌ NSG blocks port {port}", "❌ Route table has blackhole route"],
            "path": ["VM", "NIC", "NSG", "RouteTable"],
            "note": "Using sample data - Neo4j not connected"
        }]

# =========================
# SAMPLE TOPOLOGY FALLBACK
# =========================
def get_sample_topology_data(vm=None, port=None):
    nodes = [
        {
            "id": 1,
            "label": "web-server-01",
            "group": "VM",
            "status": "warning",
            "properties": {
                "resource_group": "prod-rg",
                "location": "eastus",
                "state": "Running",
                "type": "Microsoft.Compute/virtualMachines",
                "cpu": 85.5
            }
        },
        {
            "id": 2,
            "label": "app-server-01",
            "group": "VM",
            "status": "error",
            "properties": {
                "resource_group": "prod-rg",
                "location": "eastus",
                "state": "Running",
                "type": "Microsoft.Compute/virtualMachines",
                "cpu": 0.0
            }
        },
        {
            "id": 3,
            "label": "prod-nsg",
            "group": "NSG",
            "status": "error",
            "properties": {
                "resource_group": "prod-rg",
                "location": "eastus",
                "state": "Succeeded",
                "type": "Microsoft.Network/networkSecurityGroups"
            }
        },
        {
            "id": 4,
            "label": "prod-rt",
            "group": "RouteTable",
            "status": "error",
            "properties": {
                "resource_group": "prod-rg",
                "location": "eastus",
                "state": "Succeeded",
                "type": "Microsoft.Network/routeTables"
            }
        }
    ]

    edges = [
        {
            "from": 1,
            "to": 3,
            "label": "SECURED_BY",
            "description": "Protected by Network Security Group",
            "color": "#ef4444"
        },
        {
            "from": 2,
            "to": 3,
            "label": "SECURED_BY",
            "description": "Protected by Network Security Group",
            "color": "#ef4444"
        },
        {
            "from": 1,
            "to": 4,
            "label": "USES_ROUTE_TABLE",
            "description": "Uses routing table for traffic",
            "color": "#8b5cf6"
        }
    ]

    failing_components = [
        {
            "id": 1,
            "name": "web-server-01",
            "type": "VM",
            "reason": "High CPU usage: 85.5%"
        },
        {
            "id": 2,
            "name": "app-server-01",
            "type": "VM",
            "reason": "No CPU metrics (possibly down)"
        },
        {
            "id": 3,
            "name": "prod-nsg",
            "type": "NSG",
            "reason": f"Blocks port {port or 22} (priority 200)"
        },
        {
            "id": 4,
            "name": "prod-rt",
            "type": "RouteTable",
            "reason": "Blackhole route blocking internet traffic"
        }
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "failing_components": failing_components,
        "vm": vm,
        "port": port,
        "note": "Sample topology data returned because Neo4j is unavailable"
    }

# =========================
# TOPOLOGY (ENHANCED WITH FAILURE DETECTION)
@app.get("/topology")
def get_topology(vm: Optional[str] = None, port: Optional[int] = None):

    nodes = []
    edges = []
    failing_components = []

    try:
        with driver.session() as session:

            # Get all nodes with detailed properties
            node_result = session.run("""
            MATCH (n)
            RETURN id(n) AS id,
                   labels(n) AS labels,
                   n.name AS name,
                   n.resource_group AS resource_group,
                   n.location AS location,
                   n.provisioning_state AS state,
                   n.type AS type
            """)

            for r in node_result:
                node_type = r["labels"][0] if r["labels"] else "Node"
                node_name = r["name"] or f"{node_type}-{r['id']}"

                # Determine node status and color
                status = "healthy"
                if r.get("state") and r["state"].lower() in ["failed", "error"]:
                    status = "error"
                    failing_components.append({
                        "id": r["id"],
                        "name": node_name,
                        "type": node_type,
                        "reason": f"Provisioning state: {r['state']}"
                    })

                # Enhanced node data
                node_data = {
                    "id": r["id"],
                    "label": node_name,
                    "group": node_type,
                    "status": status,
                    "properties": {
                        "resource_group": r.get("resource_group", "Unknown"),
                        "location": r.get("location", "Unknown"),
                        "state": r.get("state", "Unknown"),
                        "type": r.get("type", node_type)
                    }
                }

                # Add specific properties based on node type
                if node_type == "VM":
                    # Check VM metrics for health
                    metrics_result = session.run("""
                    MATCH (m:Metrics)
                    WHERE toLower(m.vm) = toLower($vm_name)
                    RETURN m.cpu AS cpu, m.timestamp AS timestamp
                    ORDER BY m.timestamp DESC LIMIT 1
                    """, {"vm_name": node_name})

                    metrics_data = metrics_result.single()
                    if metrics_data:
                        cpu = float(metrics_data.get("cpu", 0))
                        timestamp = metrics_data.get("timestamp")
                        if cpu > 80:
                            status = "warning"
                            failing_components.append({
                                "id": r["id"],
                                "name": node_name,
                                "type": node_type,
                                "reason": f"High CPU usage: {cpu}%"
                            })
                        elif timestamp:
                            try:
                                if hasattr(timestamp, "to_native"):
                                    timestamp = timestamp.to_native()
                                if timestamp.tzinfo is None:
                                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                                age = (datetime.now(timezone.utc) - timestamp).total_seconds()
                                node_data["properties"]["metrics_age"] = int(age)
                                if age > 120:
                                    status = "warning"
                                    failing_components.append({
                                        "id": r["id"],
                                        "name": node_name,
                                        "type": node_type,
                                        "reason": f"Metrics stale ({int(age)}s since last report)"
                                    })
                            except Exception:
                                status = "warning"
                                failing_components.append({
                                    "id": r["id"],
                                    "name": node_name,
                                    "type": node_type,
                                    "reason": "Unable to parse VM metric timestamp"
                                })

                elif node_type == "NetworkSecurityGroup":
                    # Check NSG rules for port blocking
                    rule_result = session.run("""
                    MATCH (nsg:NetworkSecurityGroup {name: $nsg_name})-[:HAS_RULE]->(rule:SecurityRule)
                    WHERE rule.access = "Deny" AND rule.destination_port = $port
                    RETURN rule.access AS access, rule.priority AS priority
                    ORDER BY rule.priority ASC LIMIT 1
                    """, {"nsg_name": node_name, "port": str(port)})

                    rule_data = rule_result.single()
                    if rule_data and rule_data.get("access") == "Deny":
                        status = "error"
                        failing_components.append({
                            "id": r["id"],
                            "name": node_name,
                            "type": node_type,
                            "reason": f"Blocks port {port} (priority {rule_data.get('priority')})"
                        })
                        node_data["status"] = status

                elif node_type == "RouteTable":
                    # Check for blackhole routes
                    route_result = session.run("""
                    MATCH (rt:RouteTable {name: $rt_name})-[:HAS_ROUTE]->(r:Route)
                    WHERE r.address_prefix = "0.0.0.0/0" AND r.next_hop = "None"
                    RETURN r
                    """, {"rt_name": node_name})

                    if route_result.single():
                        status = "error"
                        failing_components.append({
                            "id": r["id"],
                            "name": node_name,
                            "type": node_type,
                            "reason": "Blackhole route blocking internet traffic"
                        })
                        node_data["status"] = status

                nodes.append(node_data)

            # Get edges with relationship details
            edge_result = session.run("""
            MATCH (a)-[r]->(b)
            RETURN id(a) AS source,
                   id(b) AS target,
                   type(r) AS type,
                   r.description AS description
            """)

            for r in edge_result:
                edge_data = {
                    "from": r["source"],
                    "to": r["target"],
                    "label": r["type"],
                    "description": r.get("description", ""),
                    "color": "#64748b"
                }

                # Color edges based on relationship type
                if r["type"] == "HAS_NIC":
                    edge_data["color"] = "#3b82f6"
                    edge_data["description"] = "VM connected to Network Interface"
                elif r["type"] == "SECURED_BY":
                    edge_data["color"] = "#ef4444"
                    edge_data["description"] = "Protected by Network Security Group"
                elif r["type"] == "USES_ROUTE_TABLE":
                    edge_data["color"] = "#8b5cf6"
                    edge_data["description"] = "Uses routing table for traffic"
                elif r["type"] == "BALANCES":
                    edge_data["color"] = "#10b981"
                    edge_data["description"] = "Load balancer distributes traffic"
                elif r["type"] == "HAS_PUBLIC_IP":
                    edge_data["color"] = "#06b6d4"
                    edge_data["description"] = "Has public internet access"

                edges.append(edge_data)

        return {
            "nodes": nodes,
            "edges": edges,
            "failing_components": failing_components,
            "vm": vm,
            "port": port
        }

    except Exception as e:
        print(f"❌ TOPOLOGY ERROR: {str(e)}")
        print("🔄 Returning sample topology data for testing")
        return get_sample_topology_data(vm, port)

@app.get("/incident/global")
def global_incident(port: int = 22, vm: Optional[str] = None):
    """Generate and return enterprise incidents from infrastructure analysis"""
    from app.core.enterprise_incident_engine import EnterpriseIncidentEngine
    from app.core.enterprise_alert_engine import EnterpriseAlertEngine

    try:
        incident_engine = EnterpriseIncidentEngine()

        if vm:
            # Generate alerts from current VM RCA before incident correlation
            alert_engine = EnterpriseAlertEngine()
            alert_engine.analyze_and_generate_alerts(vm, port)

        # Analyze infrastructure and generate incidents
        incidents = incident_engine.analyze_and_correlate_incidents(port=port)

        return {
            "incidents": [incident.to_dict() for incident in incidents],
            "incident_count": len(incidents),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "analysis_type": "enterprise_correlation"
        }
    except Exception as e:
        return {"error": f"Incident analysis failed: {str(e)}", "incidents": []}

# =========================
# ENTERPRISE INCIDENT MANAGEMENT
# =========================
@app.get("/incidents")
def get_active_incidents(severity: Optional[str] = None, status: Optional[str] = None, limit: int = 50):
    """Get active incidents with filtering"""
    from app.core.enterprise_incident_engine import EnterpriseIncidentEngine
    from app.models.enterprise_alerts import IssueSeverity, IncidentStatus

    try:
        incident_engine = EnterpriseIncidentEngine()

        severity_enum = None
        if severity:
            try:
                severity_enum = IssueSeverity(severity.upper())
            except ValueError:
                return {"error": f"Invalid severity: {severity}"}

        status_enum = None
        if status:
            try:
                status_enum = IncidentStatus(status.upper())
            except ValueError:
                return {"error": f"Invalid status: {status}"}

        incidents = incident_engine.get_active_incidents(
            severity=severity_enum,
            status=status_enum,
            limit=limit
        )

        return {
            "incidents": [incident.to_dict() for incident in incidents],
            "count": len(incidents),
            "filters": {
                "severity": severity,
                "status": status,
                "limit": limit
            }
        }
    except Exception as e:
        return {"error": f"Failed to retrieve incidents: {str(e)}"}

@app.post("/incidents/{incident_id}/acknowledge")
def acknowledge_incident(incident_id: str, user: str):
    """Acknowledge an incident"""
    from app.core.enterprise_incident_engine import EnterpriseIncidentEngine

    try:
        incident_engine = EnterpriseIncidentEngine()
        success = incident_engine.acknowledge_incident(incident_id, user)

        if success:
            return {"status": "acknowledged", "incident_id": incident_id, "acknowledged_by": user}
        else:
            return {"error": "Incident not found or already acknowledged"}
    except Exception as e:
        return {"error": f"Failed to acknowledge incident: {str(e)}"}

@app.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, root_cause: str, resolution: str, user: str):
    """Resolve an incident"""
    from app.core.enterprise_incident_engine import EnterpriseIncidentEngine

    try:
        incident_engine = EnterpriseIncidentEngine()
        success = incident_engine.resolve_incident(incident_id, root_cause, resolution, user)

        if success:
            return {"status": "resolved", "incident_id": incident_id, "resolved_by": user}
        else:
            return {"error": "Incident not found"}
    except Exception as e:
        return {"error": f"Failed to resolve incident: {str(e)}"}

@app.post("/incidents/{incident_id}/close")
def close_incident(incident_id: str):
    """Close an incident"""
    from app.core.enterprise_incident_engine import EnterpriseIncidentEngine

    try:
        incident_engine = EnterpriseIncidentEngine()
        success = incident_engine.close_incident(incident_id)

        if success:
            return {"status": "closed", "incident_id": incident_id}
        else:
            return {"error": "Incident not found"}
    except Exception as e:
        return {"error": f"Failed to close incident: {str(e)}"}

@app.post("/incidents/{incident_id}/note")
def add_investigation_note(incident_id: str, note: str, user: str):
    """Add investigation note to incident"""
    from app.core.enterprise_incident_engine import EnterpriseIncidentEngine

    try:
        incident_engine = EnterpriseIncidentEngine()
        success = incident_engine.add_investigation_note(incident_id, note, user)

        if success:
            return {"status": "note_added", "incident_id": incident_id}
        else:
            return {"error": "Incident not found"}
    except Exception as e:
        return {"error": f"Failed to add note: {str(e)}"}

@app.get("/incidents/summary")
def get_incident_summary():
    """Get incident summary statistics"""
    from app.core.enterprise_incident_engine import EnterpriseIncidentEngine

    try:
        incident_engine = EnterpriseIncidentEngine()
        summary = incident_engine.get_incident_summary()
        return summary
    except Exception as e:
        return {"error": f"Failed to get incident summary: {str(e)}"}

@app.post("/approval/request")
def create_request(data: dict):
 
    action = data.get("action")
    vm = data.get("vm")
    port = data.get("port")
 
    req = approval_engine.create_request(action, vm, port)
 
    return req

@app.get("/approval/list")
def list_requests():
    return {"requests": approval_engine.list_requests()}

@app.post("/approval/approve")
def approve_request(data: dict):
 
    req_id = data.get("id")
    approver = data.get("approver", "admin")
 
    result = approval_engine.approve(
        req_id,
        approver,
        execution_engine
    )
 
    return result