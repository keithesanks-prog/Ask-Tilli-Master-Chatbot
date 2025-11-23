"""
Data models for assessment data structures.
These are placeholders until actual database schemas are provided.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class EMTRecord(BaseModel):
    """Placeholder model for Emotion Matching Task data."""
    student_id: str
    assessment_date: datetime
    emotion_score: float = Field(..., description="Emotion matching score")
    # TODO: Add actual EMT fields once schema is provided
    metadata: Dict[str, Any] = Field(default_factory=dict)


class REALRecord(BaseModel):
    """Placeholder model for Remote Learning Assessment data."""
    student_id: str
    assessment_date: datetime
    learning_score: float = Field(..., description="Remote learning assessment score")
    # TODO: Add actual REAL fields once schema is provided
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SELRecord(BaseModel):
    """Placeholder model for SEL Assignment data."""
    student_id: str
    assessment_date: datetime
    assignment_id: Optional[str] = None
    # Core SEL competencies
    self_awareness: Optional[float] = None
    self_management: Optional[float] = None
    social_awareness: Optional[float] = None
    relationship_skills: Optional[float] = None
    responsible_decision_making: Optional[float] = None
    # General SEL score/observations
    sel_score: Optional[float] = None
    observations: Optional[str] = None
    # TODO: Add actual SEL Data fields once schema is provided
    metadata: Dict[str, Any] = Field(default_factory=dict)



class AggregatedAssessmentData(BaseModel):
    """
    Model for aggregated assessment data (from CSV export).
    Represents class-level summaries rather than individual student records.
    """
    summary: Dict[str, Any] = Field(..., description="Overall summary (total students, etc.)")
    metrics: Dict[str, Any] = Field(..., description="Per-metric comparison (pre, post, delta)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssessmentDataSet(BaseModel):
    """Container for assessment data from multiple sources.
    
    Based on the Master Agent architecture:
    - REAL Data: Remote Learning Assessment results
    - EMT Data: Emotion Matching Task results
    - SEL Data: Social-Emotional Learning assignment results
    - Aggregated Data: Class-level summaries from CSV exports
    """
    emt_data: List[EMTRecord] = Field(default_factory=list)
    real_data: List[REALRecord] = Field(default_factory=list)
    sel_data: List[SELRecord] = Field(default_factory=list)
    aggregated_data: Optional[AggregatedAssessmentData] = Field(None, description="Aggregated class-level data")

