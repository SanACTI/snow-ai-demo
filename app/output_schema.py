from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class RiskLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class RCAOutput(BaseModel):
    incident_summary: str = Field(..., description="2-3 sentence summary of what happened")
    root_cause_analysis: str = Field(..., description="Confirmed or probable root cause with evidence")
    prevention_measures: List[str] = Field(..., description="Specific actions to prevent recurrence")
    resolution_recommendations: List[str] = Field(..., description="Specific actionable fix recommendations")
    automation_monitoring_suggestions: List[str] = Field(..., description="Alerting, monitoring, automation improvements")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in analysis 0.0 to 1.0")
    evidence_used: List[str] = Field(..., description="Specific fields or facts used in analysis")
    missing_information: List[str] = Field(..., description="Data absent but would have helped")
    risk_level: RiskLevel = Field(..., description="Critical, High, Medium, or Low")