"""
Data Router Service

Determines which assessment data tables are needed based on educator questions.
Uses keyword matching as a placeholder for more sophisticated NLP in the future.
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
import re
import os

from ..models.data_models import AssessmentDataSet, EMTRecord, REALRecord, SELRecord, AggregatedAssessmentData
from . import csv_data


class DataRouter:
    """
    Routes educator questions to appropriate data sources.
    
    This is a placeholder implementation using keyword matching.
    TODO: Replace with more sophisticated NLP/ML-based routing once requirements are clearer.
    """
    
    # Keyword mappings for data source identification
    # Based on the Master Agent architecture: REAL, EMT, and SEL Data
    EMT_KEYWORDS = [
        "emotion", "emotion matching", "emt", "emotions", "emotional", "matching task",
        "emotion recognition", "feeling recognition", "emotion assignment"
    ]
    
    REAL_KEYWORDS = [
        "remote learning", "real", "distance learning", "online learning",
        "remote assessment", "learning assessment", "academic performance", 
        "real evaluation", "real assessment"
    ]
    
    SEL_KEYWORDS = [
        "sel", "social emotional", "social-emotional", "sel assignment", "sel assessment",
        "self-awareness", "self-management", "social awareness",
        "relationship skills", "responsible decision", "sel skills", "sel data"
    ]
    
    def __init__(self):
        """Initialize the data router."""
        # Allow temporarily disabling sources via environment variable.
        # Example: DISABLE_SOURCES="EMT,REAL"
        disabled = os.getenv("DISABLE_SOURCES", "")
        self.disabled_sources = {s.strip().upper() for s in disabled.split(",") if s.strip()}
    
    def determine_data_sources(self, question: str) -> List[str]:
        """
        Determine which data sources are needed based on the question.
        
        This implements the Data Router / Table Selector from the Master Agent architecture.
        
        Args:
            question: Natural language question from educator
            
        Returns:
            List of data source identifiers (e.g., ["EMT", "SEL", "REAL"])
        """
        question_lower = question.lower()
        sources = []
        
        # Check for EMT keywords
        if "EMT" not in self.disabled_sources and any(keyword in question_lower for keyword in self.EMT_KEYWORDS):
            sources.append("EMT")
        
        # Check for REAL keywords
        if "REAL" not in self.disabled_sources and any(keyword in question_lower for keyword in self.REAL_KEYWORDS):
            sources.append("REAL")
        
        # Check for SEL keywords
        if "SEL" not in self.disabled_sources and any(keyword in question_lower for keyword in self.SEL_KEYWORDS):
            sources.append("SEL")
        
        # Default: if no specific source is identified, include all sources
        if not sources:
            # Very general question - include all three data sources
            sources = [s for s in ["EMT", "REAL", "SEL"] if s not in self.disabled_sources]
        
        return list(set(sources))  # Remove duplicates
    
    def fetch_data(
        self,
        data_sources: List[str],
        grade_level: str = None,
        student_id: str = None,
        classroom_id: str = None,
        school: str = None
    ) -> AssessmentDataSet:
        """
        Fetch data from the specified sources.
        
        This is a placeholder implementation that returns mock data.
        TODO: Replace with actual database queries once schemas are provided.
        
        Args:
            data_sources: List of data source identifiers
            grade_level: Optional grade level filter
            student_id: Optional student ID filter
            classroom_id: Optional classroom ID filter
            school: Optional school filter
            
        Returns:
            AssessmentDataSet containing data from requested sources
        """
        dataset = AssessmentDataSet()
        base_date = datetime.now() - timedelta(days=30)
        
        # Generate mock data based on requested sources
        if "EMT" in data_sources and "EMT" not in self.disabled_sources:
            # TODO: Replace with actual SQL query to EMT table
            dataset.emt_data = [
                EMTRecord(
                    student_id=student_id or "student_001",
                    assessment_date=base_date + timedelta(days=i),
                    emotion_score=0.75 + (i * 0.05),
                    metadata={"placeholder": True, "source": "EMT"}
                )
                for i in range(3)
            ]
        
        if "REAL" in data_sources and "REAL" not in self.disabled_sources:
            # TODO: Replace with actual SQL query to REAL table
            dataset.real_data = [
                REALRecord(
                    student_id=student_id or "student_001",
                    assessment_date=base_date + timedelta(days=i),
                    learning_score=0.70 + (i * 0.03),
                    metadata={"placeholder": True, "source": "REAL"}
                )
                for i in range(3)
            ]
        
        if "SEL" in data_sources and "SEL" not in self.disabled_sources:
            # TODO: Replace with actual SQL query to SEL Data table
            dataset.sel_data = [
                SELRecord(
                    student_id=student_id or "student_001",
                    assessment_date=base_date + timedelta(days=i),
                    assignment_id=f"sel_assignment_{i+1}",
                    self_awareness=0.80,
                    self_management=0.75,
                    social_awareness=0.85,
                    relationship_skills=0.78,
                    responsible_decision_making=0.82,
                    sel_score=0.80,
                    observations="Positive social-emotional development observed",
                    metadata={"placeholder": True, "source": "SEL"}
                )
                for i in range(3)
            ]
            
        # Fetch Aggregated CSV Data (Always fetch if available, or could be conditional)
        # For now, we fetch it to ensure the agent has access to the real data provided by the user.
        try:
            # Filter based on available parameters
            # Note: student_id is not supported by the aggregated CSV, only grade/school
            csv_rows = csv_data.filter_scores(
                grade=grade_level,
                school=school,
            )
            
            if csv_rows:
                comp = csv_data.compute_prepost_comparison(csv_rows)
                dataset.aggregated_data = AggregatedAssessmentData(
                    summary=comp["summary"],
                    metrics=comp["metrics"],
                    metadata={"source": "CSV", "file": csv_data.DEFAULT_FILE_NAME}
                )
        except Exception as e:
            # Log error but don't fail the whole request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching CSV data: {e}")

        
        return dataset
    
    def format_data_for_llm(self, dataset: AssessmentDataSet) -> Dict[str, Any]:
        """
        Format assessment data into a structure suitable for LLM prompts.
        
        Args:
            dataset: AssessmentDataSet containing data from multiple sources
            
        Returns:
            Dictionary formatted for LLM consumption
        """
        formatted = {
            "emt_summary": None,
            "real_summary": None,
            "sel_summary": None,
            "aggregated_summary": None
        }
        
        if dataset.emt_data:
            formatted["emt_summary"] = {
                "record_count": len(dataset.emt_data),
                "average_score": sum(r.emotion_score for r in dataset.emt_data) / len(dataset.emt_data),
                "latest_score": max(dataset.emt_data, key=lambda x: x.assessment_date).emotion_score,
                "records": [
                    {
                        "student_id": r.student_id,
                        "date": r.assessment_date.isoformat(),
                        "score": r.emotion_score
                    }
                    for r in dataset.emt_data
                ]
            }
        
        if dataset.real_data:
            formatted["real_summary"] = {
                "record_count": len(dataset.real_data),
                "average_score": sum(r.learning_score for r in dataset.real_data) / len(dataset.real_data),
                "latest_score": max(dataset.real_data, key=lambda x: x.assessment_date).learning_score,
                "records": [
                    {
                        "student_id": r.student_id,
                        "date": r.assessment_date.isoformat(),
                        "score": r.learning_score
                    }
                    for r in dataset.real_data
                ]
            }
        
        if dataset.sel_data:
            # Aggregate SEL scores
            sel_scores = {}
            for record in dataset.sel_data:
                for skill in ["self_awareness", "self_management", "social_awareness", 
                             "relationship_skills", "responsible_decision_making"]:
                    value = getattr(record, skill)
                    if value is not None:
                        if skill not in sel_scores:
                            sel_scores[skill] = []
                        sel_scores[skill].append(value)
            
            # Calculate average SEL score if available
            sel_score_values = [r.sel_score for r in dataset.sel_data if r.sel_score is not None]
            
            formatted["sel_summary"] = {
                "record_count": len(dataset.sel_data),
                "average_scores": {
                    skill: sum(values) / len(values) 
                    for skill, values in sel_scores.items()
                } if sel_scores else {},
                "average_sel_score": sum(sel_score_values) / len(sel_score_values) if sel_score_values else None,
                "records": [
                    {
                        "student_id": r.student_id,
                        "assignment_id": r.assignment_id,
                        "date": r.assessment_date.isoformat(),
                        "self_awareness": r.self_awareness,
                        "self_management": r.self_management,
                        "social_awareness": r.social_awareness,
                        "relationship_skills": r.relationship_skills,
                        "responsible_decision_making": r.responsible_decision_making,
                        "sel_score": r.sel_score,
                        "observations": r.observations
                    }
                    for r in dataset.sel_data
                ]
            }
        
        if dataset.aggregated_data:
            formatted["aggregated_summary"] = {
                "description": "Aggregated class-level assessment data (Pre vs Post)",
                "student_count": dataset.aggregated_data.summary.get("total_post", 0),
                "metrics": dataset.aggregated_data.metrics
            }
        
        return formatted

