import os
import re
import copy
import logging
from typing import Dict, Any, Generator, Optional, Tuple, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from rag_pipeline import RAGPipeline
from mock_mcp_servers import call_mcp_tool
from langgraph_workflow import (
    SLOW_LAPTOP_APP,
    PASSWORD_RESET_APP,
    VPN_WORKFLOW_APP,
    get_or_create_session,
    reset_session,
    _WORKFLOW_SESSIONS,
    SupportState
)

load_dotenv()

# Setup logging
LOG_PATH = os.getenv("LOG_PATH", "logs/agent.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logger = logging.getLogger("ABCAgent")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_PATH)
file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"))
if not logger.handlers:
    logger.addHandler(file_handler)


class RouterDecision(BaseModel):
    intent: Literal["knowledge", "action", "workflow"]
    workflow: Optional[str] = None
    action: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


def is_valid_workflow_input(waiting_for: Optional[str], user_input: str) -> bool:
    """
    Determine if user_input is intended as valid input for the current workflow step,
    or if it represents a brand-new support request that should be re-routed.
    """
    if not waiting_for or not user_input or not user_input.strip():
        return False
    
    text = user_input.strip().lower()
    
    # Phrases that strongly indicate a NEW support request rather than workflow continuation
    new_req_phrases = [
        "laptop is extremely slow", "laptop slow", "computer slow", "pc slow", "system slow",
        "forgot my password", "forgot password", "reset my password", "reset password",
        "create a ticket", "create ticket", "create an it ticket", "create an incident",
        "vpn policy", "docker access", "leave days", "reimbursement", "onboarding", "policy",
        "what is", "how do i", "how can i", "vpn is not working", "vpn issue"
    ]

    # 1. OTP Validation Step (Password Reset)
    if waiting_for == "otp":
        has_digits = bool(re.search(r'\b\d{4,8}\b', text)) or bool(re.search(r'^\d[\d\s\-]{3,8}\d$', text))
        has_new_req = any(phrase in text for phrase in new_req_phrases) and not ("otp" in text or "code" in text)
        if has_digits and not has_new_req:
            return True
        return False

    # Pure digits belong to OTP validation, not OS or Yes/No answers
    if text.isdigit():
        return False

    # 2. Operating System Step (Slow Laptop / VPN)
    elif waiting_for in ["operating_system", "vpn_os"]:
        os_keywords = ["windows", "win", "mac", "macos", "linux", "ubuntu", "apple", "win11", "win10"]
        has_os = any(kw in text for kw in os_keywords)
        has_new_req = any(phrase in text for phrase in new_req_phrases)
        if has_os and not has_new_req:
            return True
        if len(text) < 20 and not has_new_req and text.isalpha():
            return True
        return False

    # 3. Restart / Resolution / Approval Step
    elif waiting_for in ["restart_status", "resolution_status", "vpn_resolution", "approval"]:
        yesno_keywords = ["yes", "y", "no", "n", "restarted", "did", "done", "fixed", "resolved", "approve", "reject"]
        has_yesno = any(kw in text for kw in yesno_keywords)
        has_new_req = any(phrase in text for phrase in new_req_phrases)
        if has_yesno and not has_new_req:
            return True
        if len(text) < 15 and not has_new_req and text.isalpha():
            return True
        return False

    return False


class MainSupportAgent:
    def __init__(self, ollama_model: str = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")):
        self.ollama_model = ollama_model
        logger.info(f"Initializing MainSupportAgent with model: {self.ollama_model}")
        
        # Initialize RAG Pipeline
        self.rag_pipeline = RAGPipeline(ollama_model=self.ollama_model)
        self.rag_pipeline.build_vector_store()

    def classify_intent(self, user_input: str) -> RouterDecision:
        """Classify incoming user query into knowledge, action, or workflow intent."""
        text = user_input.strip().lower()

        # Direct Action Matching (Takes precedence over general topic keywords)
        if text.startswith("create a ticket") or text.startswith("create ticket") or text.startswith("create an it ticket") or text.startswith("create an incident") or "create a ticket for" in text or "create a jira ticket" in text:
            return RouterDecision(intent="action", action="jira.create_ticket", confidence=0.95)

        # Deterministic Workflow Intent Matching
        if any(w in text for w in ["laptop is extremely slow", "laptop slow", "computer slow", "pc slow", "system slow", "laptop freezing", "laptop hanging"]):
            return RouterDecision(intent="workflow", workflow="slow_laptop", confidence=0.98)
        
        if any(w in text for w in ["forgot my password", "forgot password", "reset my password", "reset password", "change password", "account locked"]):
            return RouterDecision(intent="workflow", workflow="password_reset", confidence=0.98)
            
        if any(w in text for w in ["vpn is not working", "vpn not working", "vpn issue", "vpn fails", "cannot connect to vpn", "vpn connection issue"]) and not ("policy" in text or "what is" in text or "guide" in text):
            return RouterDecision(intent="workflow", workflow="vpn_troubleshooting", confidence=0.95)

        if any(w in text for w in ["vpn policy", "docker access", "leave days", "reimbursement", "onboarding", "policy", "how do i", "how can i", "what is"]):
            return RouterDecision(intent="knowledge", confidence=0.95)

        # Attempt structured Ollama LLM intent classification if available
        try:
            from langchain_ollama import OllamaLLM
            llm = OllamaLLM(model=self.ollama_model, timeout=5)
            prompt = (
                "Classify the following user query for an IT support assistant.\n"
                "Intents: 'knowledge' (for policy/how-to questions), 'action' (direct ticket/email creation), 'workflow' (multi-step issue resolution like slow laptop, password reset, vpn issue).\n"
                "Query: " + user_input + "\n"
                "Respond ONLY in JSON format: {\"intent\": \"...\", \"workflow\": \"...\", \"confidence\": 0.95}"
            )
            res = llm.invoke(prompt)
            if "knowledge" in res.lower():
                return RouterDecision(intent="knowledge", confidence=0.90)
            elif "action" in res.lower():
                return RouterDecision(intent="action", action="jira.create_ticket", confidence=0.90)
            elif "password" in res.lower():
                return RouterDecision(intent="workflow", workflow="password_reset", confidence=0.95)
            elif "slow" in res.lower():
                return RouterDecision(intent="workflow", workflow="slow_laptop", confidence=0.95)
        except Exception as e:
            logger.debug(f"LLM router fallback used due to: {e}")

        # Out-of-scope fallback detection
        out_of_scope_topics = ["weather", "sports", "recipe", "joke", "movie", "president", "stock"]
        if any(topic in text for topic in out_of_scope_topics):
            return RouterDecision(intent="knowledge", confidence=0.10)

        # Default fallback to knowledge search
        return RouterDecision(intent="knowledge", confidence=0.80)

    def process_message_stream(
        self,
        user_input: str,
        thread_id: str = "default_session"
    ) -> Generator[Tuple[str, str, Dict[str, Any]], None, None]:
        """
        Process incoming user message with streaming execution updates.
        Yields tuples of: (activity_log_text, response_text, state_dict)
        """
        logger.info(f"REQUEST_RECEIVED [thread_id={thread_id}]: {user_input}")
        session = get_or_create_session(thread_id)

        w_name = session.get("workflow")
        waiting_for = session.get("waiting_for")
        status = session.get("status")
        cur_suspended = copy.deepcopy(session.get("suspended_workflows", {}))

        # 1. Check if user input is valid for any SUSPENDED password_reset workflow waiting for OTP
        if "password_reset" in cur_suspended and is_valid_workflow_input("otp", user_input):
            logger.info(f"WORKFLOW_RESTORED_FROM_SUSPENDED [thread_id={thread_id}] workflow=password_reset")
            saved_pwd = cur_suspended.pop("password_reset")
            
            # If current active workflow was waiting for something else, suspend it
            if status in ["WAITING_FOR_USER", "WAITING_FOR_APPROVAL"] and w_name and w_name != "password_reset":
                saved_active = copy.deepcopy(dict(session))
                saved_active.pop("suspended_workflows", None)
                cur_suspended[w_name] = saved_active

            session.clear()
            session.update(saved_pwd)
            session["suspended_workflows"] = cur_suspended
            session["user_request"] = user_input
            
            yield "🔑 Resuming suspended password reset workflow with OTP...", "Checking OTP...", session

            updated_state = PASSWORD_RESET_APP.invoke(session)
            updated_state["suspended_workflows"] = cur_suspended
            _WORKFLOW_SESSIONS[thread_id] = updated_state
            logs = "\n".join(updated_state.get("messages", []))
            logger.info(f"WORKFLOW_STATE_CHANGE [thread_id={thread_id}] status={updated_state.get('status')}")
            yield logs, updated_state.get("final_response", ""), updated_state
            return

        # 2. Check if user input is valid for the ACTIVE workflow step
        if status in ["WAITING_FOR_USER", "WAITING_FOR_APPROVAL"] and is_valid_workflow_input(waiting_for, user_input):
            logger.info(f"WORKFLOW_RESUMED [thread_id={thread_id}] waiting_for={waiting_for}")
            yield f"▶️ Resuming active workflow ({w_name})...", "Processing your input...", session
            
            if w_name == "slow_laptop":
                if waiting_for == "operating_system":
                    session["operating_system"] = user_input
                    yield "💻 OS registered: " + user_input, "Processing...", session
                elif waiting_for == "restart_status":
                    restarted = True if any(w in user_input.lower() for w in ["yes", "y", "restarted", "did"]) else False
                    session["restarted"] = restarted
                    yield "🔄 Restart status recorded.", "Processing...", session
                elif waiting_for == "resolution_status":
                    resolved = True if any(w in user_input.lower() for w in ["yes", "y", "fixed", "resolved"]) else False
                    session["resolved"] = resolved
                    yield ("✅ Resolution confirmed." if resolved else "⚠️ Issue unresolved."), "Processing...", session
                elif waiting_for == "approval":
                    approved = True if "approve" in user_input.lower() else False
                    session["approved"] = approved
                    yield ("👍 Approval granted." if approved else "👎 Approval rejected."), "Processing...", session

                updated_state = SLOW_LAPTOP_APP.invoke(session)
                updated_state["suspended_workflows"] = cur_suspended
                _WORKFLOW_SESSIONS[thread_id] = updated_state
                logs = "\n".join(updated_state.get("messages", []))
                logger.info(f"WORKFLOW_STATE_CHANGE [thread_id={thread_id}] status={updated_state.get('status')}")
                yield logs, updated_state.get("final_response", ""), updated_state
                return

            elif w_name == "password_reset":
                if waiting_for == "otp":
                    session["user_request"] = user_input
                    yield "🔑 Validating OTP entry...", "Checking OTP...", session
                
                updated_state = PASSWORD_RESET_APP.invoke(session)
                updated_state["suspended_workflows"] = cur_suspended
                _WORKFLOW_SESSIONS[thread_id] = updated_state
                logs = "\n".join(updated_state.get("messages", []))
                logger.info(f"WORKFLOW_STATE_CHANGE [thread_id={thread_id}] status={updated_state.get('status')}")
                yield logs, updated_state.get("final_response", ""), updated_state
                return

            elif w_name == "vpn_troubleshooting":
                if waiting_for == "vpn_os":
                    session["operating_system"] = user_input
                elif waiting_for == "vpn_resolution":
                    session["resolved"] = True if "yes" in user_input.lower() else False
                
                updated_state = VPN_WORKFLOW_APP.invoke(session)
                updated_state["suspended_workflows"] = cur_suspended
                _WORKFLOW_SESSIONS[thread_id] = updated_state
                logs = "\n".join(updated_state.get("messages", []))
                yield logs, updated_state.get("final_response", ""), updated_state
                return

        # 3. If active workflow existed but user message was NOT valid input for it -> SUSPEND active workflow
        if status in ["WAITING_FOR_USER", "WAITING_FOR_APPROVAL"] and w_name:
            logger.info(f"WORKFLOW_SUSPENDED [thread_id={thread_id}] workflow={w_name}")
            saved_copy = copy.deepcopy(dict(session))
            saved_copy.pop("suspended_workflows", None)
            cur_suspended[w_name] = saved_copy
            session["suspended_workflows"] = cur_suspended
            yield f"⏸ Suspended workflow '{w_name}' to process new request...", "Routing new request...", session

        # Handle Out-of-Scope / Non-IT Questions
        out_of_scope_topics = ["weather", "sports", "recipe", "joke", "movie", "president", "stock", "tomorrow"]
        if any(topic in user_input.lower() for topic in out_of_scope_topics) and not any(k in user_input.lower() for k in ["vpn", "leave", "docker", "policy", "ticket", "password", "laptop"]):
            logger.info("OUT_OF_SCOPE_QUERY")
            out_resp = "I can help with ABC Technologies HR and IT support requests, but I don't have information about that topic."
            yield "ℹ️ Query out of scope.", out_resp, session
            return

        # Standard Intent Routing (New Request)
        yield "🧠 Classifying request...", "Analyzing request...", session
        decision = self.classify_intent(user_input)
        logger.info(f"ROUTER_DECISION: intent={decision.intent}, workflow={decision.workflow}, confidence={decision.confidence}")

        if decision.intent == "knowledge":
            yield "🔎 Searching ABC Technologies knowledge base...", "Retrieving policy documents...", session
            docs = self.rag_pipeline.retrieve_context(user_input, top_k=3)
            yield f"📚 Retrieved {len(docs)} relevant policy document chunks...", "Generating grounded answer...", session
            
            grounded_ans = self.rag_pipeline.generate_grounded_response(user_input, docs)
            logger.info("RAG_RESPONSE generated successfully.")
            yield f"✅ Knowledge response generated from {len(docs)} documents.", grounded_ans, session
            return

        elif decision.intent == "action":
            yield "⚡ Direct Action detected. Calling MCP Tool Registry...", "Executing ticket action...", session
            tool_res = call_mcp_tool(
                "jira.create_ticket",
                summary=user_input,
                description=f"Action requested via AI Assistant: {user_input}"
            )
            ticket_id = tool_res.get("ticket_id", "MOCK-JIRA-001")
            ans = f"Your mock Jira ticket **{ticket_id}** has been created successfully."
            logger.info(f"MCP_TOOL_CALL jira.create_ticket -> {ticket_id}")
            yield f"🎫 MOCK-JIRA Tool Executed -> Ticket ID: {ticket_id}", ans, session
            return

        elif decision.intent == "workflow":
            new_w_name = decision.workflow or "slow_laptop"
            yield f"🔄 Launching stateful LangGraph workflow: '{new_w_name}'...", "Initializing workflow...", session

            session.clear()
            session.update({
                "user_request": user_input,
                "workflow": new_w_name,
                "messages": [f"🚀 Workflow '{new_w_name}' initialized."],
                "suspended_workflows": cur_suspended,
                "status": "RUNNING"
            })

            if new_w_name == "slow_laptop":
                updated_state = SLOW_LAPTOP_APP.invoke(session)
            elif new_w_name == "password_reset":
                updated_state = PASSWORD_RESET_APP.invoke(session)
            elif new_w_name == "vpn_troubleshooting":
                updated_state = VPN_WORKFLOW_APP.invoke(session)
            else:
                updated_state = SLOW_LAPTOP_APP.invoke(session)

            updated_state["suspended_workflows"] = cur_suspended
            _WORKFLOW_SESSIONS[thread_id] = updated_state
            logs = "\n".join(updated_state.get("messages", []))
            logger.info(f"WORKFLOW_STATE_CHANGE status={updated_state.get('status')}")
            yield logs, updated_state.get("final_response", ""), updated_state
            return

    def handle_approval_action(self, thread_id: str, approved: bool) -> Generator[Tuple[str, str, Dict[str, Any]], None, None]:
        """Handle Approve/Reject button clicks from Gradio UI."""
        logger.info(f"APPROVAL_RESULT [thread_id={thread_id}] approved={approved}")
        session = get_or_create_session(thread_id)
        cur_suspended = copy.deepcopy(session.get("suspended_workflows", {}))
        session["approved"] = approved
        session["waiting_for"] = None
        session["approval_required"] = False

        yield ("👍 Approval granted. Continuing workflow..." if approved else "👎 Approval rejected."), "Processing...", session
        
        w_name = session.get("workflow", "slow_laptop")
        if w_name == "slow_laptop":
            updated_state = SLOW_LAPTOP_APP.invoke(session)
        else:
            updated_state = SLOW_LAPTOP_APP.invoke(session)

        updated_state["suspended_workflows"] = cur_suspended
        _WORKFLOW_SESSIONS[thread_id] = updated_state
        logs = "\n".join(updated_state.get("messages", []))
        yield logs, updated_state.get("final_response", ""), updated_state

    def reset_thread(self, thread_id: str):
        """Reset a conversation session thread."""
        logger.info(f"THREAD_RESET [thread_id={thread_id}]")
        reset_session(thread_id)
