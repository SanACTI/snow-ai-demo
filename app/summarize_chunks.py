from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from app.validate_input import AgentState
import os

# --- Model setup ---
CHEAP_MODEL = os.getenv("CHEAP_MODEL_NAME", "mistral")
BASE_URL = os.getenv("BASE_URL", "http://localhost:11434")

# --- Prompt ---
SUMMARIZE_SYSTEM_PROMPT = """You are a technical assistant. 
Summarize the following incident text into key points only.
Extract: symptoms, errors, timestamps, actions taken, suspected causes.
Be concise. Do not invent anything not present in the text."""

# --- Node Function ---
def summarize_chunks(state: AgentState) -> AgentState:
    from app.logger import setup_logger, log_state, NodeTimer
    incident = state.get("raw_json", {}).get("number", "UNKNOWN")
    logger = setup_logger(incident)
    log_state(logger, "summarize_chunks", "in", state)
    chunks = state.get("chunks", [])

    if len(chunks) <= 1:
        print(f"[summarize_chunks] ⏭️  Single chunk, skipping summarization")
        return {**state, "chunk_summaries": chunks}

    llm = ChatOllama(model=CHEAP_MODEL, base_url=BASE_URL, temperature=0)
    summaries = []

    for i, chunk in enumerate(chunks):
        print(f"[summarize_chunks] 🔄 Summarizing chunk {i+1}/{len(chunks)}...")
        messages = [
            SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT),
            HumanMessage(content=f"Summarize this incident text:\n\n{chunk}")
        ]
        response = llm.invoke(messages)
        summaries.append(response.content)
        print(f"[summarize_chunks] ✅ Chunk {i+1} summarized")

    result = {**state, "chunk_summaries": summaries}
    log_state(logger, "summarize_chunks", "out", result)    

    return {**state, "chunk_summaries": summaries}