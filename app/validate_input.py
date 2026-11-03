from typing import TypedDict, List, Optional

# --- State Definition ---
class AgentState(TypedDict):
    raw_json: dict                          
    sanitized_json: Optional[dict]          # cleaned version
    extracted_facts: Optional[dict]         # facts pulled by extract_facts node
    chunks: Optional[List[str]]             # text split into chunks if too large
    chunk_summaries: Optional[List[str]]    # summaries of each chunk
    rca_draft: Optional[str]                # intermediate LLM draft
    final_response: Optional[dict]          # final structured output
    validation_errors: Optional[List[str]]  # hard errors (required fields missing)
    validation_warnings: Optional[List[str]]# soft warnings (recommended fields missing)
    is_valid: bool                          # did validation pass?
    cost_estimate: Optional[float]          # estimated token cost
    confidence_score: Optional[float]       # LLM confidence in its output

# --- Required Fields (hard fail if missing) ---
REQUIRED_FIELDS = [
    "number",
    "type",
    "short_description",
    "description",
    "priority"
]

# --- Recommended Fields (warn if missing, but continue) ---
RECOMMENDED_FIELDS = [
    "symptoms",
    "impacted_services",
    "opened_at",
    "resolved_at",
    "assignment_group",
    "ci_name",
    "root_cause_notes",
    "resolution_notes",
    "work_notes",
    "close_notes",
    "related_incidents",
    "problem_id",
    "change_id"
]

# --- Node Function ---
def validate_input(state: AgentState) -> AgentState:
    from app.logger import setup_logger, log_state, NodeTimer
    incident = state.get("raw_json", {}).get("number", "UNKNOWN")
    logger = setup_logger(incident)
    log_state(logger, "validate_input", "in", state)  # log input
    errors = []
    warnings = []
    data = state["raw_json"]

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")

    # Check recommended fields
    for field in RECOMMENDED_FIELDS:
        if field not in data or not data[field]:
            warnings.append(f"Missing recommended field: {field}")

    # Log results
    if errors:
        print(f"[validate_input] ❌ Validation failed: {errors}")
        return {
            **state,
            "is_valid": False,
            "validation_errors": errors,
            "validation_warnings": warnings
        }

    if warnings:
        print(f"[validate_input] ⚠️  Warnings (missing recommended fields): {warnings}")

    print(f"[validate_input] ✅ Validation passed for {data.get('number')}")

    result = {**state, "is_valid": True, "validation_errors": [], "validation_warnings": warnings}
    log_state(logger, "validate_input", "out", result)  # log output
    return {
        **state,
        "is_valid": True,
        "validation_errors": [],
        "validation_warnings": warnings
    }