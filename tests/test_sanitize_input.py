import pytest
from app.validate_input import AgentState
from app.sanitize_input import sanitize_input

def make_state(raw_json):
    return {
        "raw_json": raw_json,
        "sanitized_json": None,
        "extracted_facts": None,
        "chunks": None,
        "chunk_summaries": None,
        "rca_draft": None,
        "final_response": None,
        "validation_errors": [],
        "validation_warnings": [],
        "is_valid": True,
        "cost_estimate": 0.0,
        "confidence_score": 0.0
    }

def test_email_is_masked():
    state = make_state({
        "number": "INC001",
        "description": "Contact john.doe@company.com for details",
        "priority": "P2"
    })
    result = sanitize_input(state)
    assert "john.doe@company.com" not in result["sanitized_json"]["description"]
    assert "[EMAIL REDACTED]" in result["sanitized_json"]["description"]

def test_html_is_stripped():
    state = make_state({
        "number": "INC001",
        "description": "<p>Server is <b>down</b></p>",
        "priority": "P2"
    })
    result = sanitize_input(state)
    assert "<p>" not in result["sanitized_json"]["description"]
    assert "Server is down" in result["sanitized_json"]["description"]

def test_empty_optional_fields_dropped():
    state = make_state({
        "number": "INC001",
        "description": "Test",
        "priority": "P2",
        "symptoms": "",
        "work_notes": None
    })
    result = sanitize_input(state)
    assert "symptoms" not in result["sanitized_json"]
    assert "work_notes" not in result["sanitized_json"]

def test_required_fields_kept_even_if_empty():
    state = make_state({
        "number": "INC001",
        "description": "Test",
        "priority": "P2"
    })
    result = sanitize_input(state)
    assert "number" in result["sanitized_json"]
    assert "priority" in result["sanitized_json"]