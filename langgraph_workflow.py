import os
import random
import logging
from typing import Dict, Any, List, Optional, TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from mock_mcp_servers import call_mcp_tool

load_dotenv()
logger = logging.getLogger(__name__)

MAX_OTP_ATTEMPTS = int(os.getenv("MAX_OTP_ATTEMPTS", "3"))
REQUIRE_APPROVAL = os.getenv("REQUIRE_APPROVAL", "true").lower() == "true"


class SupportState(TypedDict, total=False):
    user_request: str
    intent: str
    workflow: str

    operating_system: Optional[str]
    restarted: Optional[bool]

    diagnostic_result: Optional[Dict[str, Any]]
    suggested_fixes: Optional[List[str]]
    resolved: Optional[bool]

    otp: Optional[str]
    otp_attempts: int
    identity_verified: Optional[bool]

    ticket_id: Optional[str]
    notification_status: Optional[str]

    waiting_for: Optional[str]
    suspended_workflows: Optional[Dict[str, Any]]

    approval_required: bool
    approval_id: Optional[str]
    approved: Optional[bool]

    status: str
    final_response: str
    messages: List[str]


# =====================================================================
# 1. SLOW LAPTOP WORKFLOW NODES & EDGES
# =====================================================================

def identify_slow_laptop_issue(state: SupportState) -> SupportState:
    logger.info("[WORKFLOW: Slow Laptop] Identifying issue details.")
    state["status"] = "RUNNING"
    state["workflow"] = "slow_laptop"
    if not state.get("messages"):
        state["messages"] = []
    if "🧠 Starting slow-laptop workflow..." not in state["messages"]:
        state["messages"].append("🧠 Starting slow-laptop workflow...")
    return state


def check_os_and_restart_step(state: SupportState) -> str:
    if not state.get("operating_system"):
        return "ask_os"
    if state.get("restarted") is None:
        return "ask_restart"
    return "run_diagnostics"


def ask_operating_system(state: SupportState) -> SupportState:
    state["waiting_for"] = "operating_system"
    state["status"] = "WAITING_FOR_USER"
    state["final_response"] = "What operating system are you using on your laptop (e.g., Windows 11, macOS, Linux)?"
    return state


def ask_restart_status(state: SupportState) -> SupportState:
    state["messages"].append(f"💻 OS: {state.get('operating_system')}")
    state["waiting_for"] = "restart_status"
    state["status"] = "WAITING_FOR_USER"
    state["final_response"] = "Have you restarted your laptop recently to clear background processes? (Yes/No)"
    return state


def run_laptop_diagnostics(state: SupportState) -> SupportState:
    logger.info("[WORKFLOW: Slow Laptop] Invoking AWS MCP diagnostic tool.")
    state["messages"].append(f"🔄 Restarted laptop: {'Yes' if state.get('restarted') else 'No'}")
    state["messages"].append("🔍 Running mock AWS diagnostics...")
    diag_result = call_mcp_tool("aws.run_diagnostic", instance_id="laptop-abc-789")
    state["diagnostic_result"] = diag_result
    
    cpu = diag_result.get("cpu_usage", 92)
    mem = diag_result.get("memory_usage", 88)
    disk = diag_result.get("disk_usage", 95)
    state["messages"].append(f"📊 CPU usage: {cpu}% | Memory: {mem}% | Disk: {disk}%")

    fixes = diag_result.get("suggested_fixes", [
        "Reboot system to clear unmanaged background memory.",
        "Run Disk Cleanup to remove temporary caches.",
        "Close resource-intensive applications."
    ])
    state["suggested_fixes"] = fixes
    state["messages"].append("🛠️ Analyzed diagnostic telemetry. Formulated troubleshooting steps.")
    return state


def check_resolution_step(state: SupportState) -> str:
    if state.get("resolved") is None:
        return "ask_resolution"
    elif state.get("resolved") is True:
        return "finish_resolved"
    else:
        return "check_approval"


def ask_laptop_resolution(state: SupportState) -> SupportState:
    fixes_str = "\n".join([f"{i+1}. {fix}" for i, fix in enumerate(state.get("suggested_fixes", []))])
    state["waiting_for"] = "resolution_status"
    state["status"] = "WAITING_FOR_USER"
    state["final_response"] = (
        f"Here are the recommended diagnostic troubleshooting steps:\n\n{fixes_str}\n\n"
        "Did these steps resolve your laptop performance issue? (Yes/No)"
    )
    return state


