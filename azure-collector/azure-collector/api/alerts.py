from fastapi import APIRouter, HTTPException
from typing import Optional
from app.core.enterprise_alert_engine import EnterpriseAlertEngine
from app.models.enterprise_alerts import IssueSeverity

router = APIRouter()

alert_engine = EnterpriseAlertEngine()

# =========================
# EVALUATE VM AND GENERATE ALERTS
# =========================
@router.get("/alerts/evaluate")
def evaluate_vm_alerts(vm: str, port: int = 80):
    """Evaluate VM and return detailed alerts"""
    try:
        alerts = alert_engine.analyze_and_generate_alerts(vm, port)

        return {
            "vm": vm,
            "port": port,
            "alerts": [alert.to_dict() for alert in alerts],
            "alert_count": len(alerts),
            "generated_at": "now"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert evaluation failed: {str(e)}")

# =========================
# GET ACTIVE ALERTS
# =========================
@router.get("/alerts")
def get_active_alerts(vm: Optional[str] = None,
                     severity: Optional[str] = None,
                     limit: int = 100):
    """Get active alerts with optional filtering"""
    try:
        severity_enum = None
        if severity:
            try:
                severity_enum = IssueSeverity(severity.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

        alerts = alert_engine.get_active_alerts(
            vm_name=vm,
            severity=severity_enum,
            limit=limit
        )

        return {
            "alerts": [alert.to_dict() for alert in alerts],
            "count": len(alerts),
            "filters": {
                "vm": vm,
                "severity": severity,
                "limit": limit
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")

# =========================
# ACKNOWLEDGE ALERT
# =========================
@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, user: str, notes: Optional[str] = None):
    """Acknowledge an alert"""
    try:
        success = alert_engine.acknowledge_alert(alert_id, user, notes)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")

        return {"status": "acknowledged", "alert_id": alert_id, "acknowledged_by": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")

# =========================
# RESOLVE ALERT
# =========================
@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, user: str, notes: Optional[str] = None):
    """Resolve an alert"""
    try:
        success = alert_engine.resolve_alert(alert_id, user, notes)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {"status": "resolved", "alert_id": alert_id, "resolved_by": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")

# =========================
# SUPPRESS ALERT
# =========================
@router.post("/alerts/{alert_id}/suppress")
def suppress_alert(alert_id: str, reason: str, duration_hours: int = 24):
    """Suppress an alert temporarily"""
    try:
        success = alert_engine.suppress_alert(alert_id, reason, duration_hours)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {
            "status": "suppressed",
            "alert_id": alert_id,
            "reason": reason,
            "duration_hours": duration_hours
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suppress alert: {str(e)}")

# =========================
# ALERT SUMMARY
# =========================
@router.get("/alerts/summary")
def get_alert_summary():
    """Get alert summary statistics"""
    try:
        summary = alert_engine.get_alert_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert summary: {str(e)}")

# =========================
# LEGACY ENDPOINT (for backward compatibility)
# =========================
@router.get("/alerts/check")
def check_alert(vm: str):
    """Legacy endpoint - redirects to new evaluate endpoint"""
    return evaluate_vm_alerts(vm)