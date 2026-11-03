from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json
import concurrent.futures
from app.graph import build_graph
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="ServiceNow RCA Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

graph = build_graph()
# Clean up any leftover pending/decision files from previous runs
from pathlib import Path
for f in Path("outputs/pending").glob("*_pending.json") if Path("outputs/pending").exists() else []:
    f.unlink(missing_ok=True)
for f in Path("outputs/decisions").glob("*_decision.json") if Path("outputs/decisions").exists() else []:
    f.unlink(missing_ok=True)
print("[api] 🧹 Cleaned up leftover approval files")
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

results_store = {}

def run_pipeline(raw_json: dict, batch_mode: bool = False):
    import os
    incident_number = raw_json.get("number", "UNKNOWN")
    if batch_mode:
        os.environ["BATCH_MODE"] = "true"
    else:
        os.environ.pop("BATCH_MODE", None)

    config = {"configurable": {"thread_id": incident_number}}
    try:
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
        results_store[incident_number] = {"success": True, "state": final_state}
    except Exception as e:
        results_store[incident_number] = {"success": False, "error": str(e)}
    finally:
        import os as _os
        _os.environ.pop("BATCH_MODE", None)

@app.get("/")
def serve_ui():
    return FileResponse("ui/index.html")

@app.post("/analyze")
async def analyze(file: UploadFile = File(...), batch: bool = False):
    try:
        contents = await file.read()
        raw_json = json.loads(contents)
        incident_number = raw_json.get("number", "UNKNOWN")

        results_store.pop(incident_number, None)

        _executor.submit(run_pipeline, raw_json, batch)

        return {
            "success": True,
            "status": "running",
            "incident_number": incident_number,
            "message": "Pipeline started. Poll /result/{incident_number} for completion."
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/result/{incident_number}")
def get_result(incident_number: str):
    if incident_number not in results_store:
        return {"ready": False, "incident_number": incident_number}

    entry = results_store[incident_number]
    if not entry["success"]:
        return {"ready": True, "success": False, "error": entry["error"]}

    final_state = entry["state"]
    final = final_state.get("final_response", {})
    facts = final_state.get("extracted_facts", {})

    risk = final.get("risk_level", "Unknown") if isinstance(final, dict) else "Unknown"
    risk_str = risk.value if hasattr(risk, "value") else str(risk)

    return {
        "ready": True,
        "success": True,
        "incident_number": incident_number,
        "is_valid": final_state.get("is_valid"),
        "validation_errors": final_state.get("validation_errors", []),
        "validation_warnings": final_state.get("validation_warnings", []),
        "confidence_score": final_state.get("confidence_score", 0.0),
        "cost_estimate": final_state.get("cost_estimate", 0.0),
        "approval_needed": facts.get("priority") in ["P1", "P2"],
        "extracted_facts": {
            "incident_number": facts.get("incident_number"),
            "priority": facts.get("priority"),
            "outage_duration_minutes": facts.get("outage_duration_minutes"),
            "impacted_services": facts.get("impacted_services", []),
            "error_keywords": facts.get("error_keywords", []),
            "has_problem_record": facts.get("has_problem_record"),
            "has_change_record": facts.get("has_change_record"),
            "ci_name": facts.get("ci_name"),
            "assignment_group": facts.get("assignment_group")
        },
        "final_response": {
            "incident_summary": final.get("incident_summary", ""),
            "root_cause_analysis": final.get("root_cause_analysis", ""),
            "prevention_measures": final.get("prevention_measures", []),
            "resolution_recommendations": final.get("resolution_recommendations", []),
            "automation_monitoring_suggestions": final.get("automation_monitoring_suggestions", []),
            "evidence_used": final.get("evidence_used", []),
            "missing_information": final.get("missing_information", []),
            "risk_level": risk_str,
            "confidence_score": final_state.get("confidence_score", 0.0)
        }
    }

@app.get("/batch")
def get_batch_history():
    from pathlib import Path
    import orjson
    results = []
    for f in Path("outputs").glob("*_insight.json"):
        try:
            data = orjson.loads(f.read_bytes())
            facts = data.get("extracted_facts", {})
            final = data.get("final_response", {})
            risk = final.get("risk_level", "Unknown")
            risk_str = risk.value if hasattr(risk, "value") else str(risk)
            results.append({
                "incident_number": data.get("incident_number"),
                "priority": facts.get("priority"),
                "risk_level": risk_str,
                "confidence_score": data.get("confidence_score", 0.0),
                "outage_duration_minutes": facts.get("outage_duration_minutes"),
                "generated_at": data.get("generated_at"),
                "impacted_services": facts.get("impacted_services", [])
            })
        except Exception:
            continue
    return {"results": results}

@app.get("/pending")
def get_pending():
    from pathlib import Path
    import orjson
    pending_dir = Path("outputs/pending")
    pending_dir.mkdir(exist_ok=True)
    pending_files = list(pending_dir.glob("*_pending.json"))
    if not pending_files:
        return {"pending": False}
    try:
        data = orjson.loads(pending_files[0].read_bytes())
        return {"pending": True, "data": data}
    except Exception:
        return {"pending": False}

@app.post("/decide/{incident_number}")
def submit_decision(incident_number: str, action: str, edited_rca: str = ""):
    from pathlib import Path
    import orjson
    from datetime import datetime, timezone
    DECISION_DIR = Path("outputs/decisions")
    DECISION_DIR.mkdir(exist_ok=True)
    decision_path = DECISION_DIR / f"{incident_number}_decision.json"
    decision_path.write_bytes(orjson.dumps({
        "incident_number": incident_number,
        "action": action,
        "edited_rca": edited_rca,
        "decided_at": datetime.now(timezone.utc).isoformat()
    }))
    print(f"[api] Decision submitted: {incident_number} -> {action}")
    return {"success": True, "incident": incident_number, "action": action}

@app.delete("/pending/clear")
def clear_pending():
    from pathlib import Path
    cleared = 0
    for f in Path("outputs/pending").glob("*_pending.json"):
        f.unlink(missing_ok=True)
        cleared += 1
    for f in Path("outputs/decisions").glob("*_decision.json"):
        f.unlink(missing_ok=True)
    return {"cleared": cleared}

@app.get("/result/saved/{incident_number}")
def get_saved_result(incident_number: str):
    from pathlib import Path
    import orjson
    json_path = Path(f"outputs/{incident_number}_insight.json")
    if not json_path.exists():
        return {"found": False}
    try:
        data = orjson.loads(json_path.read_bytes())
        facts = data.get("extracted_facts", {})
        final = data.get("final_response", {})
        risk = final.get("risk_level", "Unknown")
        risk_str = risk.value if hasattr(risk, "value") else str(risk)
        return {
            "found": True,
            "incident_number": data.get("incident_number"),
            "confidence_score": data.get("confidence_score", 0.0),
            "cost_estimate": data.get("cost_estimate", 0.0),
            "validation_warnings": data.get("validation_warnings", []),
            "approval_needed": False,
            "extracted_facts": {
                "incident_number": facts.get("incident_number"),
                "priority": facts.get("priority"),
                "outage_duration_minutes": facts.get("outage_duration_minutes"),
                "impacted_services": facts.get("impacted_services", []),
                "error_keywords": facts.get("error_keywords", []),
                "has_problem_record": facts.get("has_problem_record"),
                "has_change_record": facts.get("has_change_record"),
                "ci_name": facts.get("ci_name"),
                "assignment_group": facts.get("assignment_group")
            },
            "final_response": {
                "incident_summary": final.get("incident_summary", ""),
                "root_cause_analysis": final.get("root_cause_analysis", ""),
                "prevention_measures": final.get("prevention_measures", []),
                "resolution_recommendations": final.get("resolution_recommendations", []),
                "automation_monitoring_suggestions": final.get("automation_monitoring_suggestions", []),
                "evidence_used": final.get("evidence_used", []),
                "missing_information": final.get("missing_information", []),
                "risk_level": risk_str,
                "confidence_score": data.get("confidence_score", 0.0)
            }
        }
    except Exception as e:
        return {"found": False, "error": str(e)}
    
@app.get("/logs/{incident_number}")
def get_node_trace(incident_number: str):
    from pathlib import Path
    import re, json as _json
    log_dir = Path("outputs/logs")
    logs = sorted(log_dir.glob(f"{incident_number}_*.log"), reverse=True)
    if not logs:
        return {"found": False}
    lines = logs[0].read_text(encoding="utf-8", errors="ignore").splitlines()
    nodes = {}
    for line in lines:
        m = re.match(r"(.+?) \| \w+ \| .+? \| \[(.+?)\] (IN|OUT|Starting|Completed.*|Failed.*) ?\|? ?(.*)", line)
        if not m:
            continue
        timestamp, node, direction, payload = m.groups()
        if node not in nodes:
            nodes[node] = {"name": node, "input": None, "output": None, "duration": None, "status": "done", "error": None}
        if direction == "IN":
            try: nodes[node]["input"] = _json.loads(payload)
            except: nodes[node]["input"] = payload
        elif direction == "OUT":
            try: nodes[node]["output"] = _json.loads(payload)
            except: nodes[node]["output"] = payload
        elif direction == "Starting":
            nodes[node]["started"] = timestamp
        elif direction.startswith("Completed"):
            dur = re.search(r"([\d.]+)s", direction + " " + payload)
            if dur: nodes[node]["duration"] = float(dur.group(1))
        elif direction.startswith("Failed"):
            nodes[node]["status"] = "error"
            nodes[node]["error"] = payload
    return {"found": True, "incident": incident_number, "nodes": list(nodes.values())}