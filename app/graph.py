from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.validate_input import AgentState, validate_input
from app.sanitize_input import sanitize_input
from app.extract_facts import extract_facts
from app.chunk_large_text import chunk_large_text
from app.summarize_chunks import summarize_chunks
from app.generate_insights import generate_insights
from app.validate_output import validate_output
from app.save_output import save_output

def should_continue(state: AgentState) -> str:
    if not state.get("is_valid"):
        print("[graph] ❌ Validation failed, stopping pipeline")
        return "stop"
    return "continue"

def needs_approval(state: AgentState) -> str:
    import os
    priority = state.get("extracted_facts", {}).get("priority", "")
    if priority in ["P1", "P2"] and os.getenv("BATCH_MODE") != "true":
        print(f"[graph] ⏸️  P1/P2 detected — human approval required")
        return "needs_approval"
    print(f"[graph] ✅ Auto-approving (batch mode or P3/P4)")
    return "auto_approve"

def human_approval(state: AgentState) -> AgentState:
    import time
    import orjson
    from pathlib import Path

    facts = state.get("extracted_facts", {})
    final = state.get("final_response", {})
    incident = facts.get("incident_number", "Unknown")
    confidence = state.get("confidence_score", 0.0)
    risk = final.get("risk_level", "Unknown") if isinstance(final, dict) else "Unknown"
    risk_str = risk.value if hasattr(risk, "value") else str(risk)

    print(f"[human_approval] ⏸️  Waiting for UI approval: {incident}")

    PENDING_DIR = Path("outputs/pending")
    PENDING_DIR.mkdir(exist_ok=True)
    pending_path = PENDING_DIR / f"{incident}_pending.json"
    pending_path.write_bytes(orjson.dumps({
        "incident_number": incident,
        "priority": facts.get("priority"),
        "confidence_score": confidence,
        "risk_level": risk_str,
        "incident_summary": final.get("incident_summary", "") if isinstance(final, dict) else "",
        "root_cause_analysis": final.get("root_cause_analysis", "") if isinstance(final, dict) else "",
        "status": "pending"
    }, option=orjson.OPT_INDENT_2))

    DECISION_DIR = Path("outputs/decisions")
    DECISION_DIR.mkdir(exist_ok=True)
    decision_path = DECISION_DIR / f"{incident}_decision.json"

    if decision_path.exists():
        decision_path.unlink()

    print(f"[human_approval] ⏳ Waiting for reviewer decision in UI...")
    timeout = 300
    start = time.time()

    while time.time() - start < timeout:
        if decision_path.exists():
            try:
                decision = orjson.loads(decision_path.read_bytes())
                action = decision.get("action", "rejected")
                print(f"[human_approval] ✅ Decision received: {action}")
                pending_path.unlink(missing_ok=True)
                decision_path.unlink(missing_ok=True)
                updated_final = dict(final) if isinstance(final, dict) else {}
                if decision.get("edited_rca"):
                    updated_final["root_cause_analysis"] = decision["edited_rca"]
                updated_final["approval_status"] = action
                return {**state, "final_response": updated_final}
            except Exception as e:
                print(f"[human_approval] ⚠️  Error reading decision: {e}")
        time.sleep(1)

    print(f"[human_approval] ⏰ Approval timeout — auto rejected")
    pending_path.unlink(missing_ok=True)
    final_dict = dict(final) if isinstance(final, dict) else {}
    final_dict["approval_status"] = "timeout"
    return {**state, "final_response": final_dict}

def should_save(state: AgentState) -> str:
    final = state.get("final_response", {})
    if isinstance(final, dict) and final.get("approval_status") == "rejected":
        print(f"[graph] ❌ Output rejected, skipping save")
        return "skip"
    return "save"

def build_graph():
    checkpointer = MemorySaver()
    graph = StateGraph(AgentState)

    graph.add_node("validate_input", validate_input)
    graph.add_node("sanitize_input", sanitize_input)
    graph.add_node("extract_facts", extract_facts)
    graph.add_node("chunk_large_text", chunk_large_text)
    graph.add_node("summarize_chunks", summarize_chunks)
    graph.add_node("generate_insights", generate_insights)
    graph.add_node("validate_output", validate_output)
    graph.add_node("human_approval", human_approval)
    graph.add_node("save_output", save_output)

    graph.set_entry_point("validate_input")

    graph.add_conditional_edges(
        "validate_input",
        should_continue,
        {"continue": "sanitize_input", "stop": END}
    )

    graph.add_edge("sanitize_input", "extract_facts")
    graph.add_edge("extract_facts", "chunk_large_text")
    graph.add_edge("chunk_large_text", "summarize_chunks")
    graph.add_edge("summarize_chunks", "generate_insights")
    graph.add_edge("generate_insights", "validate_output")

    graph.add_conditional_edges(
        "validate_output",
        needs_approval,
        {
            "needs_approval": "human_approval",
            "auto_approve": "save_output"
        }
    )

    graph.add_conditional_edges(
        "human_approval",
        should_save,
        {"save": "save_output", "skip": END}
    )

    graph.add_edge("save_output", END)

    return graph.compile(checkpointer=checkpointer)

def save_graph_image():
    app = build_graph()
    png_bytes = app.get_graph().draw_mermaid_png()
    with open("outputs/graph_diagram.png", "wb") as f:
        f.write(png_bytes)
    print("✅ Graph diagram saved to outputs/graph_diagram.png")

if __name__ == "__main__":
    save_graph_image()
