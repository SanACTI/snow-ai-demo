from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from app.validate_input import AgentState
from pathlib import Path
import os
import json

MODEL = os.getenv("MODEL_NAME", "mistral")
BASE_URL = os.getenv("BASE_URL", "http://localhost:11434")
EXEC_PROMPT = Path("prompts/executive_summary_prompt.md").read_text()

def generate_executive_summary(final_response: dict, facts: dict) -> dict:
    llm = ChatOllama(model=MODEL, base_url=BASE_URL, temperature=0)

    user_prompt = f"""
Here is the full RCA analysis:

Incident: {facts.get('incident_number')}
Priority: {facts.get('priority')}
Outage Duration: {facts.get('outage_duration_minutes')} minutes
Impacted Services: {facts.get('impacted_services')}

Incident Summary: {final_response.get('incident_summary')}
Root Cause: {final_response.get('root_cause_analysis')}
Prevention: {final_response.get('prevention_measures')}
Recommendations: {final_response.get('resolution_recommendations')}
Confidence: {final_response.get('confidence_score')}

Now produce the executive summary JSON.
"""
    messages = [
        SystemMessage(content=EXEC_PROMPT),
        HumanMessage(content=user_prompt)
    ]

    response = llm.invoke(messages)
    cleaned = response.content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```json")[-1].split("```")[0].strip()

    try:
        return json.loads(cleaned)
    except Exception:
        return {"error": "Could not generate executive summary", "raw": cleaned}