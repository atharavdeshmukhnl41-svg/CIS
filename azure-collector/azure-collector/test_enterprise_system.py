#!/usr/bin/env python3
"""
Test script for enterprise alert and incident system
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from models.enterprise_alerts import (
        IssueType, IssueSeverity, IssueCategory,
        Issue, Alert, Incident, IssueClassifier
    )
    print("✅ All enterprise models imported successfully!")

    # Test issue classification
    classifier = IssueClassifier()
    issue = classifier.classify_issue("❌ NSG blocks port 80", vm_name="test-vm", port=80)
    print(f"✅ Issue classification works: {issue.title}")

    # Test alert creation
    alert = Alert(issue=issue)
    print(f"✅ Alert creation works: {alert.alert_id}")

    # Test incident creation
    incident = Incident(
        title="Test Incident",
        description="Test incident description",
        primary_issue_type=IssueType.NSG_BLOCK,
        primary_issue_category=IssueCategory.SECURITY,
        severity=IssueSeverity.HIGH
    )
    print(f"✅ Incident creation works: {incident.incident_id}")

    print("\n🎉 Enterprise Alert & Incident System is ready!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)