# ABC Technologies — Agentic Enterprise IT Support Assistant

A production-style demonstration of a stateful **Agentic Enterprise IT Support Assistant** for **ABC Technologies**, built in Python using **LangGraph**, **ChromaDB**, **SentenceTransformers**, **Ollama**, and **Gradio**.

---

## 1. Project Title
**ABC Technologies — Agentic Enterprise IT Support Assistant**

## 2. Business Problem
Large enterprises handle thousands of internal employee support requests daily. Traditional static IT helpdesk chatbots fail when handling complex multi-step troubleshooting, lack context grounding, cannot pause for human approval, and lack standardized interfaces to external enterprise tools (Jira, ServiceNow, Slack, AWS).

## 3. Business Context
- **Company**: ABC Technologies (Fictional Enterprise)
- **Scale**: ~18,000 employees
- **Daily Support Volume**: ~6,000 daily support requests
- **Objective**: Automate common HR policies, simple IT ticket requests, and multi-step diagnostic workflows without sacrificing safety, grounding, or security.

## 4. System Goals
- **Grounded Knowledge (RAG)**: Zero policy hallucination by strictly constraining answers to ABC Technologies knowledge-base documents.
- **Stateful Multi-Step Workflows (LangGraph)**: Support interactive multi-turn troubleshooting with conditional branching, retry logic, and state persistence across pauses.
- **Standardized System Actions (MCP)**: Use Model Context Protocol (MCP) tool abstractions to interact cleanly with enterprise IT tools (Jira, ServiceNow, Outlook, Slack, AWS).
- **Human-in-the-Loop (HITL)**: Enforce human approval for sensitive operations like incident creation or manager notification.
- **Full Observability**: Structured event logging without persisting sensitive data or credentials.

---

## 5. System Architecture

```
                         EMPLOYEE
                            |
                            v
                   +----------------+
                   |   GRADIO UI    |
                   +--------+-------+
                            |
                            v
                   +----------------+
                   |  AI AGENT      |
                   |    ROUTER      |
                   +--------+-------+
                            |
             +--------------+--------------+
             |              |              |
             v              v              v
        KNOWLEDGE        ACTION        WORKFLOW
             |              |              |
             v              v              v
            RAG        TOOL REGISTRY    LANGGRAPH
             |              |              |
             v              |              v
      GROUNDED ANSWER      |        STATEFUL WORKFLOW
                            |              |
                            +------+-------+
                                   |
                                   v
                          LOCAL MOCK MCP
                                   |
              +--------------------+-------------------+
              |          |          |         |        |
              v          v          v         v        v
            JIRA     SERVICENOW  OUTLOOK   SLACK     AWS
              |          |          |         |        |
              +----------+----------+---------+--------+
                                   |
                                   v
                             MOCK RESULT
                                   |
                                   v
                            FINAL RESPONSE
```

---

## 6. Agent Router
The central agent router (`main_agent.py`) classifies incoming employee inputs into three distinct intents using Pydantic structured output (`RouterDecision`):
- `knowledge`: Policy & how-to questions routed to RAG.
- `action`: Direct simple actions routed to the MCP Tool Registry.
- `workflow`: Multi-step interactive issues routed to LangGraph stateful graphs.

Out-of-scope queries (e.g. weather, sports) are gracefully rejected with a polite enterprise domain restriction message.

## 7. RAG (Retrieval-Augmented Generation)
The local RAG pipeline (`rag_pipeline.py`) loads documents from `docs/`, splits text into 500-character chunks with 50-character overlap, creates dense embeddings, and stores them in ChromaDB.

## 8. Vector Search
Embeddings are computed locally using `sentence-transformers/all-MiniLM-L6-v2` and indexed in ChromaDB (`data/chroma/`). Similarity search retrieves top-k relevant chunks to ground response generation.

## 9. LangGraph Stateful Workflows
Workflows are built using LangGraph `StateGraph` in `langgraph_workflow.py`. The graph maintains state (`SupportState`), allowing workflows to transition between nodes based on telemetry data and user decisions.

