import pytest
from app.validate_input import validate_input, AgentState

# --- Base valid state ---
def make_state(overrides={}):
    base = {
        "raw_json": {
            "number": "INC0099999",
            "type": "incident",
            "short_description": "Test incident",
            "description": "This is a test description",
            "priority": "P2",
            "symptoms": "slow response",
            "impacted_services": ["test-service"],
            "opened_at": "2026-05-01T10:00:00Z",
            "resolved_at": "2026-05-01T11:00:00Z",
            "assignment_group": "Test Team",
            "ci_name": "test-ci",
            "root_cause_notes": "Test root cause",
            "resolution_notes": "Test resolution",
            "work_notes": "Test work notes",
            "close_notes": "Test close notes",
            "related_incidents": [],
            "problem_id": None,
            "change_id": None
        },
        "sanitized_json": None,
        "extracted_facts": None,
        "chunks": None,
        "chunk_summaries": None,
        "rca_draft": None,
        "final_response": None,
        "validation_errors": [],
        "validation_warnings": [],
        "is_valid": False,
        "cost_estimate": 0.0,
        "confidence_score": 0.0
    }
    base.update(overrides)
    return base

# --- Tests ---
def test_valid_incident_passes():
    state = make_state()
    result = validate_input(state)
    assert result["is_valid"] == True
    assert result["validation_errors"] == []

def test_missing_required_field_fails():
    state = make_state()
    del state["raw_json"]["priority"]
    result = validate_input(state)
    assert result["is_valid"] == False
    assert any("priority" in e for e in result["validation_errors"])

def test_missing_multiple_required_fields():
    state = make_state()
    del state["raw_json"]["number"]
    del state["raw_json"]["description"]
    result = validate_input(state)
    assert result["is_valid"] == False
    assert len(result["validation_errors"]) == 2

def test_missing_recommended_field_gives_warning():
    state = make_state()
    state["raw_json"]["symptoms"] = None
    result = validate_input(state)
    assert result["is_valid"] == True
    assert any("symptoms" in w for w in result["validation_warnings"])

def test_empty_required_field_fails():
    state = make_state()
    state["raw_json"]["short_description"] = ""
    result = validate_input(state)
    assert result["is_valid"] == False