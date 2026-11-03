# User Prompt Template

Analyze the following ServiceNow incident and produce a structured RCA report.

## Extracted Facts
{extracted_facts}

## Incident Text Summaries
{chunk_summaries}

## Validation Warnings (missing recommended fields)
{validation_warnings}

## Instructions
- Use only the facts above
- Follow the output JSON schema exactly
- If root cause cannot be confirmed from the data, say so explicitly
- Confidence score should reflect how complete the input data was:
  - 0.9+ = all fields present, clear root cause
  - 0.7-0.9 = most fields present, probable root cause
  - 0.5-0.7 = some fields missing, uncertain root cause
  - below 0.5 = major data gaps, analysis is speculative
- Risk level should reflect priority + outage duration + impacted services
