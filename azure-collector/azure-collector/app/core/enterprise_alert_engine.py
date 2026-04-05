# Enterprise Alert Engine
"""
Advanced alert management with lifecycle, deduplication, and correlation.
Provides enterprise-grade alert handling with proper classification and management.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from app.models.enterprise_alerts import (
    Alert, Issue, AlertStatus, IssueClassifier,
    IssueSeverity, IssueType, IssueCategory
)
from app.neo4j_manager import neo4j_manager

logger = logging.getLogger(__name__)

class EnterpriseAlertEngine:
    """
    Enterprise alert engine with:
    - Issue classification and correlation
    - Alert lifecycle management
    - Deduplication and suppression
    - Real-time alert generation
    """

    def __init__(self):
        self.manager = neo4j_manager
        self.classifier = IssueClassifier()

    def analyze_and_generate_alerts(self, vm_name: str, port: int = 80,
                                   rca_result: Dict[str, Any] = None) -> List[Alert]:
        """
        Analyze VM and generate enterprise alerts from RCA results

        Args:
            vm_name: VM to analyze
            port: Port to check
            rca_result: Pre-computed RCA result (optional)

        Returns:
            List of generated alerts
        """
        logger.info(f"Analyzing alerts for VM: {vm_name}, port: {port}")

        alerts = []

        try:
            # Get RCA result if not provided
            if not rca_result:
                from app.rca_engine import RCAEngine
                rca_engine = RCAEngine()
                rca_result = rca_engine.analyze_path(vm_name, port)

            if not rca_result:
                logger.warning(f"No RCA result for {vm_name}")
                return alerts

            # Extract issues from RCA result
            raw_issues = rca_result.get("issues", [])
            context = {
                "vm_name": vm_name,
                "port": port,
                "root_cause": rca_result.get("root_cause", ""),
                "confidence": rca_result.get("confidence", 0)
            }

            # Extract additional context from issues
            for issue in raw_issues:
                if "NSG" in issue and "blocks" in issue:
                    context["nsg_name"] = self._extract_nsg_name(issue)
                elif "CPU" in issue:
                    context["cpu_percent"] = self._extract_cpu_percent(issue)
                elif "route" in issue.lower():
                    context["route_table"] = self._extract_route_table_name(issue)

            # Deduplicate raw issues by normalized issue intent
            normalized_seen = set()
            filtered_issues = []
            for raw_issue in raw_issues:
                normalized = raw_issue.lower().strip()
                if "blackhole route" in normalized or "internet blocked by route table" in normalized:
                    normalized = "blackhole_route"
                elif "nsg allows" in normalized or "allows port" in normalized:
                    normalized = "nsg_allow"
                elif "nsg blocks" in normalized or "traffic blocked by nsg" in normalized:
                    normalized = f"nsg_block:{port}"
                elif "vm running" in normalized:
                    normalized = "vm_running"
                elif "cpu normal" in normalized:
                    normalized = "cpu_normal"

                if normalized in normalized_seen:
                    continue
                normalized_seen.add(normalized)
                filtered_issues.append(raw_issue)

            # Classify each issue
            for raw_issue in filtered_issues:
                if not self._is_alertable_issue(raw_issue):
                    continue

                try:
                    # Classify the issue
                    issue = self.classifier.classify_issue(
                        raw_issue=raw_issue,
                        vm_name=vm_name,
                        port=port,
                        context=context
                    )

                    # Create alert
                    alert = Alert(issue=issue)

                    # Check for duplicates
                    if not self._is_duplicate_alert(alert):
                        alerts.append(alert)
                        logger.debug(f"Generated alert: {alert.alert_id} for {issue.title}")
                    else:
                        logger.debug(f"Duplicate alert suppressed: {alert.alert_signature}")

                except Exception as e:
                    logger.error(f"Error classifying issue '{raw_issue}': {e}")
                    continue

            # Store alerts in database
            self._store_alerts(alerts)

        except Exception as e:
            logger.exception(f"Error generating alerts for {vm_name}: {e}")

        return alerts

    def get_active_alerts(self, vm_name: Optional[str] = None,
                         severity: Optional[IssueSeverity] = None,
                         limit: int = 100) -> List[Alert]:
        """
        Get active alerts with optional filtering

        Args:
            vm_name: Filter by VM name
            severity: Filter by severity
            limit: Maximum number of alerts to return

        Returns:
            List of active alerts
        """
        try:
            with self.manager.get_session() as session:
                query = """
                MATCH (a:Alert)
                WHERE a.status = $status
                """

                params = {"status": AlertStatus.ACTIVE.value}

                if vm_name:
                    query += " AND a.vm_name = $vm_name"
                    params["vm_name"] = vm_name

                if severity:
                    query += " AND a.severity = $severity"
                    params["severity"] = severity.value

                query += """
                RETURN a {
                    alert_id: a.alert_id,
                    issue: a.issue,
                    status: a.status,
                    acknowledged_by: a.acknowledged_by,
                    acknowledged_at: a.acknowledged_at,
                    resolved_at: a.resolved_at,
                    resolved_by: a.resolved_by,
                    resolution_notes: a.resolution_notes,
                    alert_signature: a.alert_signature,
                    source: a.source,
                    tags: a.tags
                } as alert
                ORDER BY a.created_at DESC
                LIMIT $limit
                """

                params["limit"] = limit

                result = session.run(query, params)
                alerts = []

                for record in result:
                    alert_data = record["alert"]
                    # Reconstruct Alert object from stored data
                    alert = self._reconstruct_alert_from_data(alert_data)
                    if alert:
                        alerts.append(alert)

                return alerts

        except Exception as e:
            logger.exception(f"Error retrieving active alerts: {e}")
            return []

    def acknowledge_alert(self, alert_id: str, user: str,
                         notes: Optional[str] = None) -> bool:
        """Acknowledge an alert"""
        try:
            with self.manager.get_session() as session:
                session.run("""
                    MATCH (a:Alert {alert_id: $alert_id})
                    SET a.status = $status,
                        a.acknowledged_by = $user,
                        a.acknowledged_at = datetime(),
                        a.resolution_notes = CASE
                            WHEN a.resolution_notes IS NULL THEN $notes
                            ELSE a.resolution_notes + "\n" + $notes
                        END
                """, {
                    "alert_id": alert_id,
                    "status": AlertStatus.ACKNOWLEDGED.value,
                    "user": user,
                    "notes": notes or ""
                })

                logger.info(f"Alert {alert_id} acknowledged by {user}")
                return True

        except Exception as e:
            logger.exception(f"Error acknowledging alert {alert_id}: {e}")
            return False

    def resolve_alert(self, alert_id: str, user: str,
                     notes: Optional[str] = None) -> bool:
        """Resolve an alert"""
        try:
            with self.manager.get_session() as session:
                session.run("""
                    MATCH (a:Alert {alert_id: $alert_id})
                    SET a.status = $status,
                        a.resolved_by = $user,
                        a.resolved_at = datetime(),
                        a.resolution_notes = CASE
                            WHEN a.resolution_notes IS NULL THEN $notes
                            ELSE a.resolution_notes + "\n" + $notes
                        END
                """, {
                    "alert_id": alert_id,
                    "status": AlertStatus.RESOLVED.value,
                    "user": user,
                    "notes": notes or ""
                })

                logger.info(f"Alert {alert_id} resolved by {user}")
                return True

        except Exception as e:
            logger.exception(f"Error resolving alert {alert_id}: {e}")
            return False

    def suppress_alert(self, alert_id: str, reason: str,
                      duration_hours: int = 24) -> bool:
        """Suppress an alert temporarily"""
        try:
            suppression_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)

            with self.manager.get_session() as session:
                session.run("""
                    MATCH (a:Alert {alert_id: $alert_id})
                    SET a.status = $status,
                        a.suppression_reason = $reason,
                        a.suppression_until = datetime($until)
                """, {
                    "alert_id": alert_id,
                    "status": AlertStatus.SUPPRESSED.value,
                    "reason": reason,
                    "until": suppression_until.isoformat()
                })

                logger.info(f"Alert {alert_id} suppressed for {duration_hours} hours")
                return True

        except Exception as e:
            logger.exception(f"Error suppressing alert {alert_id}: {e}")
            return False

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics"""
        try:
            with self.manager.get_session() as session:
                result = session.run("""
                    MATCH (a:Alert)
                    RETURN
                        a.status as status,
                        a.severity as severity,
                        count(a) as count
                """)

                summary = {
                    "total": 0,
                    "by_status": {},
                    "by_severity": {},
                    "active_critical": 0,
                    "active_high": 0
                }

                for record in result:
                    status = record["status"]
                    severity = record["severity"]
                    count = record["count"]

                    summary["total"] += count

                    if status not in summary["by_status"]:
                        summary["by_status"][status] = 0
                    summary["by_status"][status] += count

                    if severity not in summary["by_severity"]:
                        summary["by_severity"][severity] = 0
                    summary["by_severity"][severity] += count

                    if status == AlertStatus.ACTIVE.value:
                        if severity == IssueSeverity.CRITICAL.value:
                            summary["active_critical"] += count
                        elif severity == IssueSeverity.HIGH.value:
                            summary["active_high"] += count

                return summary

        except Exception as e:
            logger.exception(f"Error getting alert summary: {e}")
            return {"error": str(e)}

    # Private helper methods

    def _is_alertable_issue(self, issue: str) -> bool:
        """Check if an issue should generate an alert"""
        # Skip informational/success messages
        if issue.startswith("✔"):
            return False

        # Alert on warnings, errors, and critical issues
        if issue.startswith("⚠") or issue.startswith("❌") or issue.startswith("🔥"):
            return True

        # Alert on specific critical keywords
        critical_keywords = [
            "not found", "blocked", "blackhole", "high cpu",
            "no metrics", "agent down", "stale"
        ]

        issue_lower = issue.lower()

        # Do not alert on allowance messages or normal status lines
        if "allows port" in issue_lower or "nsg allows" in issue_lower:
            return False
        if "vm running" in issue_lower or "cpu normal" in issue_lower or "route table attached" in issue_lower:
            return False

        return any(keyword in issue_lower for keyword in critical_keywords)

    def _is_duplicate_alert(self, alert: Alert) -> bool:
        """Check if alert is a duplicate"""
        try:
            with self.manager.get_session() as session:
                result = session.run("""
                    MATCH (a:Alert)
                    WHERE a.alert_signature = $signature
                    AND a.status IN [$active, $acknowledged]
                    RETURN COUNT(a) as count
                """, {
                    "signature": alert.alert_signature,
                    "active": AlertStatus.ACTIVE.value,
                    "acknowledged": AlertStatus.ACKNOWLEDGED.value
                })

                count = result.single()["count"]
                return count > 0

        except Exception as e:
            logger.error(f"Error checking for duplicate alert: {e}")
            return False

    def _store_alerts(self, alerts: List[Alert]) -> None:
        """Store alerts in Neo4j"""
        try:
            with self.manager.get_session() as session:
                for alert in alerts:
                    # Convert issue to dict for storage
                    issue_dict = alert.issue.to_dict()

                    session.run("""
                        MERGE (vm:VM {name: $vm_name})
                        CREATE (a:Alert {
                            alert_id: $alert_id,
                            issue: $issue,
                            status: $status,
                            alert_signature: $signature,
                            source: $source,
                            tags: $tags,
                            created_at: datetime(),
                            vm_name: $vm_name
                        })
                        MERGE (vm)-[:HAS_ALERT]->(a)
                    """, {
                        "alert_id": alert.alert_id,
                        "issue": issue_dict,
                        "status": alert.status.value,
                        "signature": alert.alert_signature,
                        "source": alert.source,
                        "tags": alert.tags,
                        "vm_name": alert.issue.vm_name
                    })

        except Exception as e:
            logger.exception(f"Error storing alerts: {e}")

    def _reconstruct_alert_from_data(self, data: Dict[str, Any]) -> Optional[Alert]:
        """Reconstruct Alert object from stored data"""
        try:
            # Reconstruct Issue
            issue_data = data.get("issue", {})
            issue = Issue(
                issue_id=issue_data.get("issue_id", ""),
                type=IssueType(issue_data.get("type", "UNKNOWN")),
                category=IssueCategory(issue_data.get("category", "UNKNOWN")),
                severity=IssueSeverity(issue_data.get("severity", "INFO")),
                title=issue_data.get("title", ""),
                description=issue_data.get("description", ""),
                affected_resource=issue_data.get("affected_resource"),
                affected_resource_type=issue_data.get("affected_resource_type"),
                vm_name=issue_data.get("vm_name"),
                port=issue_data.get("port"),
                details=issue_data.get("details", {}),
                evidence=issue_data.get("evidence", []),
                suggested_actions=issue_data.get("suggested_actions", [])
            )

            # Reconstruct Alert
            alert = Alert(
                alert_id=data.get("alert_id", ""),
                issue=issue,
                status=AlertStatus(data.get("status", "ACTIVE")),
                acknowledged_by=data.get("acknowledged_by"),
                resolved_by=data.get("resolved_by"),
                resolution_notes=data.get("resolution_notes"),
                alert_signature=data.get("alert_signature", ""),
                source=data.get("source", "RCA_ENGINE"),
                tags=data.get("tags", [])
            )

            # Parse timestamps
            if data.get("acknowledged_at"):
                alert.acknowledged_at = datetime.fromisoformat(data["acknowledged_at"])
            if data.get("resolved_at"):
                alert.resolved_at = datetime.fromisoformat(data["resolved_at"])

            return alert

        except Exception as e:
            logger.error(f"Error reconstructing alert from data: {e}")
            return None

    # Helper methods for extracting context from issues

    def _extract_nsg_name(self, issue: str) -> Optional[str]:
        """Extract NSG name from issue text"""
        # This would need more sophisticated parsing in production
        # For now, return None and let it be filled by RCA context
        return None

    def _extract_cpu_percent(self, issue: str) -> Optional[float]:
        """Extract CPU percentage from issue text"""
        import re
        match = re.search(r'(\d+(?:\.\d+)?)%', issue)
        return float(match.group(1)) if match else None

    def _extract_route_table_name(self, issue: str) -> Optional[str]:
        """Extract route table name from issue text"""
        # This would need more sophisticated parsing in production
        return None