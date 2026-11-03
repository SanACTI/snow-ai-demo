import json
import argparse
from pathlib import Path
from app.graph import build_graph
from dotenv import load_dotenv
load_dotenv()

def run_single(graph, input_path: Path) -> dict:
    with open(input_path, "r") as f:
        raw_json = json.load(f)

    incident_number = raw_json.get("number", "UNKNOWN")
    print(f"\n{'='*50}")
    print(f"🚀 Processing: {incident_number}")
    print(f"{'='*50}")

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

    return {
        "incident": incident_number,
        "valid": final_state.get("is_valid"),
        "warnings": len(final_state.get("validation_warnings", [])),
        "confidence": final_state.get("confidence_score", 0.0),
        "saved": final_state.get("final_response") is not None
    }

def main():
    parser = argparse.ArgumentParser(description="Batch processor for ServiceNow AI Insight Agent")
    parser.add_argument("--input-dir", default="data", help="Folder containing JSON files")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    json_files = list(input_dir.glob("*.json"))

    if not json_files:
        print(f"❌ No JSON files found in {input_dir}")
        return

    print(f"\n📂 Found {len(json_files)} incidents to process")
    graph = build_graph()
    results = []

    for json_file in json_files:
        try:
            result = run_single(graph, json_file)
            results.append(result)
        except Exception as e:
            print(f"❌ Failed to process {json_file.name}: {e}")
            results.append({"incident": json_file.name, "valid": False, "error": str(e)})

    # Print summary report
    print(f"\n{'='*50}")
    print(f"📊 BATCH SUMMARY")
    print(f"{'='*50}")
    # print(f"{'Incident':<20} {'Valid':<8} {'Warnings':<10} {'Confidence':<12} {'Saved'}")
    print(f"{'Incident':<20} {'Valid':<8} {'Warnings':<10} {'Confidence':<12} {'Cost $':<10} {'Saved'}")
    print(f"{'-'*70}")
    for r in results:
        print(f"{r.get('incident','N/A'):<20} {str(r.get('valid','N/A')):<8} {str(r.get('warnings','N/A')):<10} {str(r.get('confidence','N/A')):<12} {str(r.get('cost','N/A')):<10} {str(r.get('saved','N/A'))}")

    total_cost = sum(r.get('cost', 0.0) for r in results if isinstance(r.get('cost'), float))
    print(f"\n💰 Total estimated cost: ${round(total_cost, 6)}")
    print(f"{'-'*60}")
    for r in results:
        print(f"{r.get('incident','N/A'):<20} {str(r.get('valid','N/A')):<8} {str(r.get('warnings','N/A')):<10} {str(r.get('confidence','N/A')):<12} {str(r.get('saved','N/A'))}")
    print(f"\n✅ Batch complete! {len(results)} incidents processed")

if __name__ == "__main__":
    main()