def finish_slow_laptop_resolved(state: SupportState) -> SupportState:
    state["status"] = "COMPLETED"
    state["waiting_for"] = None
    state["final_response"] = "Great! I'm glad your laptop performance issue is resolved. Please reach out if you need further IT assistance!"
    state["messages"].append("✅ Slow laptop workflow completed successfully (Issue Resolved).")
    return state


def check_approval_step(state: SupportState) -> str:
    if state.get("approved") is None:
        return "request_approval"
    elif state.get("approved") is True:
        return "create_ticket"
    else:
        return "finish_rejected"


def request_ticket_approval(state: SupportState) -> SupportState:
    logger.info("[WORKFLOW: Slow Laptop] Issue unresolved. Requesting ticket creation approval.")
    state["messages"].append("⚠️ Issue unresolved. Preparing ticket escalation...")
    state["approval_required"] = True
    state["approval_id"] = "APP-SLOW-LAPTOP-001"
    state["waiting_for"] = "approval"
    state["status"] = "WAITING_FOR_APPROVAL"
    state["final_response"] = (
        "APPROVAL REQUIRED:\n\n"
        "Action: Create ServiceNow Incident and Notify Manager\n"
        "Description: Unresolved laptop performance issue (CPU 92%, Disk 95%).\n\n"
        "Please click APPROVE or REJECT below to proceed."
    )
    return state


def create_laptop_ticket(state: SupportState) -> SupportState:
    logger.info("[WORKFLOW: Slow Laptop] Approval granted. Creating ServiceNow incident.")
    state["messages"].append("🎫 Creating MOCK ServiceNow incident...")
    
    inc_res = call_mcp_tool(
        "servicenow.create_incident",
        short_description=f"Laptop performance degraded (OS: {state.get('operating_system', 'Windows 11')})",
        category="Hardware",
        urgency="Medium"
    )
    ticket_id = inc_res.get("incident_id", "MOCK-SNOW-001")
    state["ticket_id"] = ticket_id
    state["messages"].append(f"🎫 Incident created: {ticket_id}")
    return state


def notify_laptop_manager(state: SupportState) -> SupportState:
    logger.info("[WORKFLOW: Slow Laptop] Sending manager notification.")
    state["messages"].append("📧 Sending MOCK manager notification...")
    
    slack_res = call_mcp_tool(
        "slack.send_notification",
        channel="#it-support-leads",
        message=f"Incident {state.get('ticket_id')} opened for employee laptop slowdown."
    )
    state["notification_status"] = slack_res.get("status", "sent")
    
    state["status"] = "COMPLETED"
    state["waiting_for"] = None
    state["final_response"] = (
        f"Your laptop performance issue has been escalated. A ServiceNow incident **{state.get('ticket_id')}** "
        f"has been created and your IT lead has been notified via Slack/Outlook. An IT engineer will reach out to you shortly."
    )
    state["messages"].append("✅ Workflow completed with ticket creation and manager notification.")
    return state


def finish_slow_laptop_rejected(state: SupportState) -> SupportState:
    state["status"] = "COMPLETED"
    state["waiting_for"] = None
    state["final_response"] = "The request to create an IT ticket was rejected. No ticket was logged. Let us know if you need anything else!"
    state["messages"].append("❌ Ticket approval rejected. Workflow finished without ticket creation.")
    return state


