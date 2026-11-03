import pytest
from app.chunk_large_text import chunk_large_text, MIN_LENGTH_TO_CHUNK

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

def test_small_text_not_chunked():
    state = make_state({
        "description": "Short description",
        "work_notes": "Brief notes"
    })
    result = chunk_large_text(state)
    assert len(result["chunks"]) == 1

def test_large_text_is_chunked():
    long_text = "This is a repeated sentence about an incident. " * 200
    state = make_state({
        "description": long_text,
        "work_notes": long_text
    })
    result = chunk_large_text(state)
    assert len(result["chunks"]) > 1

def test_empty_fields_handled():
    state = make_state({
        "description": "Only description present"
    })
    result = chunk_large_text(state)
    assert result["chunks"] is not None
    assert len(result["chunks"]) >= 1