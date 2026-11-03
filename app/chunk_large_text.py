from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.validate_input import AgentState

# --- Thresholds ---
CHUNK_SIZE = 3000       # characters per chunk
CHUNK_OVERLAP = 300     # overlap between chunks
MIN_LENGTH_TO_CHUNK = 3000  # only chunk if text is longer than this

# --- Node Function ---
def chunk_large_text(state: AgentState) -> AgentState:
    from app.logger import setup_logger, log_state, NodeTimer
    incident = state.get("raw_json", {}).get("number", "UNKNOWN")
    logger = setup_logger(incident)
    log_state(logger, "chunk_large_text", "in", state)
    data = state["sanitized_json"]

    # Combine the large text fields
    full_text = " ".join(filter(None, [
        data.get("description", ""),
        data.get("symptoms", ""),
        data.get("work_notes", ""),
        data.get("root_cause_notes", ""),
        data.get("resolution_notes", ""),
        data.get("close_notes", "")
    ]))

    # Skip chunking if text is small enough
    if len(full_text) <= MIN_LENGTH_TO_CHUNK:
        print(f"[chunk_large_text] ⏭️  Text small enough, skipping chunking ({len(full_text)} chars)")
        return {**state, "chunks": [full_text]}

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_text(full_text)
    print(f"[chunk_large_text] ✂️  Split into {len(chunks)} chunks")
    result = {**state, "chunks": chunks}
    log_state(logger, "chunk_large_text", "out", result)
    return {**state, "chunks": chunks}