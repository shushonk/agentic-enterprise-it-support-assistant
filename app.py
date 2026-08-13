import os
import time
import uuid
import logging
import gradio as gr
from dotenv import load_dotenv

from main_agent import MainSupportAgent

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize Main Agent Backend
agent = MainSupportAgent()

# Custom CSS for Enterprise AI Dashboard Design System
CUSTOM_CSS = """
:root {
    --bg-dark: #090d16;
    --bg-card: #111827;
    --bg-card-hover: #1e293b;
    --border-color: #334155;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --accent-blue: #38bdf8;
    --accent-indigo: #6366f1;
    --accent-green: #22c55e;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
}

body, .gradio-container {
    background-color: var(--bg-dark) !important;
    color: var(--text-main) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

/* Header Banner */
.header-container {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}

.header-title {
    font-size: 24px;
    font-weight: 700;
    color: #ffffff;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 10px;
}

.header-subtitle {
    font-size: 13px;
    color: var(--accent-blue);
    margin-top: 4px;
    font-weight: 500;
}

/* Top Status Bar */
.top-status-bar {
    background-color: #0f172a;
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: center;
    justify-content: space-between;
}

.status-badge-pill {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #e2e8f0;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.dot-green {
    width: 8px;
    height: 8px;
    background-color: #22c55e;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 8px #22c55e;
}

.dot-amber {
    width: 8px;
    height: 8px;
    background-color: #f59e0b;
    border-radius: 50%;
    display: inline-block;
}

.dot-blue {
    width: 8px;
    height: 8px;
    background-color: #38bdf8;
    border-radius: 50%;
    display: inline-block;
}

/* Cards & Panels */
.dashboard-card {
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
}

/* Chatbot Custom Styling */
.chatbot-container {
    border: 1px solid var(--border-color) !important;
    border-radius: 12px !important;
    background-color: #0f172a !important;
}

/* Primary/Secondary Buttons */
.btn-primary-custom {
    background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}

.btn-primary-custom:hover {
    background: linear-gradient(135deg, #1d4ed8 0%, #4338ca 100%) !important;
}

.btn-secondary-custom {
    background-color: #1e293b !important;
    border: 1px solid #475569 !important;
    color: #cbd5e1 !important;
    border-radius: 8px !important;
}

.btn-secondary-custom:hover {
    background-color: #334155 !important;
    color: white !important;
}

/* Approval Card Box */
.approval-card-container {
    background: linear-gradient(135deg, #451a03 0%, #78350f 100%);
    border: 2px solid #f59e0b;
    border-radius: 12px;
    padding: 16px;
    margin-top: 12px;
    margin-bottom: 12px;
}

.paused-card-container {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
    border: 2px solid #6366f1;
    border-radius: 12px;
    padding: 16px;
    margin-top: 12px;
    margin-bottom: 12px;
}

/* Footer */
.custom-footer {
    border-top: 1px solid var(--border-color);
    padding-top: 16px;
    margin-top: 24px;
    text-align: center;
    font-size: 12px;
    color: var(--text-muted);
}
"""

WELCOME_MSG = """Hello! I'm the **ABC Technologies AI Support Assistant**.

I can help with:
• HR and IT policies
• VPN and software access
• Password support
• IT tickets
• Multi-step troubleshooting

How can I help you today?"""

# Dict format required by Gradio 6.0 Chatbot
DEFAULT_CHAT_HISTORY = [
    {"role": "assistant", "content": WELCOME_MSG}
]


