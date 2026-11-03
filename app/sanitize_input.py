import re
from app.validate_input import AgentState

# --- Patterns to mask ---
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_PATTERN = re.compile(r'\b\d{10}\b|\+\d{1,3}[\s-]?\d{7,12}')

# --- Fields to drop if empty ---
FIELDS_TO_CLEAN = [
    "symptoms", "impacted_services", "root_cause_notes",
    "resolution_notes", "work_notes", "close_notes",
    "related_incidents", "problem_id", "change_id"
]

# --- Helper: clean a string value ---
def clean_text(value: str) -> str:
    value = EMAIL_PATTERN.sub("[EMAIL REDACTED]", value)
    value = PHONE_PATTERN.sub("[PHONE REDACTED]", value)
    value = re.sub(r'<[^>]+>', '', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value

# --- Node Function ---
def sanitize_input(state: AgentState) -> AgentState:
    from app.logger import setup_logger, log_state, NodeTimer
    incident = state.get("raw_json", {}).get("number", "UNKNOWN")
    logger = setup_logger(incident)
    log_state(logger, "sanitize_input", "in", state)
    data = dict(state["raw_json"])
    sanitized = {}

    for key, value in data.items():
        if value is None or value == "" or value == []:
            if key in FIELDS_TO_CLEAN:
                print(f"[sanitize_input] 🗑️  Dropped empty field: {key}")
                continue

        if isinstance(value, str):
            sanitized[key] = clean_text(value)
        elif isinstance(value, list):
            sanitized[key] = [clean_text(v) if isinstance(v, str) else v for v in value]
        else:
            sanitized[key] = value

    print(f"[sanitize_input] ✅ Sanitization complete for {sanitized.get('number')}")
    result = {**state, "sanitized_json": sanitized}
    log_state(logger, "sanitize_input", "out", result)
    return {**state, "sanitized_json": sanitized}