## 10. Stateful Workflows Supported
- **Slow Laptop Workflow**: OS collection -> restart verification -> AWS MCP telemetry diagnostic (CPU 92%, Disk 95%) -> troubleshooting recommendation -> resolution check -> approval request -> ServiceNow incident creation -> Slack manager notification.
- **Password Reset Workflow**: Identity verification -> 6-digit mock OTP generation -> OTP entry validation (with 3 retry attempts) -> password reset -> Outlook email confirmation. Escalates to ServiceNow security incident on 3 invalid attempts.
- **VPN Troubleshooting Workflow**: OS collection -> gateway configuration check -> mock diagnostics -> troubleshooting recommendation -> resolution check / Jira ticket logging.

## 11. Conditional Branching & Retry Logic
- Password Reset retries up to 3 invalid OTP attempts before triggering an escalation branch to ServiceNow.
- Slow Laptop branches on whether fixes resolved the problem, triggering Human-in-the-Loop approval if unresolved.

## 12. Model Context Protocol (MCP) Architecture
MCP provides a standardized tool call contract separating agent decision-making from tool implementation specifics. The agent interacts with `call_mcp_tool(tool_name, **kwargs)` rather than direct API implementation code.

## 13. Local Mock MCP Servers
`mock_mcp_servers.py` provides local mock implementations for:
- `JiraMCPServer`: `create_ticket`, `get_ticket`, `update_ticket`
- `ServiceNowMCPServer`: `create_incident`, `get_incident`, `update_incident`
- `OutlookMCPServer`: `send_email`
- `SlackMCPServer`: `send_notification`
- `AWSMCPServer`: `run_diagnostic`

All mock responses are explicitly tagged with `"mock": True`.

## 14. Human-In-The-Loop (HITL)
Sensitive actions (creating incident tickets, sending manager notifications) pause the workflow and request approval. The Gradio UI presents interactive **[ APPROVE ]** and **[ REJECT ]** buttons.

## 15. Suspend and Resume
Each conversation thread maintains session state indexed by `thread_id`. When a workflow pauses (e.g. `WAITING_FOR_USER` or `WAITING_FOR_APPROVAL`), incoming responses resume execution from the exact paused node without restarting from `START`.

## 16. Streaming Execution Updates
The assistant uses Python generators to yield live progress updates to the Gradio activity panel (e.g. `🧠 Classifying request...`, `🔎 Searching knowledge base...`, `📊 CPU usage: 92%`, `🎫 Creating MOCK ServiceNow incident...`).

## 17. Observability & Logging
All events (`REQUEST_RECEIVED`, `ROUTER_DECISION`, `RAG_RETRIEVAL`, `WORKFLOW_STATE_CHANGE`, `MCP_TOOL_CALL`, `APPROVAL_REQUEST`) are logged to `logs/agent.log`. Real credentials and passwords are never logged.

## 18. Security
- Zero external cloud API calls required.
- Standardized tool parameters validation.
- No `eval()` or `exec()` usage.
- All simulated operations are labeled `MOCK`.

## 19. Dummy Knowledge Base Documents
Located in `docs/`:
- `hr_policy.txt`: Hybrid work, code of conduct, performance evaluations.
- `leave_policy.txt`: Annual leave, sick leave, maternity/paternity leave.
- `reimbursement_policy.txt`: Internet allowance, travel expense rules.
- `vpn_guide.txt`: GlobalProtect connection steps and gateways.
- `docker_guide.txt`: Docker Desktop approval workflow and guidelines.
- `software_access.txt`: Software catalog tiers and request procedures.
- `onboarding_guide.txt`: First week checklist and credentials.
- `password_policy.txt`: Password length, expiry, and OTP rules.
- `faq.txt`: Quick IT helpdesk Q&A.

---

## 20. Project Structure