def extract_text(content):
    """Safely extract plain text from string or Gradio 6.0 content object lists."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list) and len(content) > 0:
        first = content[0]
        if isinstance(first, dict):
            return first.get("text", str(first))
        elif hasattr(first, "text"):
            return first.text
    return str(content) if content is not None else ""


def normalize_history(history_input):
    """Convert input history into clean list of dict messages for Gradio Chatbot."""
    if not history_input:
        return list(DEFAULT_CHAT_HISTORY)
    
    clean = []
    for item in history_input:
        if isinstance(item, dict):
            role = item.get("role", "user")
            text = extract_text(item.get("content", ""))
            clean.append({"role": role, "content": text})
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            if item[0]:
                clean.append({"role": "user", "content": str(item[0])})
            if item[1]:
                clean.append({"role": "assistant", "content": str(item[1])})

    return clean if clean else list(DEFAULT_CHAT_HISTORY)


def render_top_status_bar(ollama_online: bool = True):
    return """
    <div class="top-status-bar">
        <div class="status-badge-pill"><span class="dot-green"></span> SYSTEM: Operational</div>
        <div class="status-badge-pill"><span class="dot-green"></span> LLM ROUTER: Active</div>
        <div class="status-badge-pill"><span class="dot-blue"></span> RAG: ChromaDB Ready</div>
        <div class="status-badge-pill"><span class="dot-blue"></span> LANGGRAPH: Ready</div>
        <div class="status-badge-pill"><span class="dot-green"></span> MCP: Mock Servers Ready</div>
    </div>
    """


def render_agent_control_center(status_badge: str, workflow_name: str, state_status: str, session_id: str):
    return f"""
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
        <div style="background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase;">Agent Status</div>
            <div style="font-size: 14px; font-weight: 700; color: #38bdf8; margin-top: 4px;">{status_badge}</div>
        </div>
        <div style="background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase;">Active Workflow</div>
            <div style="font-size: 14px; font-weight: 700; color: #a78bfa; margin-top: 4px;">{workflow_name}</div>
        </div>
        <div style="background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase;">Workflow State</div>
            <div style="font-size: 14px; font-weight: 700; color: #facc15; margin-top: 4px;">{state_status}</div>
        </div>
        <div style="background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase;">Session ID</div>
            <div style="font-size: 14px; font-weight: 700; color: #4ade80; margin-top: 4px;">REQ-{session_id.upper()}</div>
        </div>
    </div>
    """


def render_architecture_components():
    return """
    <div style="background: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 12px;">
        <div style="font-size: 12px; font-weight: 700; color: #e2e8f0; margin-bottom: 8px;">⚙️ ARCHITECTURE COMPONENTS</div>
        <div style="display: flex; flex-direction: column; gap: 6px; font-size: 12px;">
            <div style="display: flex; justify-content: space-between;"><span>🧠 LLM Intent Router</span><span style="color: #4ade80; font-weight: 600;">ACTIVE</span></div>
            <div style="display: flex; justify-content: space-between;"><span>📚 ChromaDB Vector RAG</span><span style="color: #38bdf8; font-weight: 600;">READY</span></div>
            <div style="display: flex; justify-content: space-between;"><span>🔄 LangGraph State Machine</span><span style="color: #a78bfa; font-weight: 600;">ACTIVE</span></div>
            <div style="display: flex; justify-content: space-between;"><span>🔌 Mock MCP Tools Server</span><span style="color: #facc15; font-weight: 600;">READY</span></div>
            <div style="display: flex; justify-content: space-between;"><span>📊 Observability Engine</span><span style="color: #4ade80; font-weight: 600;">ACTIVE</span></div>
        </div>
    </div>
    """


def render_tools_used(state_dict: dict, is_rag: bool, is_action: bool):
    tools = []
    if is_rag:
        tools.append('<span style="background: #1e3a8a; color: #93c5fd; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">ChromaDB RAG Retrieval</span>')
    
    wf = state_dict.get("workflow")
    if wf:
        tools.append(f'<span style="background: #312e81; color: #c7d2fe; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">LangGraph ({wf})</span>')
    
    if state_dict.get("diagnostic_result"):
        tools.append('<span style="background: #065f46; color: #a7f3d0; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">MOCK AWS Diagnostic</span>')
    
    if state_dict.get("ticket_id"):
        t_id = state_dict.get("ticket_id", "")
        if "SNOW" in t_id:
            tools.append('<span style="background: #831843; color: #fbcfe8; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">MOCK ServiceNow Incident</span>')
        elif "JIRA" in t_id:
            tools.append('<span style="background: #1e3a8a; color: #bfdbfe; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">MOCK Jira Ticket</span>')

    if state_dict.get("notification_status"):
        tools.append('<span style="background: #701a75; color: #f5d0fe; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">MOCK Outlook Email</span>')

    if is_action and not tools:
        tools.append('<span style="background: #1e3a8a; color: #bfdbfe; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">MOCK Jira Action</span>')

    if not tools:
        tools_html = '<span style="color: #64748b; font-size: 12px; italic;">No external tools invoked yet</span>'
    else:
        tools_html = '<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px;">' + "".join(tools) + '</div>'

    return f"""
    <div style="background: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 12px;">
        <div style="font-size: 12px; font-weight: 700; color: #e2e8f0; margin-bottom: 6px;">🛠️ TOOLS USED (ENTERPRISE MOCK REGISTRY)</div>
        {tools_html}
    </div>
    """


def render_workflow_diagram(workflow_name: str, state_status: str, waiting_for: str):
    if not workflow_name or workflow_name == "None":
        return """
        <div style="background: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 12px;">
            <div style="font-size: 12px; font-weight: 700; color: #94a3b8;">🔄 WORKFLOW GRAPH: IDLE</div>
            <div style="font-size: 12px; color: #64748b; margin-top: 4px;">No active LangGraph workflow currently running. Select a workflow query to visualize graph execution.</div>
        </div>
        """

    if workflow_name == "slow_laptop":
        s1 = "✓"
        s2 = "✓" if waiting_for not in ["operating_system"] else "⏳"
        s3 = "✓" if waiting_for not in ["operating_system", "restart_status"] else ("⏳" if waiting_for == "restart_status" else "○")
        s4 = "✓" if state_status in ["WAITING_FOR_APPROVAL", "COMPLETED"] else ("⏳" if state_status == "RUNNING" else "○")
        s5 = "✓" if state_status == "COMPLETED" else ("⚠️" if state_status == "WAITING_FOR_APPROVAL" else "○")

        return f"""
        <div style="background: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 12px;">
            <div style="font-size: 12px; font-weight: 700; color: #a78bfa; margin-bottom: 8px;">🔄 WORKFLOW: SLOW LAPTOP (LANGGRAPH)</div>
            <div style="display: flex; flex-direction: column; gap: 4px; font-size: 12px;">
                <div>{s1} 1. Request Classified</div>
                <div>{s2} 2. Collect Operating System</div>
                <div>{s3} 3. Check Laptop Restart Status</div>
                <div>{s4} 4. Run AWS Diagnostics (MOCK)</div>
                <div>{s5} 5. Human Approval & Incident Creation (MOCK)</div>
            </div>
        </div>
        """
    elif workflow_name == "password_reset":
        s1 = "✓"
        s2 = "⏳" if waiting_for == "otp" else "✓"
        s3 = "✓" if state_status == "COMPLETED" else "○"
        return f"""
        <div style="background: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 12px;">
            <div style="font-size: 12px; font-weight: 700; color: #a78bfa; margin-bottom: 8px;">🔄 WORKFLOW: PASSWORD RESET (LANGGRAPH)</div>
            <div style="display: flex; flex-direction: column; gap: 4px; font-size: 12px;">
                <div>{s1} 1. Account Identity Identification</div>
                <div>{s2} 2. OTP Security Challenge</div>
                <div>{s3} 3. Password Reset & Notification</div>
            </div>
        </div>
        """
    else:
        return f"""
        <div style="background: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 12px;">
            <div style="font-size: 12px; font-weight: 700; color: #a78bfa;">🔄 WORKFLOW: {workflow_name.upper()}</div>
            <div style="font-size: 12px; color: #38bdf8; margin-top: 4px;">Status: {state_status}</div>
        </div>
        """


def build_activity_timeline(messages: list, state_status: str, exec_time: float, log_step: str):
    events = []
    if log_step:
        events.append(f"⏳ {log_step}")
    
    if messages:
        for m in messages:
            clean_m = m.replace("🧠 ", "").replace("💻 ", "").replace("🔄 ", "").replace("🔍 ", "").replace("📊 ", "")
            events.append(f"✓ {clean_m}")

    if state_status == "WAITING_FOR_APPROVAL":
        events.append("⚠️ Action paused: Human Approval Required")
    elif state_status == "WAITING_FOR_USER":
        events.append("⏳ Action paused: Waiting for User Input")
    elif state_status == "COMPLETED":
        events.append("✓ Execution Completed")

    timeline_text = "\n".join(events[-8:]) if events else "✓ System initialized. Ready for support requests."
    return f"```\n{timeline_text}\n\n⏱️ Execution time: {exec_time:.2f}s\n```"


def build_observability_md(session_id: str, workflow: str, status: str, duration: float, tools: list):
    tools_str = ", ".join(tools) if tools else "None"
    return f"""
