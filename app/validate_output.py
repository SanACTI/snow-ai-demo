import json
from pydantic import ValidationError
from app.validate_input import AgentState
from app.output_schema import RCAOutput

def validate_output(state: AgentState) -> AgentState:
    from app.logger import setup_logger, log_state, NodeTimer
    incident = state.get("raw_json", {}).get("number", "UNKNOWN")
    logger = setup_logger(incident)
    log_state(logger, "validate_output", "in", state)

    rca_draft = state.get("rca_draft", "")

    if not rca_draft:
        print(f"[validate_output] ❌ No RCA draft found")
        return {**state, "final_response": None, "confidence_score": 0.0}

    # Once LLM is connected, rca_draft will be a JSON string
    # For now handle the placeholder case
    if "PENDING LLM OUTPUT" in rca_draft:
        print(f"[validate_output] ⏭️  LLM pending, skipping schema validation")
        return {
            **state,
            "final_response": {"raw_draft": rca_draft, "status": "pending_llm"},
            "confidence_score": 0.0
        }

    # --- This runs once LLM is connected ---
    try:
        parsed = json.loads(rca_draft)
        validated = RCAOutput(**parsed)
        print(f"[validate_output] ✅ Output validated successfully")
        print(f"[validate_output] 🎯 Confidence: {validated.confidence_score}")
        return {
            **state,
            "final_response": validated.model_dump(),
            "confidence_score": validated.confidence_score
        }
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"[validate_output] ❌ Validation failed: {e}")

        result = {**state, "final_response": None, "confidence_score": 0.0}
        log_state(logger, "validate_output", "out", result)
        # LLM repair attempt will go here
        return {
            **state,
            "final_response": None,
            "confidence_score": 0.0
        }