# Build Slow Laptop Graph
def build_slow_laptop_graph() -> StateGraph:
    builder = StateGraph(SupportState)
    
    builder.add_node("identify_issue", identify_slow_laptop_issue)
    builder.add_node("ask_os", ask_operating_system)
    builder.add_node("ask_restart", ask_restart_status)
    builder.add_node("run_diagnostics", run_laptop_diagnostics)
    builder.add_node("ask_resolution", ask_laptop_resolution)
    builder.add_node("finish_resolved", finish_slow_laptop_resolved)
    builder.add_node("request_approval", request_ticket_approval)
    builder.add_node("create_ticket", create_laptop_ticket)
    builder.add_node("notify_manager", notify_laptop_manager)
    builder.add_node("finish_rejected", finish_slow_laptop_rejected)

    builder.set_entry_point("identify_issue")

    builder.add_conditional_edges(
        "identify_issue",
        check_os_and_restart_step,
        {
            "ask_os": "ask_os",
            "ask_restart": "ask_restart",
            "run_diagnostics": "run_diagnostics"
        }
    )

    builder.add_edge("ask_os", END)
    builder.add_edge("ask_restart", END)

    builder.add_conditional_edges(
        "run_diagnostics",
        check_resolution_step,
        {
            "ask_resolution": "ask_resolution",
            "finish_resolved": "finish_resolved",
            "check_approval": "request_approval"
        }
    )

    builder.add_edge("ask_resolution", END)

    builder.add_conditional_edges(
        "request_approval",
        check_approval_step,
        {
            "request_approval": END,
            "create_ticket": "create_ticket",
            "finish_rejected": "finish_rejected"
        }
    )

    builder.add_edge("create_ticket", "notify_manager")
    builder.add_edge("notify_manager", END)
    builder.add_edge("finish_resolved", END)
    builder.add_edge("finish_rejected", END)

    return builder.compile()


# =====================================================================
# 2. PASSWORD RESET WORKFLOW NODES & EDGES
# =====================================================================

def verify_pwd_identity(state: SupportState) -> SupportState:
    logger.info("[WORKFLOW: Password Reset] Verifying identity.")
    state["status"] = "RUNNING"
    state["workflow"] = "password_reset"
    if not state.get("messages"):
        state["messages"] = []
    if "🔑 Initiating identity verification for password reset..." not in state["messages"]:
        state["messages"].append("🔑 Initiating identity verification for password reset...")
    state["otp_attempts"] = state.get("otp_attempts", 0)
    
    if not state.get("otp"):
        mock_otp = f"{random.randint(100000, 999999)}"
        state["otp"] = mock_otp
        logger.info(f"[WORKFLOW: Password Reset] Generated MOCK OTP: {mock_otp}")
        state["messages"].append(f"📱 Generated DEMONSTRATION ONLY — MOCK OTP: {mock_otp}")
    return state


def check_pwd_step(state: SupportState) -> str:
    if state.get("identity_verified") is True:
        return "reset_password"
    
    user_input = (state.get("user_request") or "").strip()
    if user_input and user_input != "I forgot my password." and not user_input.startswith("🔑 Initiating"):
        return "validate_otp"
    
    return "wait_for_otp"


def wait_for_otp_input(state: SupportState) -> SupportState:
    mock_otp = state.get("otp", "482913")
    attempts = state.get("otp_attempts", 0)
    state["waiting_for"] = "otp"
    state["status"] = "WAITING_FOR_USER"
    
    attempt_msg = f" (Attempt {attempts + 1} of {MAX_OTP_ATTEMPTS})" if attempts > 0 else ""
    state["final_response"] = (
        f"🔐 [DEMONSTRATION ONLY — MOCK OTP: **{mock_otp}**]\n\n"
        f"Please enter the 6-digit verification OTP sent to your registered contact{attempt_msg}:"
    )
    return state


def validate_otp_input(state: SupportState) -> SupportState:
    entered = state.get("user_request", "").strip()
    expected = state.get("otp", "")
    current_attempts = state.get("otp_attempts", 0) + 1
    state["otp_attempts"] = current_attempts

    if entered == expected or (expected and entered in expected):
        logger.info("[WORKFLOW: Password Reset] OTP validation successful.")
        state["identity_verified"] = True
        state["waiting_for"] = None
        state["messages"].append("✅ OTP verified successfully.")
    else:
        logger.warning(f"[WORKFLOW: Password Reset] Invalid OTP entered: '{entered}' (Attempt {current_attempts}/{MAX_OTP_ATTEMPTS})")
        state["identity_verified"] = False
        state["messages"].append(f"❌ Invalid OTP entered (Attempt {current_attempts}/{MAX_OTP_ATTEMPTS}).")
    return state


def check_otp_validation_result(state: SupportState) -> str:
    if state.get("identity_verified") is True:
        return "reset_password"
    elif state.get("otp_attempts", 0) >= MAX_OTP_ATTEMPTS:
        return "escalate_incident"
    else:
        return "wait_for_otp"


def reset_user_password(state: SupportState) -> SupportState:
    logger.info("[WORKFLOW: Password Reset] Executing mock password reset.")
    state["messages"].append("🔒 Resetting corporate SSO password (MOCK)...")
    state["ticket_id"] = "MOCK-PWD-RESET-88"
    return state


