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

# Custom CSS disabled - UI rendered using default native Python Gradio components


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
    return "SYSTEM: Operational | LLM ROUTER: Active | RAG: ChromaDB Ready | LANGGRAPH: Ready | MCP: Mock Servers Ready"


def render_agent_control_center(status_badge: str, workflow_name: str, state_status: str, session_id: str):
    return f"**Agent Status:** {status_badge}\n**Active Workflow:** {workflow_name}\n**Workflow State:** {state_status}\n**Session ID:** REQ-{session_id.upper()}"


def render_architecture_components():
    return "**ARCHITECTURE COMPONENTS**\n- LLM Intent Router: ACTIVE\n- ChromaDB Vector RAG: READY\n- LangGraph State Machine: ACTIVE\n- Mock MCP Tools Server: READY\n- Observability Engine: ACTIVE"


def render_tools_used(state_dict: dict, is_rag: bool, is_action: bool):
    tools = []
    if is_rag:
        tools.append('ChromaDB RAG Retrieval')
    
    wf = state_dict.get("workflow")
    if wf:
        tools.append(f'LangGraph ({wf})')
    
    if state_dict.get("diagnostic_result"):
        tools.append('MOCK AWS Diagnostic')
    
    if state_dict.get("ticket_id"):
        t_id = state_dict.get("ticket_id", "")
        if "SNOW" in t_id:
            tools.append('MOCK ServiceNow Incident')
        elif "JIRA" in t_id:
            tools.append('MOCK Jira Ticket')

    if state_dict.get("notification_status"):
        tools.append('MOCK Outlook Email')

    if is_action and not tools:
        tools.append('MOCK Jira Action')

    if not tools:
        tools_str = "*No external tools invoked yet*"
    else:
        tools_str = ", ".join(tools)

    return f"**TOOLS USED (ENTERPRISE MOCK REGISTRY)**\n{tools_str}"


