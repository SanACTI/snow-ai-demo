import pytest
from app.extract_facts import extract_facts

def make_state(sanitized_json):
    return {
        "raw_json": {},
        "sanitized_json": sanitized_json,
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

def test_outage_duration_calculated():
    state = make_state({
        "number": "INC001",
        "type": "incident",
        "priority": "P1",
        "opened_at": "2026-05-01T10:00:00Z",
        "resolved_at": "2026-05-01T11:00:00Z",
        "description": "Test"
    })
    result = extract_facts(state)
    assert result["extracted_facts"]["outage_duration_minutes"] == 60

def test_error_keywords_detected():
    state = make_state({
        "number": "INC001",
        "type": "incident",
        "priority": "P1",
        "description": "Server timeout and connection refused errors detected"
    })
    result = extract_facts(state)
    keywords = result["extracted_facts"]["error_keywords"]
    assert "timeout" in keywords
    assert "connection refused" in keywords

def test_no_keywords_when_clean_description():
    state = make_state({
        "number": "INC001",
        "type": "incident",
        "priority": "P3",
        "description": "Routine maintenance completed successfully"
    })
    result = extract_facts(state)
    assert result["extracted_facts"]["error_keywords"] == []

def test_linked_records_detected():
    state = make_state({
        "number": "INC001",
        "type": "incident",
        "priority": "P1",
        "description": "Test",
        "problem_id": "PRB001",
        "change_id": "CHG001"
    })
    result = extract_facts(state)
    assert result["extracted_facts"]["has_problem_record"] == True
    assert result["extracted_facts"]["has_change_record"] == True

def test_missing_timestamps_gives_none_duration():
    state = make_state({
        "number": "INC001",
        "type": "incident",
        "priority": "P2",
        "description": "Test",
        "opened_at": None,
        "resolved_at": None
    })
    result = extract_facts(state)
    assert result["extracted_facts"]["outage_duration_minutes"] is None