def notify_pwd_employee(state: SupportState) -> SupportState:
    logger.info("[WORKFLOW: Password Reset] Sending completion email via Outlook MCP.")
    state["messages"].append("📧 Sending password reset confirmation email (MOCK)...")
    call_mcp_tool(
        "outlook.send_email",
        to="employee@abctechnologies.com",
        subject="ABC Technologies - Password Reset Confirmation",
        body="Your corporate SSO password has been successfully reset."
    )
    state["status"] = "COMPLETED"
    state["waiting_for"] = None
    state["final_response"] = (
        "✅ Your ABC Technologies corporate SSO password has been reset successfully!\n\n"
        "A confirmation email has been sent to your registered mailbox. "
        "Please use your new password to sign into corporate applications."
    )
    state["messages"].append("✅ Password reset workflow completed.")
    return state


def escalate_pwd_incident(state: SupportState) -> SupportState:
    logger.error("[WORKFLOW: Password Reset] Max OTP attempts reached. Escalating to ServiceNow.")
    state["messages"].append("⚠️ Exceeded maximum OTP verification attempts. Escalating security incident...")
    
    inc_res = call_mcp_tool(
        "servicenow.create_incident",
        short_description="Multiple failed OTP password reset attempts - Account Lockout",
        category="Security",
        urgency="High"
    )
    incident_id = inc_res.get("incident_id", "MOCK-SNOW-002")
    state["ticket_id"] = incident_id
    state["status"] = "COMPLETED"
    state["waiting_for"] = None
    state["final_response"] = (
        f"🚨 You have exceeded the maximum allowed OTP attempts ({MAX_OTP_ATTEMPTS}).\n\n"
        f"For security compliance, your account password reset has been suspended and a high-priority ServiceNow "
        f"security incident **{incident_id}** has been dispatched to the IT Security Team."
    )
    state["messages"].append(f"🚨 Escalated to ServiceNow Incident {incident_id}.")
    return state


# Build Password Reset Graph
def build_password_reset_graph() -> StateGraph:
    builder = StateGraph(SupportState)

    builder.add_node("verify_identity", verify_pwd_identity)
    builder.add_node("wait_for_otp", wait_for_otp_input)
    builder.add_node("validate_otp", validate_otp_input)
    builder.add_node("reset_password", reset_user_password)
    builder.add_node("notify_employee", notify_pwd_employee)
    builder.add_node("escalate_incident", escalate_pwd_incident)

    builder.set_entry_point("verify_identity")

    builder.add_conditional_edges(
        "verify_identity",
        check_pwd_step,
        {
            "wait_for_otp": "wait_for_otp",
            "validate_otp": "validate_otp",
            "reset_password": "reset_password"
        }
    )

    builder.add_edge("wait_for_otp", END)

    builder.add_conditional_edges(
        "validate_otp",
        check_otp_validation_result,
        {
            "reset_password": "reset_password",
            "wait_for_otp": "wait_for_otp",
            "escalate_incident": "escalate_incident"
        }
    )

    builder.add_edge("reset_password", "notify_employee")
    builder.add_edge("notify_employee", END)
    builder.add_edge("escalate_incident", END)

    return builder.compile()


# =====================================================================
# 3. VPN TROUBLESHOOTING WORKFLOW NODES & EDGES
# =====================================================================

def init_vpn_workflow(state: SupportState) -> SupportState:
    state["status"] = "RUNNING"
    state["workflow"] = "vpn_troubleshooting"
    if not state.get("messages"):
        state["messages"] = []
    state["messages"].append("🌐 Starting VPN Troubleshooting workflow...")
    return state


def ask_vpn_os(state: SupportState) -> SupportState:
    if not state.get("operating_system"):
        state["waiting_for"] = "vpn_os"
        state["status"] = "WAITING_FOR_USER"
        state["final_response"] = "Which operating system are you connecting to GlobalProtect VPN from (e.g. Windows, macOS, Linux)?"
    else:
        state["messages"].append(f"💻 VPN OS: {state['operating_system']}")
        state["waiting_for"] = None
    return state


def run_vpn_diagnostics(state: SupportState) -> SupportState:
    state["messages"].append("🔍 Checking GlobalProtect client configurations and gateway endpoints...")
    state["messages"].append("🛠️ Gateway: vpn-us.abctechnologies.com | Status: DNS Resolution Warning")
    return state


