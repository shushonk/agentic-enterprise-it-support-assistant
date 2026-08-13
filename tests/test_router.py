import pytest
from main_agent import MainSupportAgent


@pytest.fixture(scope="module")
def agent():
    return MainSupportAgent()


def test_knowledge_routing(agent):
    decision1 = agent.classify_intent("What is the VPN policy?")
    assert decision1.intent == "knowledge"

    decision2 = agent.classify_intent("How do I request Docker access?")
    assert decision2.intent == "knowledge"

    decision3 = agent.classify_intent("How many leave days can I take?")
    assert decision3.intent == "knowledge"


def test_action_routing(agent):
    decision = agent.classify_intent("Create a ticket for my VPN issue.")
    assert decision.intent == "action"
    assert decision.action == "jira.create_ticket"


def test_workflow_routing(agent):
    decision1 = agent.classify_intent("My laptop is extremely slow.")
    assert decision1.intent == "workflow"
    assert decision1.workflow == "slow_laptop"

    decision2 = agent.classify_intent("I forgot my password.")
    assert decision2.intent == "workflow"
    assert decision2.workflow == "password_reset"


def test_out_of_scope_routing(agent):
    # Verify streaming stream handles out of scope queries properly
    stream_output = list(agent.process_message_stream("What is the weather tomorrow?", thread_id="test_out_of_scope"))
    final_log, final_resp, state = stream_output[-1]
    assert "I can help with ABC Technologies HR and IT support requests" in final_resp
