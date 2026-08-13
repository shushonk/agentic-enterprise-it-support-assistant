import pytest
from langgraph_workflow import (
    SLOW_LAPTOP_APP,
    PASSWORD_RESET_APP,
    VPN_WORKFLOW_APP,
    get_or_create_session,
    reset_session
)


def test_password_reset_workflow_success():
    thread_id = "test_pwd_success"
    reset_session(thread_id)
    session = get_or_create_session(thread_id)

    # Step 1: Initial state & generate OTP
    state1 = PASSWORD_RESET_APP.invoke(session)
    assert state1["workflow"] == "password_reset"
    assert state1["status"] == "WAITING_FOR_USER"
    assert state1["waiting_for"] == "otp"
    assert state1["otp"] is not None

    otp = state1["otp"]

    # Step 2: User inputs valid OTP
    state1["user_request"] = otp
    state2 = PASSWORD_RESET_APP.invoke(state1)
    assert state2["identity_verified"] is True
    assert state2["status"] == "COMPLETED"
    assert "reset successfully" in state2["final_response"]


def test_password_reset_invalid_otp_retry_and_escalation():
    thread_id = "test_pwd_escalate"
    reset_session(thread_id)
    session = get_or_create_session(thread_id)

    # Step 1: Initial trigger
    state = PASSWORD_RESET_APP.invoke(session)
    
    # Attempt 1: Invalid OTP
    state["user_request"] = "000000"
    state = PASSWORD_RESET_APP.invoke(state)
    assert state["identity_verified"] is False
    assert state["otp_attempts"] == 1
    assert state["status"] == "WAITING_FOR_USER"

    # Attempt 2: Invalid OTP
    state["user_request"] = "111111"
    state = PASSWORD_RESET_APP.invoke(state)
    assert state["identity_verified"] is False
    assert state["otp_attempts"] == 2
    assert state["status"] == "WAITING_FOR_USER"

    # Attempt 3: Invalid OTP -> Escalation to ServiceNow
    state["user_request"] = "222222"
    state = PASSWORD_RESET_APP.invoke(state)
    assert state["identity_verified"] is False
    assert state["otp_attempts"] == 3
    assert state["status"] == "COMPLETED"
    assert state["ticket_id"].startswith("MOCK-SNOW-")
    assert "exceeded the maximum allowed OTP attempts" in state["final_response"]


def test_slow_laptop_workflow_resolved():
    thread_id = "test_slow_resolved"
    reset_session(thread_id)
    session = get_or_create_session(thread_id)

    # Step 1: Init -> ask OS
    state = SLOW_LAPTOP_APP.invoke(session)
    assert state["waiting_for"] == "operating_system"

    # Step 2: Provide OS -> ask Restart
    state["operating_system"] = "Windows 11"
    state = SLOW_LAPTOP_APP.invoke(state)
    assert state["waiting_for"] == "restart_status"

    # Step 3: Provide Restart -> Run Diag -> Suggest fixes -> Ask resolution
    state["restarted"] = True
    state = SLOW_LAPTOP_APP.invoke(state)
    assert state["waiting_for"] == "resolution_status"
    assert state["diagnostic_result"] is not None

    # Step 4: Confirm issue resolved -> COMPLETED
    state["resolved"] = True
    state = SLOW_LAPTOP_APP.invoke(state)
    assert state["status"] == "COMPLETED"
    assert "issue is resolved" in state["final_response"]


def test_slow_laptop_workflow_unresolved_approval_granted():
    thread_id = "test_slow_approval_yes"
    reset_session(thread_id)
    session = get_or_create_session(thread_id)

    state = SLOW_LAPTOP_APP.invoke(session)
    state["operating_system"] = "macOS Sequoia"
    state = SLOW_LAPTOP_APP.invoke(state)
    state["restarted"] = True
    state = SLOW_LAPTOP_APP.invoke(state)
    
    # User states unresolved -> requires approval
    state["resolved"] = False
    state = SLOW_LAPTOP_APP.invoke(state)
    assert state["status"] == "WAITING_FOR_APPROVAL"
    assert state["approval_required"] is True

    # User approves ticket creation
    state["approved"] = True
    state = SLOW_LAPTOP_APP.invoke(state)
    assert state["status"] == "COMPLETED"
    assert state["ticket_id"].startswith("MOCK-SNOW-")
    assert state["notification_status"] == "sent"


def test_slow_laptop_workflow_approval_rejected():
    thread_id = "test_slow_approval_no"
    reset_session(thread_id)
    session = get_or_create_session(thread_id)

    state = SLOW_LAPTOP_APP.invoke(session)
    state["operating_system"] = "Linux Ubuntu"
    state = SLOW_LAPTOP_APP.invoke(state)
    state["restarted"] = False
    state = SLOW_LAPTOP_APP.invoke(state)
    state["resolved"] = False
    state = SLOW_LAPTOP_APP.invoke(state)

    # User rejects ticket creation
    state["approved"] = False
    state = SLOW_LAPTOP_APP.invoke(state)
    assert state["status"] == "COMPLETED"
    assert state.get("ticket_id") is None
    assert "rejected" in state["final_response"]