def suggest_vpn_fixes(state: SupportState) -> SupportState:
    if state.get("resolved") is None:
        state["waiting_for"] = "vpn_resolution"
        state["status"] = "WAITING_FOR_USER"
        state["final_response"] = (
            "Please try the following VPN troubleshooting steps:\n\n"
            "1. Open Command Prompt and run `ipconfig /flushdns`.\n"
            "2. Restart the GlobalProtect service via Task Manager -> Services.\n"
            "3. Select gateway endpoint `vpn-us.abctechnologies.com` explicitly.\n\n"
            "Did this solve your VPN connection issue? (Yes/No)"
        )
    return state


def finish_vpn_resolved(state: SupportState) -> SupportState:
    state["status"] = "COMPLETED"
    state["waiting_for"] = None
    state["final_response"] = "Awesome! Glad your VPN connection is restored."
    state["messages"].append("✅ VPN workflow completed (Resolved).")
    return state


def create_vpn_ticket(state: SupportState) -> SupportState:
    state["messages"].append("🎫 Creating MOCK Jira ticket for VPN issue...")
    ticket_res = call_mcp_tool(
        "jira.create_ticket",
        summary=f"VPN Connection Failure on {state.get('operating_system', 'Windows')}",
        priority="High"
    )
    ticket_id = ticket_res.get("ticket_id", "MOCK-JIRA-005")
    state["ticket_id"] = ticket_id
    state["status"] = "COMPLETED"
    state["waiting_for"] = None
    state["final_response"] = (
        f"Your VPN issue has been logged as Jira ticket **{ticket_id}**. "
        "Network Operations has been notified."
    )
    state["messages"].append(f"✅ VPN ticket created: {ticket_id}")
    return state


def build_vpn_workflow_graph() -> StateGraph:
    builder = StateGraph(SupportState)
    builder.add_node("init_vpn", init_vpn_workflow)
    builder.add_node("ask_vpn_os", ask_vpn_os)
    builder.add_node("run_vpn_diag", run_vpn_diagnostics)
    builder.add_node("suggest_vpn_fixes", suggest_vpn_fixes)
    builder.add_node("finish_vpn_resolved", finish_vpn_resolved)
    builder.add_node("create_vpn_ticket", create_vpn_ticket)

    builder.set_entry_point("init_vpn")
    builder.add_edge("init_vpn", "ask_vpn_os")
    builder.add_edge("ask_vpn_os", "run_vpn_diag")
    builder.add_edge("run_vpn_diag", "suggest_vpn_fixes")

    builder.add_conditional_edges(
        "suggest_vpn_fixes",
        lambda s: "resolved" if s.get("resolved") is True else "unresolved",
        {
            "resolved": "finish_vpn_resolved",
            "unresolved": "create_vpn_ticket"
        }
    )

    builder.add_edge("finish_vpn_resolved", END)
    builder.add_edge("create_vpn_ticket", END)
    return builder.compile()


# Compiled Workflow Instances
SLOW_LAPTOP_APP = build_slow_laptop_graph()
PASSWORD_RESET_APP = build_password_reset_graph()
VPN_WORKFLOW_APP = build_vpn_workflow_graph()


# Session Thread Storage for State Persistence & Suspend/Resume
_WORKFLOW_SESSIONS: Dict[str, SupportState] = {}


def get_or_create_session(thread_id: str) -> SupportState:
    """Retrieve existing session state or initialize a fresh state."""
    if thread_id not in _WORKFLOW_SESSIONS:
        _WORKFLOW_SESSIONS[thread_id] = {
            "user_request": "",
            "intent": "",
            "workflow": "",
            "operating_system": None,
            "restarted": None,
            "diagnostic_result": None,
            "suggested_fixes": [],
            "resolved": None,
            "otp": None,
            "otp_attempts": 0,
            "identity_verified": None,
            "ticket_id": None,
            "notification_status": None,
            "waiting_for": None,
            "approval_required": False,
            "approval_id": None,
            "approved": None,
            "status": "IDLE",
            "final_response": "",
            "messages": []
        }
    return _WORKFLOW_SESSIONS[thread_id]


def reset_session(thread_id: str):
    """Clear session state for a given thread."""
    if thread_id in _WORKFLOW_SESSIONS:
        del _WORKFLOW_SESSIONS[thread_id]
