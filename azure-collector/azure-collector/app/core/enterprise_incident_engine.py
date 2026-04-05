# Enterprise Incident Engine
"""
Advanced incident management with correlation, impact analysis, and lifecycle management.
Correlates alerts into incidents and provides enterprise-grade incident response.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Set
from collections import defaultdict
from app.models.enterprise_alerts import (
    Incident, Alert, Issue, IncidentStatus, IssueSeverity,
    IssueType, IssueCategory
)
from app.core.enterprise_alert_engine import EnterpriseAlertEngine
from app.neo4j_manager import neo4j_manager

logger = logging.getLogger(__name__)

class EnterpriseIncidentEngine:
    """
    Enterprise incident engine with:
    - Alert correlation and incident creation
    - Impact analysis and priority calculation
    - Incident lifecycle management
    - Root cause analysis and resolution tracking
    """

    def __init__(self):
        self.manager = neo4j_manager
        self.alert_engine = EnterpriseAlertEngine()

    def analyze_and_correlate_incidents(self, vms: List[str] = None,
                                       port: int = 80) -> List[Incident]:
        """
        Analyze infrastructure and correlate alerts into incidents

        Args:
            vms: List of VMs to analyze (if None, analyzes all)
            port: Port to check

        Returns:
            List of correlated incidents
        """
        logger.info("Starting incident analysis and correlation")

        incidents = []

        try:
            # Get all active alerts
            active_alerts = self.alert_engine.get_active_alerts()

            if not active_alerts:
                logger.info("No active alerts found")
                return incidents

            # Group alerts by correlation criteria
            alert_groups = self._correlate_alerts(active_alerts)

            # Create incidents from alert groups
            for group_key, alerts in alert_groups.items():
                if len(alerts) > 0:  # Only create incidents for groups with alerts
                    incident = self._create_incident_from_alerts(alerts, group_key)
                    if incident:
                        incidents.append(incident)

            # Store incidents
            self._store_incidents(incidents)

            logger.info(f"Created {len(incidents)} incidents from {len(active_alerts)} alerts")

        except Exception as e:
            logger.exception(f"Error in incident analysis: {e}")

        return incidents

    def get_active_incidents(self, severity: Optional[IssueSeverity] = None,
                           status: Optional[IncidentStatus] = None,
                           limit: int = 50) -> List[Incident]:
        """
        Get active incidents with optional filtering

        Args:
            severity: Filter by severity
            status: Filter by status
            limit: Maximum incidents to return

        Returns:
            List of active incidents
        """
        try:
            with self.manager.get_session() as session:
                query = """
                MATCH (i:Incident)
                WHERE i.status IN [$open, $investigating]
                """

                params = {
                    "open": IncidentStatus.OPEN.value,
                    "investigating": IncidentStatus.INVESTIGATING.value
                }

                if severity:
                    query += " AND i.severity = $severity"
                    params["severity"] = severity.value

                if status:
                    query += " AND i.status = $status"
                    params["status"] = status.value

                query += """
                RETURN i {
                    incident_id: i.incident_id,
                    title: i.title,
                    description: i.description,
                    primary_issue_type: i.primary_issue_type,
                    primary_issue_category: i.primary_issue_category,
                    severity: i.severity,
                    priority: i.priority,
                    status: i.status,
                    affected_vms: i.affected_vms,
                    affected_services: i.affected_services,
                    business_impact: i.business_impact,
                    estimated_user_impact: i.estimated_user_impact,
                    related_alerts: i.related_alerts,
                    related_issues: i.related_issues,
                    root_cause_analysis: i.root_cause_analysis,
                    investigation_notes: i.investigation_notes,
                    resolution_steps: i.resolution_steps,
                    preventive_measures: i.preventive_measures,
                    created_at: i.created_at,
                    detected_at: i.detected_at,
                    acknowledged_at: i.acknowledged_at,
                    resolved_at: i.resolved_at,
                    closed_at: i.closed_at,
                    assigned_to: i.assigned_to,
                    assigned_by: i.assigned_by,
                    assigned_at: i.assigned_at,
                    customer_communication: i.customer_communication,
                    stakeholder_updates: i.stakeholder_updates,
                    tags: i.tags,
                    source: i.source,
                    confidence_score: i.confidence_score
                } as incident
                ORDER BY i.created_at DESC
                LIMIT $limit
                """

                params["limit"] = limit

                result = session.run(query, params)
                incidents = []

                for record in result:
                    incident_data = record["incident"]
                    incident = self._reconstruct_incident_from_data(incident_data)
                    if incident:
                        incidents.append(incident)

                return incidents

        except Exception as e:
            logger.exception(f"Error retrieving active incidents: {e}")
            return []

    def acknowledge_incident(self, incident_id: str, user: str) -> bool:
        """Acknowledge an incident"""
        try:
            with self.manager.get_session() as session:
                session.run("""
                    MATCH (i:Incident {incident_id: $incident_id})
                    SET i.status = $status,
                        i.acknowledged_at = datetime(),
                        i.assigned_to = $user
                """, {
                    "incident_id": incident_id,
                    "status": IncidentStatus.INVESTIGATING.value,
                    "user": user
                })

                logger.info(f"Incident {incident_id} acknowledged by {user}")
                return True

        except Exception as e:
            logger.exception(f"Error acknowledging incident {incident_id}: {e}")
            return False

    def resolve_incident(self, incident_id: str, root_cause: str,
                        resolution: str, user: str) -> bool:
        """Resolve an incident"""
        try:
            with self.manager.get_session() as session:
                session.run("""
                    MATCH (i:Incident {incident_id: $incident_id})
                    SET i.status = $status,
                        i.resolved_at = datetime(),
                        i.root_cause_analysis = $root_cause,
                        i.resolution_steps = $resolution_steps
                """, {
                    "incident_id": incident_id,
                    "status": IncidentStatus.RESOLVED.value,
                    "root_cause": root_cause,
                    "resolution_steps": resolution.split('\n') if '\n' in resolution else [resolution]
                })

                logger.info(f"Incident {incident_id} resolved by {user}")
                return True

        except Exception as e:
            logger.exception(f"Error resolving incident {incident_id}: {e}")
            return False

    def close_incident(self, incident_id: str) -> bool:
        """Close an incident"""
        try:
            with self.manager.get_session() as session:
                session.run("""
                    MATCH (i:Incident {incident_id: $incident_id})
                    SET i.status = $status,
                        i.closed_at = datetime()
                """, {
                    "incident_id": incident_id,
                    "status": IncidentStatus.CLOSED.value
                })

                logger.info(f"Incident {incident_id} closed")
                return True

        except Exception as e:
            logger.exception(f"Error closing incident {incident_id}: {e}")
            return False

    def add_investigation_note(self, incident_id: str, note: str, user: str) -> bool:
        """Add investigation note to incident"""
        try:
            with self.manager.get_session() as session:
                # First get current notes
                result = session.run("""
                    MATCH (i:Incident {incident_id: $incident_id})
                    RETURN i.investigation_notes as notes
                """, {"incident_id": incident_id})

                record = result.single()
                current_notes = record["notes"] if record else []

                # Add new note
                timestamp = datetime.now(timezone.utc).isoformat()
                new_note = f"[{timestamp}] {user}: {note}"
                updated_notes = current_notes + [new_note]

                # Update incident
                session.run("""
                    MATCH (i:Incident {incident_id: $incident_id})
                    SET i.investigation_notes = $notes
                """, {
                    "incident_id": incident_id,
                    "notes": updated_notes
                })

                logger.info(f"Added investigation note to incident {incident_id}")
                return True

        except Exception as e:
            logger.exception(f"Error adding investigation note: {e}")
            return False

    def get_incident_summary(self) -> Dict[str, Any]:
        """Get incident summary statistics"""
        try:
            with self.manager.get_session() as session:
                result = session.run("""
                    MATCH (i:Incident)
                    RETURN
                        i.status as status,
                        i.severity as severity,
                        i.priority as priority,
                        count(i) as count
                """)

                summary = {
                    "total": 0,
                    "by_status": {},
                    "by_severity": {},
                    "by_priority": {},
                    "active_critical": 0,
                    "active_high": 0,
                    "open_count": 0
                }

                for record in result:
                    status = record["status"]
                    severity = record["severity"]
                    priority = record["priority"]
                    count = record["count"]

                    summary["total"] += count

                    if status not in summary["by_status"]:
                        summary["by_status"][status] = 0
                    summary["by_status"][status] += count

                    if severity not in summary["by_severity"]:
                        summary["by_severity"][severity] = 0
                    summary["by_severity"][severity] += count

                    if priority not in summary["by_priority"]:
                        summary["by_priority"][priority] = 0
                    summary["by_priority"][priority] += count

                    if status in [IncidentStatus.OPEN.value, IncidentStatus.INVESTIGATING.value]:
                        summary["open_count"] += count
                        if severity == IssueSeverity.CRITICAL.value:
                            summary["active_critical"] += count
                        elif severity == IssueSeverity.HIGH.value:
                            summary["active_high"] += count

                return summary

        except Exception as e:
            logger.exception(f"Error getting incident summary: {e}")
            return {"error": str(e)}

    # Private helper methods

    def _correlate_alerts(self, alerts: List[Alert]) -> Dict[str, List[Alert]]:
        """
        Correlate alerts into groups based on various criteria

        Returns:
            Dict with correlation keys and grouped alerts
        """
        groups = defaultdict(list)

        for alert in alerts:
            # Primary correlation: by issue type and affected resource
            correlation_key = f"{alert.issue.type.value}:{alert.issue.affected_resource or 'none'}"

            # Secondary correlation: group related issues
            if alert.issue.type in [IssueType.NSG_BLOCK, IssueType.BLACKHOLE_ROUTE,
                                   IssueType.LB_MISCONFIG, IssueType.NO_PUBLIC_IP]:
                # Network connectivity issues
                correlation_key = f"NETWORK_CONNECTIVITY:{alert.issue.vm_name}"
            elif alert.issue.type in [IssueType.HIGH_CPU, IssueType.HIGH_MEMORY]:
                # Performance issues
                correlation_key = f"PERFORMANCE:{alert.issue.vm_name}"
            elif alert.issue.type in [IssueType.NO_METRICS, IssueType.STALE_METRICS,
                                     IssueType.AGENT_DOWN]:
                # Monitoring issues
                correlation_key = f"MONITORING:{alert.issue.vm_name}"

            groups[correlation_key].append(alert)

        return dict(groups)

    def _create_incident_from_alerts(self, alerts: List[Alert], group_key: str) -> Optional[Incident]:
        """Create an incident from a group of correlated alerts"""
        if not alerts:
            return None

        try:
            # Determine primary issue (highest severity)
            primary_alert = max(alerts, key=lambda a: self._severity_score(a.issue.severity))

            # Collect all affected VMs
            affected_vms = list(set(alert.issue.vm_name for alert in alerts if alert.issue.vm_name))

            # Create incident
            incident = Incident(
                title=self._generate_incident_title(primary_alert, len(alerts)),
                description=self._generate_incident_description(alerts),
                primary_issue_type=primary_alert.issue.type,
                primary_issue_category=primary_alert.issue.category,
                severity=primary_alert.issue.severity,
                affected_vms=affected_vms,
                related_alerts=[alert.alert_id for alert in alerts],
                related_issues=[alert.issue for alert in alerts],
                tags=[group_key.split(':')[0]],  # Add correlation tag
                confidence_score=min(1.0, len(alerts) * 0.1 + 0.5)  # Higher confidence with more alerts
            )

            # Calculate priority and impact
            incident.calculate_priority()
            incident.estimated_user_impact = len(affected_vms) * 10  # Rough estimate

            # Set business impact based on severity
            if incident.severity == IssueSeverity.CRITICAL:
                incident.business_impact = "Critical infrastructure outage affecting multiple systems"
            elif incident.severity == IssueSeverity.HIGH:
                incident.business_impact = "Significant service degradation"
            else:
                incident.business_impact = "Minor service impact"

            return incident

        except Exception as e:
            logger.exception(f"Error creating incident from alerts: {e}")
            return None

    def _generate_incident_title(self, primary_alert: Alert, alert_count: int) -> str:
        """Generate incident title"""
        base_title = primary_alert.issue.title

        if alert_count > 1:
            return f"{base_title} (affecting {alert_count} components)"
        else:
            return base_title

    def _generate_incident_description(self, alerts: List[Alert]) -> str:
        """Generate incident description from alerts"""
        descriptions = []

        for alert in alerts:
            desc = f"- {alert.issue.title}: {alert.issue.description}"
            descriptions.append(desc)

        return "Multiple related issues detected:\n" + "\n".join(descriptions)

    def _severity_score(self, severity: IssueSeverity) -> int:
        """Convert severity to numeric score for comparison"""
        scores = {
            IssueSeverity.CRITICAL: 4,
            IssueSeverity.HIGH: 3,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 1,
            IssueSeverity.INFO: 0
        }
        return scores.get(severity, 0)

    def _store_incidents(self, incidents: List[Incident]) -> None:
        """Store incidents in Neo4j"""
        try:
            with self.manager.get_session() as session:
                for incident in incidents:
                    # Convert related issues to dicts
                    related_issues = [issue.to_dict() for issue in incident.related_issues]

                    session.run("""
                        CREATE (i:Incident {
                            incident_id: $incident_id,
                            title: $title,
                            description: $description,
                            primary_issue_type: $primary_issue_type,
                            primary_issue_category: $primary_issue_category,
                            severity: $severity,
                            priority: $priority,
                            status: $status,
                            affected_vms: $affected_vms,
                            affected_services: $affected_services,
                            business_impact: $business_impact,
                            estimated_user_impact: $estimated_user_impact,
                            related_alerts: $related_alerts,
                            related_issues: $related_issues,
                            investigation_notes: $investigation_notes,
                            resolution_steps: $resolution_steps,
                            preventive_measures: $preventive_measures,
                            customer_communication: $customer_communication,
                            stakeholder_updates: $stakeholder_updates,
                            tags: $tags,
                            source: $source,
                            confidence_score: $confidence_score,
                            created_at: datetime()
                        })
                    """, {
                        "incident_id": incident.incident_id,
                        "title": incident.title,
                        "description": incident.description,
                        "primary_issue_type": incident.primary_issue_type.value,
                        "primary_issue_category": incident.primary_issue_category.value,
                        "severity": incident.severity.value,
                        "priority": incident.priority,
                        "status": incident.status.value,
                        "affected_vms": incident.affected_vms,
                        "affected_services": incident.affected_services,
                        "business_impact": incident.business_impact,
                        "estimated_user_impact": incident.estimated_user_impact,
                        "related_alerts": incident.related_alerts,
                        "related_issues": related_issues,
                        "investigation_notes": incident.investigation_notes,
                        "resolution_steps": incident.resolution_steps,
                        "preventive_measures": incident.preventive_measures,
                        "customer_communication": incident.customer_communication,
                        "stakeholder_updates": incident.stakeholder_updates,
                        "tags": incident.tags,
                        "source": incident.source,
                        "confidence_score": incident.confidence_score
                    })

                    # Create relationships to related alerts
                    for alert_id in incident.related_alerts:
                        session.run("""
                            MATCH (i:Incident {incident_id: $incident_id})
                            MATCH (a:Alert {alert_id: $alert_id})
                            MERGE (i)-[:RELATED_TO]->(a)
                        """, {
                            "incident_id": incident.incident_id,
                            "alert_id": alert_id
                        })

        except Exception as e:
            logger.exception(f"Error storing incidents: {e}")

    def _reconstruct_incident_from_data(self, data: Dict[str, Any]) -> Optional[Incident]:
        """Reconstruct Incident object from stored data"""
        try:
            # Reconstruct related issues
            related_issues = []
            for issue_data in data.get("related_issues", []):
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
                related_issues.append(issue)

            # Create incident
            incident = Incident(
                incident_id=data.get("incident_id", ""),
                title=data.get("title", ""),
                description=data.get("description", ""),
                primary_issue_type=IssueType(data.get("primary_issue_type", "UNKNOWN")),
                primary_issue_category=IssueCategory(data.get("primary_issue_category", "UNKNOWN")),
                severity=IssueSeverity(data.get("severity", "INFO")),
                priority=data.get("priority", "P4"),
                status=IncidentStatus(data.get("status", "OPEN")),
                affected_vms=data.get("affected_vms", []),
                affected_services=data.get("affected_services", []),
                business_impact=data.get("business_impact", ""),
                estimated_user_impact=data.get("estimated_user_impact", 0),
                related_alerts=data.get("related_alerts", []),
                related_issues=related_issues,
                root_cause_analysis=data.get("root_cause_analysis", ""),
                investigation_notes=data.get("investigation_notes", []),
                resolution_steps=data.get("resolution_steps", []),
                preventive_measures=data.get("preventive_measures", []),
                customer_communication=data.get("customer_communication", []),
                stakeholder_updates=data.get("stakeholder_updates", []),
                tags=data.get("tags", []),
                source=data.get("source", "AUTOMATED"),
                confidence_score=data.get("confidence_score", 0.0)
            )

            # Parse timestamps
            for timestamp_field in ["created_at", "detected_at", "acknowledged_at",
                                  "resolved_at", "closed_at", "assigned_at"]:
                if data.get(timestamp_field):
                    setattr(incident, timestamp_field,
                           datetime.fromisoformat(data[timestamp_field]))

            return incident

        except Exception as e:
            logger.error(f"Error reconstructing incident from data: {e}")
            return None