# Executive Summary Prompt

Based on the RCA analysis below, produce a concise executive summary.
Respond ONLY with a valid JSON object, no markdown backticks.

Required fields:
{
  "what_happened": "1 sentence — what went wrong",
  "business_impact": "1 sentence — impact on users/revenue/operations",
  "likely_cause": "1 sentence — root cause in plain language",
  "what_we_did": "1 sentence — how it was resolved",
  "next_steps": "1 sentence — what happens next",
  "automation_opportunity": "1 sentence — what can be automated"
}

Rules:
- No technical jargon — this is for leadership
- Maximum 2 lines per field
- Be direct and factual