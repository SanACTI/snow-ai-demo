# Required Output JSON Schema

The LLM must return exactly this structure. All fields are required.

```json
{
  "incident_summary": "string — 2-3 sentence summary of what happened",
  "root_cause_analysis": "string — confirmed or probable root cause with evidence",
  "prevention_measures": [
    "string — specific action to prevent recurrence"
  ],
  "resolution_recommendations": [
    "string — specific actionable fix recommendation"
  ],
  "automation_monitoring_suggestions": [
    "string — alerting, monitoring, or automation improvement"
  ],
  "confidence_score": "float between 0.0 and 1.0",
  "evidence_used": [
    "string — specific field or fact used in analysis"
  ],
  "missing_information": [
    "string — data that was absent but would have helped"
  ],
  "risk_level": "string — one of: Critical, High, Medium, Low"
}
```