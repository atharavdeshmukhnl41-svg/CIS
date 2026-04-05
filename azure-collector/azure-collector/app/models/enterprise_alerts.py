# Enterprise Alert & Incident Management System
"""
Unified system for alerts, incidents, and issue classification.
Provides enterprise-grade incident management with proper lifecycle,
correlation, and severity calculation.
"""

from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import hashlib
import logging

logger = logging.getLogger(__name__)

class IssueSeverity(Enum):
    """Enterprise severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class IssueCategory(Enum):
    """Issue classification categories"""
    NETWORK = "NETWORK"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    AVAILABILITY = "AVAILABILITY"
    CONFIGURATION = "CONFIGURATION"
    MONITORING = "MONITORING"

class IssueType(Enum):
    """Specific issue types"""
    VM_NOT_FOUND = "VM_NOT_FOUND"
    NSG_BLOCK = "NSG_BLOCK"
    BLACKHOLE_ROUTE = "BLACKHOLE_ROUTE"
    LB_MISCONFIG = "LB_MISCONFIG"
    NO_PUBLIC_IP = "NO_PUBLIC_IP"
    HIGH_CPU = "HIGH_CPU"
    HIGH_MEMORY = "HIGH_MEMORY"
    NO_METRICS = "NO_METRICS"
    STALE_METRICS = "STALE_METRICS"
    AGENT_DOWN = "AGENT_DOWN"
    NETWORK_LATENCY = "NETWORK_LATENCY"
    DISK_FULL = "DISK_FULL"
    UNKNOWN = "UNKNOWN"

class AlertStatus(Enum):
    """Alert lifecycle states"""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"

class IncidentStatus(Enum):
    """Incident lifecycle states"""
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

@dataclass
class Issue:
    """Detailed issue with enterprise classification"""
    type: IssueType
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    issue_id: str = field(default_factory=lambda: f"ISS-{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}")
    affected_resource: Optional[str] = None
    affected_resource_type: Optional[str] = None
    vm_name: Optional[str] = None
    port: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "issue_id": self.issue_id,
            "type": self.type.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "affected_resource": self.affected_resource,
            "affected_resource_type": self.affected_resource_type,
            "vm_name": self.vm_name,
            "port": self.port,
            "details": self.details,
            "evidence": self.evidence,
            "suggested_actions": self.suggested_actions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

@dataclass
class Alert:
    """Enterprise alert with lifecycle management"""
    issue: Issue
    alert_id: str = field(default_factory=lambda: f"ALT-{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}")
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    suppression_reason: Optional[str] = None
    suppression_until: Optional[datetime] = None
    alert_signature: str = ""  # For deduplication
    source: str = "RCA_ENGINE"  # RCA_ENGINE, MONITORING, MANUAL
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Generate alert signature for deduplication"""
        sig_components = [
            self.issue.vm_name or "unknown",
            self.issue.type.value,
            self.issue.affected_resource or "none",
            str(self.issue.port) if self.issue.port else "any"
        ]
        self.alert_signature = hashlib.sha256("|".join(sig_components).encode()).hexdigest()[:16]

    def acknowledge(self, user: str, notes: Optional[str] = None):
        """Acknowledge the alert"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_by = user
        self.acknowledged_at = datetime.now(timezone.utc)
        if notes:
            self.resolution_notes = notes

    def resolve(self, user: str, notes: Optional[str] = None):
        """Resolve the alert"""
        self.status = AlertStatus.RESOLVED
        self.resolved_by = user
        self.resolved_at = datetime.now(timezone.utc)
        if notes:
            self.resolution_notes = notes

    def suppress(self, reason: str, duration_hours: int = 24):
        """Suppress the alert temporarily"""
        self.status = AlertStatus.SUPPRESSED
        self.suppression_reason = reason
        self.suppression_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)

    def is_suppressed(self) -> bool:
        """Check if alert is currently suppressed"""
        if self.status != AlertStatus.SUPPRESSED:
            return False
        return self.suppression_until and datetime.now(timezone.utc) < self.suppression_until

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "alert_id": self.alert_id,
            "issue": self.issue.to_dict(),
            "status": self.status.value,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
            "suppression_reason": self.suppression_reason,
            "suppression_until": self.suppression_until.isoformat() if self.suppression_until else None,
            "alert_signature": self.alert_signature,
            "source": self.source,
            "tags": self.tags
        }

@dataclass
class Incident:
    """Enterprise incident with correlation and impact analysis"""
    title: str
    description: str
    primary_issue_type: IssueType
    primary_issue_category: IssueCategory
    severity: IssueSeverity
    incident_id: str = field(default_factory=lambda: f"INC-{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}")
    priority: str = "P4"  # P0, P1, P2, P3, P4
    status: IncidentStatus = IncidentStatus.OPEN

    # Impact analysis
    affected_vms: List[str] = field(default_factory=list)
    affected_services: List[str] = field(default_factory=list)
    business_impact: str = "Unknown"
    estimated_user_impact: int = 0  # Number of users affected

    # Related alerts and issues
    related_alerts: List[str] = field(default_factory=list)  # Alert IDs
    related_issues: List[Issue] = field(default_factory=list)

    # Investigation and resolution
    root_cause_analysis: str = ""
    investigation_notes: List[str] = field(default_factory=list)
    resolution_steps: List[str] = field(default_factory=list)
    preventive_measures: List[str] = field(default_factory=list)

    # Timeline
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detected_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    # Assignment
    assigned_to: Optional[str] = None
    assigned_by: Optional[str] = None
    assigned_at: Optional[datetime] = None

    # Communication
    customer_communication: List[str] = field(default_factory=list)
    stakeholder_updates: List[str] = field(default_factory=list)

    # Metadata
    tags: List[str] = field(default_factory=list)
    source: str = "AUTOMATED"  # AUTOMATED, MANUAL, MONITORING
    confidence_score: float = 0.0  # 0.0 to 1.0

    def calculate_priority(self):
        """Calculate priority based on severity and impact"""
        severity_score = {
            IssueSeverity.CRITICAL: 4,
            IssueSeverity.HIGH: 3,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 1,
            IssueSeverity.INFO: 0
        }

        impact_score = min(len(self.affected_vms) * 0.1, 1.0) + min(self.estimated_user_impact * 0.001, 1.0)

        total_score = severity_score.get(self.severity, 0) + impact_score

        if total_score >= 4.5:
            self.priority = "P0"
        elif total_score >= 3.5:
            self.priority = "P1"
        elif total_score >= 2.5:
            self.priority = "P2"
        elif total_score >= 1.5:
            self.priority = "P3"
        else:
            self.priority = "P4"

    def acknowledge(self, user: str):
        """Acknowledge the incident"""
        self.status = IncidentStatus.INVESTIGATING
        self.acknowledged_at = datetime.now(timezone.utc)
        self.assigned_to = user

    def resolve(self, root_cause: str, resolution: str):
        """Resolve the incident"""
        self.status = IncidentStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
        self.root_cause_analysis = root_cause
        self.resolution_steps = resolution.split('\n') if '\n' in resolution else [resolution]

    def close(self):
        """Close the incident"""
        self.status = IncidentStatus.CLOSED
        self.closed_at = datetime.now(timezone.utc)

    def add_investigation_note(self, note: str, user: str):
        """Add investigation note"""
        timestamp = datetime.now(timezone.utc).isoformat()
        self.investigation_notes.append(f"[{timestamp}] {user}: {note}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "primary_issue_type": self.primary_issue_type.value,
            "primary_issue_category": self.primary_issue_category.value,
            "severity": self.severity.value,
            "priority": self.priority,
            "status": self.status.value,
            "affected_vms": self.affected_vms,
            "affected_services": self.affected_services,
            "business_impact": self.business_impact,
            "estimated_user_impact": self.estimated_user_impact,
            "related_alerts": self.related_alerts,
            "related_issues": [issue.to_dict() for issue in self.related_issues],
            "root_cause_analysis": self.root_cause_analysis,
            "investigation_notes": self.investigation_notes,
            "resolution_steps": self.resolution_steps,
            "preventive_measures": self.preventive_measures,
            "created_at": self.created_at.isoformat(),
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "assigned_to": self.assigned_to,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "customer_communication": self.customer_communication,
            "stakeholder_updates": self.stakeholder_updates,
            "tags": self.tags,
            "source": self.source,
            "confidence_score": self.confidence_score
        }

class IssueClassifier:
    """Classifies raw issues into structured enterprise issues"""

    @staticmethod
    def classify_issue(raw_issue: str, vm_name: str = None, port: int = None,
                      context: Dict[str, Any] = None) -> Issue:
        """
        Classify a raw issue string into structured Issue object

        Args:
            raw_issue: Raw issue string (e.g., "❌ NSG blocks port 80")
            vm_name: VM name if available
            port: Port if available
            context: Additional context from RCA

        Returns:
            Classified Issue object
        """
        context = context or {}

        # Clean the issue text
        clean_issue = raw_issue.replace("❌", "").replace("⚠", "").replace("🔥", "").replace("✔", "").strip()

        # Classification logic
        if "VM not found" in clean_issue:
            return Issue(
                type=IssueType.VM_NOT_FOUND,
                category=IssueCategory.AVAILABILITY,
                severity=IssueSeverity.CRITICAL,
                title="VM Not Found",
                description=f"Virtual Machine '{vm_name}' was not found in the infrastructure",
                vm_name=vm_name,
                affected_resource=vm_name,
                affected_resource_type="VM",
                suggested_actions=[
                    "Verify VM name spelling",
                    "Check if VM exists in Azure portal",
                    "Verify Azure subscription and resource group access"
                ]
            )

        elif "NSG blocks port" in clean_issue or "Traffic blocked by NSG" in clean_issue:
            port_num = port or 80
            return Issue(
                type=IssueType.NSG_BLOCK,
                category=IssueCategory.SECURITY,
                severity=IssueSeverity.HIGH,
                title=f"Port {port_num} Blocked by NSG",
                description=f"Network Security Group is blocking traffic on port {port_num}",
                vm_name=vm_name,
                port=port_num,
                affected_resource=context.get("nsg_name", "Unknown NSG"),
                affected_resource_type="NSG",
                details={"port": port_num, "nsg_name": context.get("nsg_name")},
                suggested_actions=[
                    f"Add inbound security rule to allow port {port_num}",
                    "Set appropriate priority for the rule",
                    "Verify rule direction (Inbound/Outbound)",
                    "Check source/destination IP ranges"
                ]
            )

        elif "Blackhole route" in clean_issue or "Internet blocked by route table" in clean_issue:
            return Issue(
                type=IssueType.BLACKHOLE_ROUTE,
                category=IssueCategory.NETWORK,
                severity=IssueSeverity.CRITICAL,
                title="Blackhole Route Blocking Internet Access",
                description="Route table contains a blackhole route (0.0.0.0/0 -> None) blocking all internet traffic",
                vm_name=vm_name,
                affected_resource=context.get("route_table", "Unknown Route Table"),
                affected_resource_type="RouteTable",
                details={"route_table": context.get("route_table"), "prefix": "0.0.0.0/0", "next_hop": "None"},
                suggested_actions=[
                    "Edit the 0.0.0.0/0 route in the route table",
                    "Change Next Hop Type from 'None' to 'Internet'",
                    "Verify internet connectivity after change",
                    "Consider using Virtual Network Gateway for controlled internet access"
                ]
            )

        elif "backend pool" in clean_issue or "LB misconfiguration" in clean_issue:
            return Issue(
                type=IssueType.LB_MISCONFIG,
                category=IssueCategory.CONFIGURATION,
                severity=IssueSeverity.HIGH,
                title="Load Balancer Backend Pool Misconfiguration",
                description="VM is not properly configured in Load Balancer backend pool",
                vm_name=vm_name,
                affected_resource=context.get("lb_name", "Unknown Load Balancer"),
                affected_resource_type="LoadBalancer",
                details={"lb_name": context.get("lb_name")},
                suggested_actions=[
                    "Navigate to Load Balancer → Backend pools",
                    "Select the appropriate backend pool",
                    "Add VM NIC to the backend pool",
                    "Verify health probe configuration",
                    "Test load balancer functionality"
                ]
            )

        elif "No Public IP" in clean_issue:
            return Issue(
                type=IssueType.NO_PUBLIC_IP,
                category=IssueCategory.NETWORK,
                severity=IssueSeverity.HIGH,
                title="Missing Public IP Configuration",
                description="VM has no public IP address assigned for external access",
                vm_name=vm_name,
                affected_resource=vm_name,
                affected_resource_type="VM",
                suggested_actions=[
                    "Associate a public IP address with the VM NIC",
                    "Configure Load Balancer for public access",
                    "Use NAT Gateway for outbound internet access",
                    "Verify network routing configuration"
                ]
            )

        elif "High CPU usage" in clean_issue:
            cpu_percent = context.get("cpu_percent", 0)
            return Issue(
                type=IssueType.HIGH_CPU,
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.MEDIUM,
                title=f"High CPU Usage ({cpu_percent}%)",
                description=f"VM is experiencing high CPU utilization at {cpu_percent}%",
                vm_name=vm_name,
                affected_resource=vm_name,
                affected_resource_type="VM",
                details={"cpu_percent": cpu_percent},
                suggested_actions=[
                    "Monitor top CPU-consuming processes",
                    "Scale VM to higher SKU if needed",
                    "Optimize application performance",
                    "Check for memory pressure affecting CPU",
                    "Review recent deployments or configuration changes"
                ]
            )

        elif "No metrics available" in clean_issue or "agent issue" in clean_issue.lower():
            return Issue(
                type=IssueType.NO_METRICS,
                category=IssueCategory.MONITORING,
                severity=IssueSeverity.HIGH,
                title="Monitoring Agent Not Reporting",
                description="CIP monitoring agent is not sending metrics data",
                vm_name=vm_name,
                affected_resource=vm_name,
                affected_resource_type="VM",
                suggested_actions=[
                    "Check CIP agent service status",
                    "Restart cip.service if stopped",
                    "Verify agent configuration and API connectivity",
                    "Check agent logs for error messages",
                    "Validate network connectivity to metrics endpoint"
                ]
            )

        elif "Metrics stale" in clean_issue:
            age_seconds = context.get("age_seconds", 0)
            return Issue(
                type=IssueType.STALE_METRICS,
                category=IssueCategory.MONITORING,
                severity=IssueSeverity.MEDIUM,
                title=f"Stale Metrics Data ({age_seconds}s old)",
                description=f"Monitoring metrics are outdated ({age_seconds} seconds old)",
                vm_name=vm_name,
                affected_resource=vm_name,
                affected_resource_type="VM",
                details={"age_seconds": age_seconds},
                suggested_actions=[
                    "Check CIP agent service status",
                    "Restart monitoring agent",
                    "Verify agent-to-API connectivity",
                    "Check for network latency issues",
                    "Validate agent configuration"
                ]
            )

        else:
            # Unknown issue
            return Issue(
                type=IssueType.UNKNOWN,
                category=IssueCategory.UNKNOWN,
                severity=IssueSeverity.INFO,
                title="Unknown Issue Detected",
                description=clean_issue,
                vm_name=vm_name,
                details={"raw_issue": raw_issue}
            )