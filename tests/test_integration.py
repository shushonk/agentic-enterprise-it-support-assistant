import pytest
from main_agent import MainSupportAgent


@pytest.fixture(scope="module")
def agent():
    return MainSupportAgent()


def test_e2e_rag_knowledge_flow(agent):
    stream = list(agent.process_message_stream("What is the VPN policy?", thread_id="e2e_rag"))
    assert len(stream) > 0
    final_log, final_resp, session = stream[-1]
    assert "GlobalProtect" in final_resp or "corporate" in final_resp or "VPN" in final_resp


def test_e2e_direct_action_flow(agent):
    stream = list(agent.process_message_stream("Create an IT ticket for laptop display flicker.", thread_id="e2e_action"))
    assert len(stream) > 0
    final_log, final_resp, session = stream[-1]
    assert "MOCK-JIRA-" in final_resp
    assert "created successfully" in final_resp


def test_e2e_slow_laptop_workflow_flow(agent):
    t_id = "e2e_slow"
    # Step 1: Initial query
    s1 = list(agent.process_message_stream("My laptop is extremely slow.", thread_id=t_id))
    _, resp1, session1 = s1[-1]
    assert "operating system" in resp1.lower()
    assert session1["status"] == "WAITING_FOR_USER"

    # Step 2: User provides OS
    s2 = list(agent.process_message_stream("Windows 11", thread_id=t_id))
    _, resp2, session2 = s2[-1]
    assert "restarted" in resp2.lower()
    assert session2["status"] == "WAITING_FOR_USER"

    # Step 3: User provides restart status
    s3 = list(agent.process_message_stream("Yes", thread_id=t_id))
    _, resp3, session3 = s3[-1]
    assert "troubleshooting" in resp3.lower() or "resolve" in resp3.lower()
    assert session3["status"] == "WAITING_FOR_USER"

    # Step 4: User states unresolved -> Approval state
    s4 = list(agent.process_message_stream("No", thread_id=t_id))
    _, resp4, session4 = s4[-1]
    assert session4["status"] == "WAITING_FOR_APPROVAL"

    # Step 5: Approval action -> Ticket creation
    s5 = list(agent.handle_approval_action(t_id, approved=True))
    _, resp5, session5 = s5[-1]
    assert session5["status"] == "COMPLETED"
    assert "MOCK-SNOW-" in resp5
