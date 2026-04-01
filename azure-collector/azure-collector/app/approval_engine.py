import uuid
from datetime import datetime
 
class ApprovalEngine:
 
    def __init__(self):
        self.requests = {}  # in-memory (later DB)
 
    # -------------------------
    # CREATE REQUEST
    # -------------------------
    def create_request(self, action, vm, port):
 
        req_id = str(uuid.uuid4())
 
        self.requests[req_id] = {
            "id": req_id,
            "action": action,
            "vm": vm,
            "port": port,
            "status": "PENDING",
            "created_at": datetime.utcnow().isoformat(),
            "approved_by": None
        }
 
        return self.requests[req_id]
 
    # -------------------------
    # GET ALL REQUESTS
    # -------------------------
    def list_requests(self):
        return list(self.requests.values())
 
    # -------------------------
    # APPROVE REQUEST
    # -------------------------
    def approve(self, req_id, approver, execution_engine):
 
        if req_id not in self.requests:
            return {"error": "Request not found"}
 
        req = self.requests[req_id]
 
        if req["status"] != "PENDING":
            return {"error": "Already processed"}
 
        # Execute action
        result = execution_engine.execute(
            req["action"],
            req["vm"],
            req["port"]
        )
 
        req["status"] = "APPROVED"
        req["approved_by"] = approver
        req["executed_at"] = datetime.utcnow().isoformat()
        req["result"] = result
 
        return req