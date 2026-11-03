from datetime import datetime
from app.validate_input import AgentState

# --- Keywords to look for ---
ERROR_KEYWORDS = [
    "timeout", "connection refused", "out of memory", "OOM",
    "null pointer", "stack overflow", "disk full", "CPU spike",
    "latency", "degraded", "unavailable", "crashed", "exception",
    "pool exhausted", "deadlock", "failed", "error", "critical"
]

# --- Node Function ---
def extract_facts(state: AgentState) -> AgentState:
    from app.logger import setup_logger, log_state, NodeTimer
    incident = state.get("raw_json", {}).get("number", "UNKNOWN")
    logger = setup_logger(incident)
    log_state(logger, "extract_facts", "in", state)
    data = state["sanitized_json"]
    facts = {}

    # Basic identity
    facts["incident_number"] = data.get("number")
    facts["incident_type"] = data.get("type")
    facts["priority"] = data.get("priority")
    facts["assignment_group"] = data.get("assignment_group")
    facts["ci_name"] = data.get("ci_name")
    facts["impacted_services"] = data.get("impacted_services", [])

    # Outage duration
    opened_at = data.get("opened_at")
    resolved_at = data.get("resolved_at")
    if opened_at and resolved_at:
        try:
            opened = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
            resolved = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
            duration_mins = int((resolved - opened).total_seconds() / 60)
            facts["outage_duration_minutes"] = duration_mins
            print(f"[extract_facts] ⏱️  Outage duration: {duration_mins} mins")
        except Exception as e:
            facts["outage_duration_minutes"] = None
            print(f"[extract_facts] ⚠️  Could not calculate duration: {e}")
    else:
        facts["outage_duration_minutes"] = None

    # Error keywords
    search_text = " ".join(filter(None, [
        data.get("short_description", ""),
        data.get("description", ""),
        data.get("symptoms", ""),
        data.get("work_notes", "")
    ])).lower()

    facts["error_keywords"] = [kw for kw in ERROR_KEYWORDS if kw.lower() in search_text]
    print(f"[extract_facts] 🔍 Error keywords found: {facts['error_keywords']}")

    # Linked records
    facts["has_problem_record"] = bool(data.get("problem_id"))
    facts["has_change_record"] = bool(data.get("change_id"))
    facts["related_incidents"] = data.get("related_incidents", [])

    # Data quality
    facts["missing_recommended_fields"] = state.get("validation_warnings", [])

    print(f"[extract_facts] ✅ Facts extracted for {facts['incident_number']}")
    result = {**state, "extracted_facts": facts}
    log_state(logger, "extract_facts", "out", result)
    return {**state, "extracted_facts": facts}