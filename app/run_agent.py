import json
import argparse
from pathlib import Path
from app.graph import build_graph
from dotenv import load_dotenv
load_dotenv()

def main():
    # --- Argument parser ---
    parser = argparse.ArgumentParser(description="ServiceNow AI Insight Agent")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=False, help="Output folder (default: outputs/)")
    args = parser.parse_args()

    # --- Load input JSON ---
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        return

    with open(input_path, "r") as f:
        raw_json = json.load(f)

    incident_number = raw_json.get("number", "UNKNOWN")
    print(f"\n🚀 Starting pipeline for: {incident_number}\n")

    # --- Build and run graph ---
    graph = build_graph()

    # thread_id lets checkpointer track this specific run
    config = {"configurable": {"thread_id": incident_number}}

    final_state = graph.invoke(
        {
            "raw_json": raw_json,
            "sanitized_json": None,
            "extracted_facts": None,
            "chunks": None,
            "chunk_summaries": None,
            "rca_draft": None,
            "final_response": None,
            "validation_errors": [],
            "validation_warnings": [],
            "is_valid": False,
            "cost_estimate": 0.0,
            "confidence_score": 0.0
        },
        config=config
    )

    print(f"\n✅ Pipeline complete!")
    print(f"   Incident     : {final_state['extracted_facts'].get('incident_number') if final_state.get('extracted_facts') else 'N/A'}")
    print(f"   Valid        : {final_state.get('is_valid')}")
    print(f"   Warnings     : {len(final_state.get('validation_warnings', []))}")
    print(f"   Output saved : outputs/")

if __name__ == "__main__":
    main()