```
enterprise_it_assistant/
│
├── main_agent.py               # Router & Central Support Agent
├── rag_pipeline.py             # ChromaDB & SentenceTransformer RAG Pipeline
├── langgraph_workflow.py       # LangGraph Stateful Workflows & Graph Nodes
├── mock_mcp_servers.py         # Local Mock MCP Servers & Tool Registry
├── app.py                      # Gradio Web Interface
│
├── requirements.txt            # Python Dependencies
├── README.md                   # System Documentation
├── .env.example                # Environment Variable Template
├── .env                        # Active Environment Variables
├── .gitignore                  # Git Ignore File
│
├── docs/                       # Dummy Knowledge Base Text Files
│   ├── hr_policy.txt
│   ├── leave_policy.txt
│   ├── reimbursement_policy.txt
│   ├── vpn_guide.txt
│   ├── docker_guide.txt
│   ├── software_access.txt
│   ├── onboarding_guide.txt
│   ├── password_policy.txt
│   └── faq.txt
│
├── data/                       # Local ChromaDB Persistence
│   └── chroma/
│
├── logs/                       # System Activity Event Logs
│   └── agent.log
│
└── tests/                      # Pytest Suite
    ├── __init__.py
    ├── test_rag.py
    ├── test_mcp.py
    ├── test_workflows.py
    ├── test_router.py
    └── test_integration.py
```

---

## 21. Installation

### Virtual Environment Setup

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 22. Ollama Setup
Install Ollama from [ollama.com](https://ollama.com).

To use the cloud model:
```bash
ollama run gpt-oss:120b-cloud
```

## 23. Model Configuration
Set your model in `.env`:
```env
OLLAMA_MODEL=gpt-oss:120b-cloud
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHROMA_PATH=data/chroma
LOG_PATH=logs/agent.log
REQUIRE_APPROVAL=true
MAX_OTP_ATTEMPTS=3
```

---

## 24. Running RAG Vector Index Initialization
The RAG vector database initializes automatically on first run. To force rebuild:
```python
from rag_pipeline import RAGPipeline
rag = RAGPipeline()
rag.build_vector_store(force_rebuild=True)
```

## 25. Running the Application
Launch the Gradio Web Interface:
```bash
python app.py
```
Open your browser at:
`http://127.0.0.1:7860`

## 26. Running Tests
Run the complete `pytest` test suite:
```bash
python -m pytest -v
```

---

## 27. Demonstration Queries

### DEMO 1 — Knowledge Query (VPN Policy)
- **Input**: `"What is the VPN policy?"`
- **Path**: Router -> `KNOWLEDGE` -> RAG -> `vpn_guide.txt` -> Grounded Response.

### DEMO 2 — Knowledge Query (Docker Access)
- **Input**: `"How can I request Docker access?"`
- **Path**: Router -> `KNOWLEDGE` -> RAG -> `docker_guide.txt` -> Grounded Response.

### DEMO 3 — Password Reset Workflow
- **Input**: `"I forgot my password."`
- **Path**: Router -> `WORKFLOW` -> `password_reset` -> Mock OTP -> User enters OTP -> Password reset + Email confirmation.

### DEMO 4 — Slow Laptop Workflow & Human Approval
- **Input**: `"My laptop is extremely slow."`
- **Path**: Router -> `WORKFLOW` -> `slow_laptop` -> OS collection -> Restart check -> AWS diagnostics -> Troubleshooting -> Unresolved -> Approval prompt -> **[ APPROVE ]** -> ServiceNow incident `MOCK-SNOW-001` + Slack manager notification.

### DEMO 5 — Direct Simple Action
- **Input**: `"Create a ticket for my VPN issue."`
- **Path**: Router -> `ACTION` -> `jira.create_ticket` -> `MOCK-JIRA-001` ticket confirmation.

### DEMO 6 — Out-of-Scope Query Handling
- **Input**: `"What is the weather tomorrow?"`
- **Response**: `"I can help with ABC Technologies HR and IT support requests, but I don't have information about that topic."`

---

## 28. Limitations
- Enterprise tool interactions (Jira, ServiceNow, Slack, AWS) use simulated local mock servers (`"mock": True`).
- OTP verification simulates SMS/MFA messaging for demonstration safety.

## 29. Future Improvements
- Connect real MCP servers over STDIO / SSE transport layers using standard MCP SDK endpoints.
- Integrate active directory SSO identity authorization headers for employee permission checks.
