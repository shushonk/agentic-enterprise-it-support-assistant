import pytest
from mock_mcp_servers import (
    JiraMCPServer,
    ServiceNowMCPServer,
    OutlookMCPServer,
    SlackMCPServer,
    AWSMCPServer,
    call_mcp_tool,
    TOOLS
)


def test_jira_mcp_server():
    res = JiraMCPServer.create_ticket(summary="Test VPN Issue", priority="High")
    assert res["mock"] is True
    assert res["status"] == "created"
    assert res["ticket_id"].startswith("MOCK-JIRA-")
    assert res["summary"] == "Test VPN Issue"

    get_res = JiraMCPServer.get_ticket(res["ticket_id"])
    assert get_res["mock"] is True
    assert get_res["status"] == "found"

    up_res = JiraMCPServer.update_ticket(res["ticket_id"], "In Progress")
    assert up_res["mock"] is True
    assert up_res["status"] == "updated"


def test_servicenow_mcp_server():
    res = ServiceNowMCPServer.create_incident(short_description="Slow laptop hardware issue")
    assert res["mock"] is True
    assert res["status"] == "created"
    assert res["incident_id"].startswith("MOCK-SNOW-")
    assert res["short_description"] == "Slow laptop hardware issue"

    get_res = ServiceNowMCPServer.get_incident(res["incident_id"])
    assert get_res["mock"] is True
    assert get_res["status"] == "found"


def test_outlook_mcp_server():
    res = OutlookMCPServer.send_email(to="user@abctechnologies.com", subject="Test Subject", body="Test Body")
    assert res["mock"] is True
    assert res["status"] == "sent"
    assert res["recipient"] == "user@abctechnologies.com"


def test_slack_mcp_server():
    res = SlackMCPServer.send_notification(channel="#it-support", message="Test alert message")
    assert res["mock"] is True
    assert res["status"] == "sent"
    assert res["channel"] == "#it-support"


def test_aws_mcp_server():
    res = AWSMCPServer.run_diagnostic(instance_id="i-test123")
    assert res["mock"] is True
    assert res["cpu_usage"] == 92
    assert res["memory_usage"] == 88
    assert res["disk_usage"] == 95
    assert res["status"] == "performance_issue_detected"


def test_mcp_tool_registry_call():
    for tool_name in TOOLS:
        if tool_name == "jira.create_ticket":
            res = call_mcp_tool(tool_name, summary="Test tool registry call")
        elif tool_name == "servicenow.create_incident":
            res = call_mcp_tool(tool_name, short_description="Test incident")
        elif tool_name == "outlook.send_email":
            res = call_mcp_tool(tool_name, to="test@abc.com", subject="Subj", body="Body")
        elif tool_name == "slack.send_notification":
            res = call_mcp_tool(tool_name, channel="#chan", message="Msg")
        elif tool_name == "aws.run_diagnostic":
            res = call_mcp_tool(tool_name, instance_id="i-123")
        else:
            continue

        assert res["mock"] is True
        assert res["status"] in ["created", "sent", "performance_issue_detected", "found", "updated"]


def test_invalid_mcp_tool():
    res = call_mcp_tool("nonexistent.tool")
    assert res["mock"] is True
    assert res["status"] == "error"