def render_workflow_diagram(workflow_name: str, state_status: str, waiting_for: str):
    if not workflow_name or workflow_name == "None":
        return "**WORKFLOW GRAPH: IDLE**\nNo active LangGraph workflow currently running. Select a workflow query to visualize graph execution."

    if workflow_name == "slow_laptop":
        s1 = "✓"
        s2 = "✓" if waiting_for not in ["operating_system"] else "⏳"
        s3 = "✓" if waiting_for not in ["operating_system", "restart_status"] else ("⏳" if waiting_for == "restart_status" else "○")
        s4 = "✓" if state_status in ["WAITING_FOR_APPROVAL", "COMPLETED"] else ("⏳" if state_status == "RUNNING" else "○")
        s5 = "✓" if state_status == "COMPLETED" else ("⚠️" if state_status == "WAITING_FOR_APPROVAL" else "○")

        return f"**WORKFLOW: SLOW LAPTOP (LANGGRAPH)**\n- {s1} 1. Request Classified\n- {s2} 2. Collect Operating System\n- {s3} 3. Check Laptop Restart Status\n- {s4} 4. Run AWS Diagnostics (MOCK)\n- {s5} 5. Human Approval & Incident Creation (MOCK)"
    elif workflow_name == "password_reset":
        s1 = "✓"
        s2 = "⏳" if waiting_for == "otp" else "✓"
        s3 = "✓" if state_status == "COMPLETED" else "○"
        return f"**WORKFLOW: PASSWORD RESET (LANGGRAPH)**\n- {s1} 1. Account Identity Identification\n- {s2} 2. OTP Security Challenge\n- {s3} 3. Password Reset & Notification"
    else:
        return f"**WORKFLOW: {workflow_name.upper()}**\nStatus: {state_status}"


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
            render_agent_control_center("🟢 Ready", "None", "IDLE", session_id or "DEF"), # 3. control_center_md
            render_architecture_components(),                                # 4. arch_status_md
            render_workflow_diagram("None", "IDLE", ""),                     # 5. workflow_diagram_md
            render_tools_used({}, False, False),                            # 6. tools_used_md
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

            ctrl_md = render_agent_control_center(status_badge, wf_name, state_status, session_id)
            activity_md = build_activity_timeline(state_dict.get("messages", []), state_status, exec_time, log_step)
            arch_md = render_architecture_components()
            tools_md = render_tools_used(state_dict, is_rag, is_action)
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
                ctrl_md,               # 3. control_center_md
                arch_md,               # 4. arch_status_md
                workflow_diagram_md,     # 5. workflow_diagram_md
                tools_md,              # 6. tools_used_md
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
            ctrl_md = render_agent_control_center(status_badge, wf_name, state_status, session_id)
            activity_md = build_activity_timeline(state_dict.get("messages", []), state_status, exec_time, log_step)
            arch_md = render_architecture_components()
            tools_md = render_tools_used(state_dict, False, True)
            workflow_diagram_md = render_workflow_diagram(wf_name, state_status, "")

            invoked_tools = ["LangGraph", "ServiceNow Incident MOCK"]
            observability_md = build_observability_md(session_id, wf_name, state_status, exec_time, invoked_tools)

            # ALWAYS YIELD EXACTLY 19 OUTPUT VALUES MATCHING send_outputs
            yield (
                updated_history,
                "",
                ctrl_md,
                arch_md,
                workflow_diagram_md,
                tools_md,
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
        render_agent_control_center("🟢 Ready", "None", "IDLE", new_session_id), # 3. control_center_md
        render_architecture_components(),                                   # 4. arch_status_md
        render_workflow_diagram("None", "IDLE", ""),                        # 5. workflow_diagram_md
        render_tools_used({}, False, False),                               # 6. tools_used_md
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
    with gr.Row():
        with gr.Column(scale=4):
            gr.Markdown("## 🏢 ABC TECHNOLOGIES | Enterprise AI Support Assistant\nAgentic IT & HR Automation powered by LLM Router + ChromaDB RAG + LangGraph + Mock MCP")
        with gr.Column(scale=1):
            gr.Markdown("**System Operational**")

    # Top Status Indicators Bar
    gr.Markdown(render_top_status_bar())

    # Main Two-Column Dashboard Layout
    with gr.Row():
        # LEFT COLUMN (~68% width): Support Chat & Visualizers
        with gr.Column(scale=7):
            gr.Markdown("### 💬 AI Support Chat Window")
            
            chatbot = gr.Chatbot(
                value=DEFAULT_CHAT_HISTORY,
                label="Support Assistant Chat",
                height=520
            )

            # Input Area
            with gr.Row():
                user_input = gr.Textbox(
                    placeholder="Describe your IT or HR support request (e.g. 'What is the VPN policy?', 'My laptop is extremely slow', 'I forgot my password')...",
                    label="Employee Input",
                    scale=5,
                    lines=1
                )
                send_btn = gr.Button("SEND 🚀", variant="primary", scale=1)
                reset_btn = gr.Button("CLEAR 🔄", variant="secondary", scale=1)

            # Quick Demo Buttons
            gr.Markdown("#### 💡 QUICK DEMO SCENARIOS")
            with gr.Row():
                btn_demo1 = gr.Button("🔐 VPN Policy")
                btn_demo2 = gr.Button("🐳 Docker Access")
                btn_demo3 = gr.Button("🔑 Password Reset")
                btn_demo4 = gr.Button("💻 Slow Laptop")
                btn_demo5 = gr.Button("🎫 Create Ticket")

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
            control_center_md = gr.Markdown(render_agent_control_center("🟢 Ready", "None", "IDLE", "DEF"))

            # Architecture Component Status
            arch_status_md = gr.Markdown(render_architecture_components())

            # Active Workflow Graph Visualizer
            workflow_diagram_md = gr.Markdown(render_workflow_diagram("None", "IDLE", ""))

            # Tools Used Badges Display
            tools_used_md = gr.Markdown(render_tools_used({}, False, False))

            # Human-in-the-Loop Approval Card
            with gr.Group(visible=False) as approval_card_box:
                approval_desc_md = gr.Markdown("### ⚠️ HUMAN-IN-THE-LOOP APPROVAL REQUIRED")
                with gr.Row():
                    approve_btn = gr.Button("APPROVE ✅", variant="primary")
                    reject_btn = gr.Button("REJECT ❌", variant="stop")

            # Workflow Paused Card
            with gr.Group(visible=False) as workflow_paused_box:
                workflow_paused_md = gr.Markdown("### ⏸ WORKFLOW PAUSED")

            # Live Activity Timeline Log
            gr.Markdown("#### ⏱️ LIVE EXECUTION TIMELINE")
            activity_timeline_md = gr.Markdown("```\n✓ System initialized. Ready for support requests.\n```")

            # Observability Accordion Panel
            with gr.Accordion("🔍 SYSTEM OBSERVABILITY & TELEMETRY", open=False):
                observability_md = gr.Markdown(build_observability_md("DEF", "None", "IDLE", 0.0, []))

    # Footer
    gr.Markdown("**ABC Technologies** • Agentic Enterprise IT Support Assistant | RAG • LangGraph • MCP • Human-in-the-loop • Observability\n*Demo Environment • All enterprise integrations (ServiceNow, AWS, Jira, Outlook) are MOCKED*")

    # Wire Event Handlers - Exactly 19 Output Components
    send_inputs = [user_input, chatbot, session_id_state]
    send_outputs = [
        chatbot,              # 1
        user_input,           # 2
        control_center_md,    # 3
        arch_status_md,       # 4
        workflow_diagram_md,  # 5
        tools_used_md,        # 6
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
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True, share=False, show_error=True)