**Request ID:** `REQ-{session_id.upper()}`  
**Current Workflow:** `{workflow or 'None'}`  
**State:** `{status}`  
**Duration:** `{duration:.2f}s`  
**Components:** `LLM Router`, `ChromaDB RAG`, `LangGraph`, `Mock MCP`  
**Tools Invoked:** `{tools_str}`  
**Status:** `{status}`
"""


def user_submit_message(message: str, history: list, session_id: str):
    """
    Handle user message submit with streaming updates.
    EVERY yield statement MUST return EXACTLY 19 output values matching send_outputs.
    """
    if not message or not message.strip():
        yield (
            normalize_history(history),                                      # 1. chatbot
            "",                                                              # 2. user_input
            render_agent_control_center("🟢 Ready", "None", "IDLE", session_id or "DEF"), # 3. control_center_html
            render_architecture_components(),                                # 4. arch_status_html
            render_workflow_diagram("None", "IDLE", ""),                     # 5. workflow_diagram_md
            render_tools_used({}, False, False),                            # 6. tools_used_html
            "```\n✓ Ready\n```",                                             # 7. activity_timeline_md
            build_observability_md(session_id or "DEF", "None", "IDLE", 0.0, []), # 8. observability_md
            gr.update(visible=False),                                        # 9. approval_card_box
            "No active approval",                                            # 10. approval_desc_md
            gr.update(visible=False),                                        # 11. workflow_paused_box
            "",                                                              # 12. workflow_paused_md
            gr.update(visible=False),                                        # 13. rag_vis_box
            "",                                                              # 14. rag_info_md
            gr.update(visible=False),                                        # 15. mcp_vis_box
            "",                                                              # 16. mcp_info_md
            session_id or "DEF",                                             # 17. session_id_state
            "🟢 Ready",                                                       # 18. agent_status_state
            "IDLE"                                                           # 19. workflow_state_state
        )
        return

    if not session_id:
        session_id = str(uuid.uuid4())[:8]

    start_time = time.time()
    
    # Normalize history to clean dict messages
    updated_history = normalize_history(history)
    updated_history.append({"role": "user", "content": message})
    updated_history.append({"role": "assistant", "content": "Analyzing request..."})

    try:
        # Stream intermediate steps to Gradio UI
        for log_step, resp_step, state_dict in agent.process_message_stream(message, thread_id=session_id):
            exec_time = time.time() - start_time
            
            wf_name = state_dict.get("workflow") or "None"
            state_status = state_dict.get("status") or "RUNNING"
            waiting_for = state_dict.get("waiting_for") or ""

            is_rag = "knowledge" in log_step.lower() or "knowledge base" in log_step.lower() or "retrieved" in log_step.lower()
            is_action = "mcp tool" in log_step.lower() or "jira" in log_step.lower() or "ticket" in log_step.lower()

            if state_status == "WAITING_FOR_APPROVAL":
                status_badge = "⚠️ Approval Required"
                approval_card_vis = gr.update(visible=True)
                approval_text = "### ⚠️ HUMAN-IN-THE-LOOP APPROVAL REQUIRED\n\n**Action:** Create ServiceNow Incident (MOCK)\n**Reason:** Unresolved hardware/VPN issue requires IT Support Dispatch."
                paused_card_vis = gr.update(visible=False)
                paused_text = ""
            elif state_status == "WAITING_FOR_USER":
                status_badge = "⏸ Workflow Paused"
                approval_card_vis = gr.update(visible=False)
                approval_text = ""
                paused_card_vis = gr.update(visible=True)
                paused_text = f"### ⏸ WORKFLOW PAUSED\n\nThe workflow requires user input to proceed.\n\n**Awaiting:** `{waiting_for}`"
            elif state_status == "COMPLETED":
                status_badge = "🟢 Ready"
                approval_card_vis = gr.update(visible=False)
                approval_text = ""
                paused_card_vis = gr.update(visible=False)
                paused_text = ""
            else:
                status_badge = "⚙️ Processing..."
                approval_card_vis = gr.update(visible=False)
                approval_text = ""
                paused_card_vis = gr.update(visible=False)
                paused_text = ""

            if resp_step:
                updated_history[-1]["content"] = extract_text(resp_step)

            ctrl_html = render_agent_control_center(status_badge, wf_name, state_status, session_id)
            activity_md = build_activity_timeline(state_dict.get("messages", []), state_status, exec_time, log_step)
            arch_html = render_architecture_components()
            tools_html = render_tools_used(state_dict, is_rag, is_action)
            workflow_diagram_md = render_workflow_diagram(wf_name, state_status, waiting_for)

            invoked_tools = []
            if is_rag:
                invoked_tools.append("ChromaDB RAG")
            if wf_name != "None":
                invoked_tools.append(f"LangGraph ({wf_name})")
            if state_dict.get("diagnostic_result"):
                invoked_tools.append("AWS Diagnostic MOCK")
            if state_dict.get("ticket_id"):
                invoked_tools.append(f"{state_dict.get('ticket_id')} MOCK")

            observability_md = build_observability_md(session_id, wf_name, state_status, exec_time, invoked_tools)

            # RAG Vis panel
            if is_rag:
                rag_vis = gr.update(visible=True)
                rag_info = f"**Query:** `{message}`\n\n**Source:** ABC Technologies Knowledge Base (`docs/`)\n\n**Status:** Grounded Response Generated via RAG"
            else:
                rag_vis = gr.update(visible=False)
                rag_info = ""

            # MCP Vis panel
            if is_action or state_dict.get("ticket_id"):
                mcp_vis = gr.update(visible=True)
                mcp_info = f"**Tool Requested:** `{state_dict.get('ticket_id', 'jira.create_ticket')}`\n\n**Server:** Mock MCP Enterprise Server\n\n**Status:** Execution Success"
            else:
                mcp_vis = gr.update(visible=False)
                mcp_info = ""

            # ALWAYS YIELD EXACTLY 19 OUTPUT VALUES MATCHING send_outputs
            yield (
                updated_history,         # 1. chatbot
                "",                      # 2. user_input
                ctrl_html,               # 3. control_center_html
                arch_html,               # 4. arch_status_html
                workflow_diagram_md,     # 5. workflow_diagram_md
                tools_html,              # 6. tools_used_html
                activity_md,             # 7. activity_timeline_md
                observability_md,        # 8. observability_md
                approval_card_vis,       # 9. approval_card_box
                approval_text,           # 10. approval_desc_md
                paused_card_vis,         # 11. workflow_paused_box
                paused_text,             # 12. workflow_paused_md
                rag_vis,                 # 13. rag_vis_box
                rag_info,                # 14. rag_info_md
                mcp_vis,                 # 15. mcp_vis_box
                mcp_info,                # 16. mcp_info_md
                session_id,              # 17. session_id_state
                status_badge,            # 18. agent_status_state
                state_status             # 19. workflow_state_state
            )

    except Exception as e:
        logger.error(f"Error processing message stream: {e}", exc_info=True)
        updated_history[-1]["content"] = f"An error occurred: {str(e)}"
        yield (
            updated_history,
            "",
            render_agent_control_center("❌ Error", "None", "ERROR", session_id),
            render_architecture_components(),
            render_workflow_diagram("None", "ERROR", ""),
            render_tools_used({}, False, False),
            f"```\n❌ Error: {str(e)}\n```",
            build_observability_md(session_id, "None", "ERROR", 0.0, []),
            gr.update(visible=False),
            "",
            gr.update(visible=False),
            "",
            gr.update(visible=False),
            "",
            gr.update(visible=False),
            "",
            session_id,
            "❌ Error",
            "ERROR"
        )


def handle_approval_click(approved: bool, history: list, session_id: str):
    """Handle Approve or Reject button click. ALWAYS yields 19 output values."""
    if not session_id:
        session_id = "default_session"

    start_time = time.time()
    updated_history = normalize_history(history)
    updated_history.append({"role": "assistant", "content": "Processing approval..."})

    try:
        for log_step, resp_step, state_dict in agent.handle_approval_action(session_id, approved=approved):
            exec_time = time.time() - start_time
            wf_name = state_dict.get("workflow") or "None"
            state_status = state_dict.get("status") or "COMPLETED"

            if resp_step:
                updated_history[-1]["content"] = extract_text(resp_step)

            status_badge = "🟢 Ready" if state_status == "COMPLETED" else "⚙️ Processing..."
            ctrl_html = render_agent_control_center(status_badge, wf_name, state_status, session_id)
            activity_md = build_activity_timeline(state_dict.get("messages", []), state_status, exec_time, log_step)
            arch_html = render_architecture_components()
            tools_html = render_tools_used(state_dict, False, True)
            workflow_diagram_md = render_workflow_diagram(wf_name, state_status, "")

            invoked_tools = ["LangGraph", "ServiceNow Incident MOCK"]
            observability_md = build_observability_md(session_id, wf_name, state_status, exec_time, invoked_tools)

            # ALWAYS YIELD EXACTLY 19 OUTPUT VALUES MATCHING send_outputs
            yield (
                updated_history,
                "",
                ctrl_html,
                arch_html,
                workflow_diagram_md,
                tools_html,
                activity_md,
                observability_md,
                gr.update(visible=False),
                "Approval Action Executed",
                gr.update(visible=False),
                "",
                gr.update(visible=False),
                "",
                gr.update(visible=True),
                f"**MCP Action:** ServiceNow Incident Creation {'Approved ✅' if approved else 'Rejected ❌'}",
                session_id,
                status_badge,
                state_status
            )
    except Exception as e:
        logger.error(f"Error handling approval action: {e}", exc_info=True)
        updated_history[-1]["content"] = f"Approval error: {str(e)}"
        yield (
            updated_history,
            "",
            render_agent_control_center("❌ Error", "None", "ERROR", session_id),
            render_architecture_components(),
            render_workflow_diagram("None", "ERROR", ""),
            render_tools_used({}, False, False),
            f"```\n❌ Approval Error: {str(e)}\n```",
            build_observability_md(session_id, "None", "ERROR", 0.0, []),
            gr.update(visible=False),
            "",
            gr.update(visible=False),
            "",
            gr.update(visible=False),
            "",
            gr.update(visible=False),
            "",
            session_id,
            "❌ Error",
            "ERROR"
        )


def reset_conversation():
    """Reset the Gradio conversation UI and session state. ALWAYS returns 19 output values."""
    new_session_id = str(uuid.uuid4())[:8]
    agent.reset_thread(new_session_id)
    return (
        list(DEFAULT_CHAT_HISTORY),                                         # 1. chatbot
        "",                                                                 # 2. user_input
        render_agent_control_center("🟢 Ready", "None", "IDLE", new_session_id), # 3. control_center_html
        render_architecture_components(),                                   # 4. arch_status_html
        render_workflow_diagram("None", "IDLE", ""),                        # 5. workflow_diagram_md
        render_tools_used({}, False, False),                               # 6. tools_used_html
        "```\n✓ Session reset. Ready for new support requests.\n```",      # 7. activity_timeline_md
        build_observability_md(new_session_id, "None", "IDLE", 0.0, []),    # 8. observability_md
        gr.update(visible=False),                                           # 9. approval_card_box
        "",                                                                 # 10. approval_desc_md
        gr.update(visible=False),                                           # 11. workflow_paused_box
        "",                                                                 # 12. workflow_paused_md
        gr.update(visible=False),                                           # 13. rag_vis_box
        "",                                                                 # 14. rag_info_md
        gr.update(visible=False),                                           # 15. mcp_vis_box
        "",                                                                 # 16. mcp_info_md
        new_session_id,                                                     # 17. session_id_state
        "🟢 Ready",                                                          # 18. agent_status_state
        "IDLE"                                                              # 19. workflow_state_state
    )


# Build Polished Gradio Enterprise AI Support Dashboard UI
with gr.Blocks(title="ABC Technologies - Enterprise AI Support Assistant") as demo:
    session_id_state = gr.State(value=lambda: str(uuid.uuid4())[:8])
    agent_status_state = gr.State(value="🟢 Ready")
    workflow_state_state = gr.State(value="IDLE")

    # Top Header Banner
    with gr.Row(elem_classes=["header-container"]):
        with gr.Column(scale=4):
            gr.HTML("""
            <div>
                <div class="header-title">🏢 ABC TECHNOLOGIES <span style="font-weight: 400; font-size: 18px; color: #94a3b8;">| Enterprise AI Support Assistant</span></div>
                <div class="header-subtitle">Agentic IT & HR Automation powered by LLM Router + ChromaDB RAG + LangGraph + Mock MCP</div>
            </div>
            """)
        with gr.Column(scale=1):
            gr.HTML("""
            <div style="text-align: right;">
                <span class="status-badge-pill"><span class="dot-green"></span> System Operational</span>
            </div>
            """)

    # Top Status Indicators Bar
    gr.HTML(render_top_status_bar())

    # Main Two-Column Dashboard Layout
    with gr.Row():
        # LEFT COLUMN (~68% width): Support Chat & Visualizers
        with gr.Column(scale=7):
            gr.Markdown("### 💬 AI Support Chat Window")
            
            chatbot = gr.Chatbot(
                value=DEFAULT_CHAT_HISTORY,
                label="Support Assistant Chat",
                height=520,
                elem_classes=["chatbot-container"]
            )

            # Input Area
            with gr.Row():
                user_input = gr.Textbox(
                    placeholder="Describe your IT or HR support request (e.g. 'What is the VPN policy?', 'My laptop is extremely slow', 'I forgot my password')...",
                    label="Employee Input",
                    scale=5,
                    lines=1
                )
                send_btn = gr.Button("SEND 🚀", variant="primary", scale=1, elem_classes=["btn-primary-custom"])
                reset_btn = gr.Button("CLEAR 🔄", variant="secondary", scale=1, elem_classes=["btn-secondary-custom"])

            # Quick Demo Buttons
            gr.Markdown("#### 💡 QUICK DEMO SCENARIOS")
            with gr.Row():
                btn_demo1 = gr.Button("🔐 VPN Policy", elem_classes=["btn-secondary-custom"])
                btn_demo2 = gr.Button("🐳 Docker Access", elem_classes=["btn-secondary-custom"])
                btn_demo3 = gr.Button("🔑 Password Reset", elem_classes=["btn-secondary-custom"])
                btn_demo4 = gr.Button("💻 Slow Laptop", elem_classes=["btn-secondary-custom"])
                btn_demo5 = gr.Button("🎫 Create Ticket", elem_classes=["btn-secondary-custom"])

            # RAG Retrieval Visualizer Panel
            with gr.Group(visible=False) as rag_vis_box:
                gr.Markdown("### 📚 KNOWLEDGE BASE RETRIEVAL (ChromaDB RAG)")
                rag_info_md = gr.Markdown("")

            # MCP Tool Execution Visualizer Panel
            with gr.Group(visible=False) as mcp_vis_box:
                gr.Markdown("### ⚡ ENTERPRISE MCP TOOL EXECUTION")
                mcp_info_md = gr.Markdown("")

        # RIGHT COLUMN (~32% width): Agent & Workflow Control Center
        with gr.Column(scale=3):
            gr.Markdown("### 📊 AGENT CONTROL CENTER")

            # Dynamic Metrics Display
            control_center_html = gr.HTML(render_agent_control_center("🟢 Ready", "None", "IDLE", "DEF"))

            # Architecture Component Status
            arch_status_html = gr.HTML(render_architecture_components())

            # Active Workflow Graph Visualizer
            workflow_diagram_md = gr.HTML(render_workflow_diagram("None", "IDLE", ""))

            # Tools Used Badges Display
            tools_used_html = gr.HTML(render_tools_used({}, False, False))

            # Human-in-the-Loop Approval Card
            with gr.Group(visible=False, elem_classes=["approval-card-container"]) as approval_card_box:
                approval_desc_md = gr.Markdown("### ⚠️ HUMAN-IN-THE-LOOP APPROVAL REQUIRED")
                with gr.Row():
                    approve_btn = gr.Button("APPROVE ✅", variant="primary", elem_classes=["btn-primary-custom"])
                    reject_btn = gr.Button("REJECT ❌", variant="stop")

            # Workflow Paused Card
            with gr.Group(visible=False, elem_classes=["paused-card-container"]) as workflow_paused_box:
                workflow_paused_md = gr.Markdown("### ⏸ WORKFLOW PAUSED")

            # Live Activity Timeline Log
            gr.Markdown("#### ⏱️ LIVE EXECUTION TIMELINE")
            activity_timeline_md = gr.Markdown("```\n✓ System initialized. Ready for support requests.\n```")

            # Observability Accordion Panel
            with gr.Accordion("🔍 SYSTEM OBSERVABILITY & TELEMETRY", open=False):
                observability_md = gr.Markdown(build_observability_md("DEF", "None", "IDLE", 0.0, []))

    # Footer
    gr.HTML("""
    <div class="custom-footer">
        <strong>ABC Technologies</strong> • Agentic Enterprise IT Support Assistant | RAG • LangGraph • MCP • Human-in-the-loop • Observability<br/>
        <span style="color: #64748b;">Demo Environment • All enterprise integrations (ServiceNow, AWS, Jira, Outlook) are MOCKED</span>
    </div>
    """)

    # Wire Event Handlers - Exactly 19 Output Components
    send_inputs = [user_input, chatbot, session_id_state]
    send_outputs = [
        chatbot,              # 1
        user_input,           # 2
        control_center_html,  # 3
        arch_status_html,     # 4
        workflow_diagram_md,  # 5
        tools_used_html,      # 6
        activity_timeline_md, # 7
        observability_md,     # 8
        approval_card_box,    # 9
        approval_desc_md,     # 10
        workflow_paused_box,  # 11
        workflow_paused_md,   # 12
        rag_vis_box,          # 13
        rag_info_md,          # 14
        mcp_vis_box,          # 15
        mcp_info_md,          # 16
        session_id_state,     # 17
        agent_status_state,   # 18
        workflow_state_state  # 19
    ]

    # Generator callbacks for Event Handlers using yield from to yield all 19 outputs cleanly
    def handle_user_submit(msg, hist, sess):
        yield from user_submit_message(msg, hist, sess)

    def handle_approve(hist, sess):
        yield from handle_approval_click(True, hist, sess)

    def handle_reject(hist, sess):
        yield from handle_approval_click(False, hist, sess)

    def handle_demo_vpn(hist, sess):
        yield from user_submit_message("What is the VPN policy?", hist, sess)

    def handle_demo_docker(hist, sess):
        yield from user_submit_message("How do I request Docker access?", hist, sess)

    def handle_demo_pwd(hist, sess):
        yield from user_submit_message("I forgot my password.", hist, sess)

    def handle_demo_laptop(hist, sess):
        yield from user_submit_message("My laptop is extremely slow.", hist, sess)

    def handle_demo_ticket(hist, sess):
        yield from user_submit_message("Create a ticket for my VPN issue.", hist, sess)

    # Event Bindings
    user_input.submit(handle_user_submit, inputs=send_inputs, outputs=send_outputs)
    send_btn.click(handle_user_submit, inputs=send_inputs, outputs=send_outputs)

    approve_btn.click(handle_approve, inputs=[chatbot, session_id_state], outputs=send_outputs)
    reject_btn.click(handle_reject, inputs=[chatbot, session_id_state], outputs=send_outputs)

    reset_btn.click(reset_conversation, inputs=[], outputs=send_outputs)

    # Preset Quick Demo Query Event Bindings
    btn_demo1.click(handle_demo_vpn, inputs=[chatbot, session_id_state], outputs=send_outputs)
    btn_demo2.click(handle_demo_docker, inputs=[chatbot, session_id_state], outputs=send_outputs)
    btn_demo3.click(handle_demo_pwd, inputs=[chatbot, session_id_state], outputs=send_outputs)
    btn_demo4.click(handle_demo_laptop, inputs=[chatbot, session_id_state], outputs=send_outputs)
    btn_demo5.click(handle_demo_ticket, inputs=[chatbot, session_id_state], outputs=send_outputs)


if __name__ == "__main__":
    logger.info("Starting ABC Technologies Enterprise Support Dashboard on http://127.0.0.1:7860")
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True, share=False, css=CUSTOM_CSS, show_error=True)
