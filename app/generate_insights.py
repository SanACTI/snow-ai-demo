from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from app.validate_input import AgentState
from app.token_guard import (
    build_full_prompt, check_and_route,
    truncate_prompt, count_tokens
)
from pathlib import Path
import os
import json
import time

# --- Model setup ---
MODEL = os.getenv("MODEL_NAME", "mistral")
BASE_URL = os.getenv("BASE_URL", "http://localhost:11434")
PROMPT_VERSION = "v1"
MAX_RETRIES = 3
RETRY_DELAY = 2

# --- Load prompts ---
SYSTEM_PROMPT = Path("prompts/system_prompt.md").read_text()
OUTPUT_SCHEMA = Path("prompts/output_schema.md").read_text()
USER_TEMPLATE = Path("prompts/user_prompt_template.md").read_text()

def generate_insights(state: AgentState) -> AgentState:
    from app.logger import setup_logger, log_state, NodeTimer
    incident = state.get("raw_json", {}).get("number", "UNKNOWN")
    logger = setup_logger(incident)
    log_state(logger, "generate_insights", "in", state)

    facts = state.get("extracted_facts", {})
    summaries = state.get("chunk_summaries", [])
    sanitized = state.get("sanitized_json", {})
    warnings = state.get("validation_warnings", [])

    # --- Cache check ---
    from app.cache import get_cache_key, get_cached_response, save_to_cache, init_cache
    init_cache()
    cache_key = get_cache_key(sanitized, PROMPT_VERSION)
    cached = get_cached_response(cache_key)
    if cached:
        print(f"[generate_insights] ✅ Cache hit, skipping LLM call")
        return {**state, "rca_draft": json.dumps(cached)}

    # --- Build prompt ---
    user_prompt = build_full_prompt(facts, summaries, warnings, USER_TEMPLATE, OUTPUT_SCHEMA)

    # --- Token guard check ---
    routing = check_and_route(user_prompt, facts)
    action = routing["action"]
    cost_estimate = routing["cost_estimate"]

    # Handle routing decisions
    if action == "batch_required":
        print(f"[generate_insights] 🔴 Routed to batch — skipping LLM call")
        fallback = json.dumps({
            "incident_summary": f"{facts.get('incident_number')} routed to batch queue due to payload size.",
            "root_cause_analysis": "Root cause analysis deferred — payload too large for online processing.",
            "prevention_measures": ["Process via batch queue for full analysis."],
            "resolution_recommendations": ["Resubmit via run_batch.py for full analysis."],
            "automation_monitoring_suggestions": ["Consider payload size limits in ingestion pipeline."],
            "confidence_score": 0.0,
            "evidence_used": [],
            "missing_information": ["Full analysis deferred to batch"],
            "risk_level": "High"
        })
        return {**state, "rca_draft": fallback, "cost_estimate": 0.0}

    elif action == "truncate_and_send":
        print(f"[generate_insights] ✂️  Truncating prompt for P1/P2")
        user_prompt = truncate_prompt(user_prompt)

    elif action == "summarize_first":
        print(f"[generate_insights] 📝 Summarizing work notes before sending")
        # Compress the summaries further
        combined = "\n\n".join(summaries)
        user_prompt = build_full_prompt(
            facts,
            [combined[:2000]],  # hard cap summaries
            warnings,
            USER_TEMPLATE,
            OUTPUT_SCHEMA
        )
        # Recount after compression
        new_count = count_tokens(user_prompt)
        print(f"[generate_insights] 📊 Compressed to {new_count} tokens")

    # --- Retry loop ---
    llm = ChatOllama(model=MODEL, base_url=BASE_URL, temperature=0)
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[generate_insights] 🤖 Calling Mistral for {facts.get('incident_number')}... (attempt {attempt}/{MAX_RETRIES})")
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]
            response = llm.invoke(messages)
            rca_draft = response.content

            # Strip markdown backticks
            cleaned_draft = rca_draft.strip()
            if cleaned_draft.startswith("```"):
                cleaned_draft = cleaned_draft.split("```json")[-1].split("```")[0].strip()

            print(f"[generate_insights] ✅ Insights generated")
            print(f"[generate_insights] 📄 Raw response:\n{rca_draft}")

            # Save to cache
            try:
                save_to_cache(
                    cache_key,
                    facts.get("incident_number", "UNKNOWN"),
                    PROMPT_VERSION,
                    json.loads(cleaned_draft)
                )
                print(f"[generate_insights] 💾 Cached response")
            except Exception:
                print(f"[generate_insights] ⚠️  Could not cache response")

            return {**state, "rca_draft": cleaned_draft, "cost_estimate": cost_estimate}

        except Exception as e:
            last_error = e
            print(f"[generate_insights] ❌ Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                print(f"[generate_insights] ⏳ Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)

    # --- All retries failed ---
    print(f"[generate_insights] ❌ All {MAX_RETRIES} attempts failed. Using fallback.")
    fallback = json.dumps({
        "incident_summary": f"Analysis failed for {facts.get('incident_number')} after {MAX_RETRIES} attempts.",
        "root_cause_analysis": "Root cause unconfirmed - LLM unavailable during analysis.",
        "prevention_measures": ["Manual investigation required."],
        "resolution_recommendations": ["Please retry when LLM service is available."],
        "automation_monitoring_suggestions": ["Monitor LLM service availability."],
        "confidence_score": 0.0,
        "evidence_used": [],
        "missing_information": ["LLM response unavailable"],
        "risk_level": "High"
    })
    result = {**state, "rca_draft": fallback, "cost_estimate": 0.0}
    log_state(logger, "generate_insights", "out", result)
    
    return {**state, "rca_draft": fallback, "cost_estimate": 0.0}