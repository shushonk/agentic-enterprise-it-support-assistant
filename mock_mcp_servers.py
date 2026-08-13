import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

# Counter states for unique ticket/incident ID generation
_jira_counter = 1
_snow_counter = 1


class JiraMCPServer:
    """Mock Jira MCP Server for IT ticket management."""

    @staticmethod
    def create_ticket(
        summary: str,
        description: str = "",
        project: str = "IT",
        priority: str = "Medium",
        reporter: str = "employee@abctechnologies.com"
    ) -> Dict[str, Any]:
        global _jira_counter
        ticket_id = f"MOCK-JIRA-{_jira_counter:03d}"
        _jira_counter += 1
        
        logger.info(f"[MCP JIRA] Creating ticket {ticket_id}: {summary}")
        return {
            "mock": True,
            "system": "Jira",
            "status": "created",
            "ticket_id": ticket_id,
            "summary": summary,
            "description": description,
            "project": project,
            "priority": priority,
            "reporter": reporter,
            "message": f"Mock Jira ticket {ticket_id} created successfully."
        }

    @staticmethod
    def get_ticket(ticket_id: str) -> Dict[str, Any]:
        logger.info(f"[MCP JIRA] Retrieving ticket {ticket_id}")
        return {
            "mock": True,
            "system": "Jira",
            "status": "found",
            "ticket_id": ticket_id,
            "summary": "Mock issue summary",
            "priority": "Medium",
            "assignee": "helpdesk-agent@abctechnologies.com"
        }

    @staticmethod
    def update_ticket(ticket_id: str, status: str = "In Progress") -> Dict[str, Any]:
        logger.info(f"[MCP JIRA] Updating ticket {ticket_id} to status {status}")
        return {
            "mock": True,
            "system": "Jira",
            "status": "updated",
            "ticket_id": ticket_id,
            "new_status": status,
            "message": f"Mock Jira ticket {ticket_id} updated to {status}."
        }


class ServiceNowMCPServer:
    """Mock ServiceNow MCP Server for IT incident management."""

    @staticmethod
    def create_incident(
        short_description: str,
        category: str = "IT Hardware",
        urgency: str = "Medium",
        caller: str = "employee@abctechnologies.com"
    ) -> Dict[str, Any]:
        global _snow_counter
        incident_id = f"MOCK-SNOW-{_snow_counter:03d}"
        _snow_counter += 1

        logger.info(f"[MCP SERVICENOW] Creating incident {incident_id}: {short_description}")
        return {
            "mock": True,
            "system": "ServiceNow",
            "status": "created",
            "incident_id": incident_id,
            "short_description": short_description,
            "category": category,
            "urgency": urgency,
            "caller": caller,
            "message": f"Mock ServiceNow incident {incident_id} created successfully."
        }

    @staticmethod
    def get_incident(incident_id: str) -> Dict[str, Any]:
        logger.info(f"[MCP SERVICENOW] Retrieving incident {incident_id}")
        return {
            "mock": True,
            "system": "ServiceNow",
            "status": "found",
            "incident_id": incident_id,
            "urgency": "Medium",
            "state": "New"
        }

    @staticmethod
    def update_incident(incident_id: str, work_notes: str) -> Dict[str, Any]:
        logger.info(f"[MCP SERVICENOW] Updating incident {incident_id}")
        return {
            "mock": True,
            "system": "ServiceNow",
            "status": "updated",
            "incident_id": incident_id,
            "work_notes": work_notes,
            "message": f"Mock ServiceNow incident {incident_id} updated."
        }


class OutlookMCPServer:
    """Mock Outlook MCP Server for email notifications."""

    @staticmethod
    def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
        logger.info(f"[MCP OUTLOOK] Sending mock email to {to}: {subject}")
        return {
            "mock": True,
            "system": "Outlook",
            "status": "sent",
            "recipient": to,
            "subject": subject,
            "message": f"Mock email sent to {to}."
        }


class SlackMCPServer:
    """Mock Slack MCP Server for team messaging."""

    @staticmethod
    def send_notification(channel: str, message: str) -> Dict[str, Any]:
        logger.info(f"[MCP SLACK] Sending notification to {channel}: {message}")
        return {
            "mock": True,
            "system": "Slack",
            "status": "sent",
            "channel": channel,
            "message_text": message,
            "message": f"Mock Slack notification sent to {channel}."
        }


class AWSMCPServer:
    """Mock AWS MCP Server for workspace diagnostics."""

    @staticmethod
    def run_diagnostic(instance_id: str = "i-abctech001") -> Dict[str, Any]:
        logger.info(f"[MCP AWS] Running diagnostic for workstation instance {instance_id}")
        return {
            "mock": True,
            "system": "AWS",
            "instance_id": instance_id,
            "cpu_usage": 92,
            "memory_usage": 88,
            "disk_usage": 95,
            "status": "performance_issue_detected",
            "diagnostics_summary": "High utilization detected on CPU (92%), Memory (88%), Disk (95%).",
            "suggested_fixes": [
                "Restart the laptop to terminate runaway background processes.",
                "Run Disk Cleanup to remove temporary cache files.",
                "Close resource-heavy browser tabs or application containers."
            ]
        }


# Central MCP Tool Registry Mapping
TOOLS: Dict[str, Callable] = {
    "jira.create_ticket": JiraMCPServer.create_ticket,
    "jira.get_ticket": JiraMCPServer.get_ticket,
    "jira.update_ticket": JiraMCPServer.update_ticket,
    "servicenow.create_incident": ServiceNowMCPServer.create_incident,
    "servicenow.get_incident": ServiceNowMCPServer.get_incident,
    "servicenow.update_incident": ServiceNowMCPServer.update_incident,
    "outlook.send_email": OutlookMCPServer.send_email,
    "slack.send_notification": SlackMCPServer.send_notification,
    "aws.run_diagnostic": AWSMCPServer.run_diagnostic,
}


def call_mcp_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Standardized execution abstraction for MCP tools.
    Validates tool existence and returns structured output tagged with MOCK: True.
    """
    if tool_name not in TOOLS:
        logger.error(f"Attempted call to unregistered tool: {tool_name}")
        return {
            "mock": True,
            "status": "error",
            "message": f"Tool '{tool_name}' is not registered in the MCP tool registry."
        }

    try:
        tool_func = TOOLS[tool_name]
        result = tool_func(**kwargs)
        result["mock"] = True
        return result
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {
            "mock": True,
            "status": "error",
            "message": f"Tool execution failed: {str(e)}"
        }
