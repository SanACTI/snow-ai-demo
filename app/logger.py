import logging
import time
import json
from pathlib import Path
from datetime import datetime, timezone

LOG_DIR = Path("outputs/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logger(incident_number: str) -> logging.Logger:
    logger = logging.getLogger(incident_number)
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    log_file = LOG_DIR / f"{incident_number}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

def log_state(logger: logging.Logger, node_name: str, direction: str, state: dict):
    """Log actual state fields as JSON — input or output of a node."""
    # Only log relevant fields per node, not the entire state
    relevant = {
        "validate_input":   {"in": ["raw_json"], "out": ["is_valid","validation_errors","validation_warnings"]},
        "sanitize_input":   {"in": ["raw_json"], "out": ["sanitized_json"]},
        "extract_facts":    {"in": ["sanitized_json"], "out": ["extracted_facts"]},
        "chunk_large_text": {"in": ["sanitized_json"], "out": ["chunks"]},
        "summarize_chunks": {"in": ["chunks"], "out": ["chunk_summaries"]},
        "generate_insights":{"in": ["extracted_facts","chunk_summaries"], "out": ["rca_draft","cost_estimate"]},
        "validate_output":  {"in": ["rca_draft"], "out": ["final_response","confidence_score"]},
        "save_output":      {"in": ["final_response","confidence_score"], "out": ["final_response"]},
    }
    fields = relevant.get(node_name, {}).get(direction, [])
    snapshot = {}
    for f in fields:
        val = state.get(f)
        if val is not None:
            try:
                # Truncate large values for readability
                serialized = json.dumps(val, default=str)
                if len(serialized) > 800:
                    serialized = serialized[:800] + "... [truncated]"
                snapshot[f] = json.loads(serialized) if len(serialized) < 800 else serialized
            except Exception:
                snapshot[f] = str(val)[:400]
    try:
        logger.info(f"[{node_name}] {direction.upper()} | {json.dumps(snapshot, default=str)}")
    except Exception:
        pass

class NodeTimer:
    def __init__(self, logger: logging.Logger, node_name: str):
        self.logger = logger
        self.node_name = node_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"[{self.node_name}] Starting")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = round(time.time() - self.start_time, 3)
        if exc_type:
            self.logger.error(f"[{self.node_name}] Failed after {duration}s — {exc_val}")
        else:
            self.logger.info(f"[{self.node_name}] Completed in {duration}s")