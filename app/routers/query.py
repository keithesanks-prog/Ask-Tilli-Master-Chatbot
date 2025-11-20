"""
Query Router

Additional query endpoints for testing and data inspection.
"""
from fastapi import APIRouter, Depends
from typing import List, Dict, Any

from ..services.data_router import DataRouter
from ..services import csv_data
from ..middleware.auth import require_admin


router = APIRouter(prefix="/query", tags=["query"])
data_router = DataRouter()


@router.get("/sources")
async def identify_sources(question: str) -> Dict[str, Any]:
    """
    Identify which data sources would be used for a given question.
    Useful for testing and debugging the data routing logic.
    
    Args:
        question: Natural language question to analyze
        
    Returns:
        Dictionary with identified data sources
    """
    sources = data_router.determine_data_sources(question)
    return {
        "question": question,
        "data_sources": sources
    }


@router.get("/test-data")
async def get_test_data(sources: str = "EMT,SEL") -> Dict[str, Any]:
    """
    Fetch test/mock data for specified sources.
    Useful for development and testing.
    
    Args:
        sources: Comma-separated list of data sources (e.g., "EMT,SEL,REAL")
        
    Returns:
        Formatted data summary
    """
    source_list = [s.strip() for s in sources.split(",")]
    dataset = data_router.fetch_data(data_sources=source_list)
    data_summary = data_router.format_data_for_llm(dataset)
    
    return {
        "sources": source_list,
        "data_summary": data_summary
    }


@router.get("/prepost")
async def prepost_comparison(
    school: str = None,
    grade: str = None,
    assessment: str = None,
    file_name: str = csv_data.DEFAULT_FILE_NAME,
    current_user: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Compute PRE vs POST comparison from the uploaded CSV dataset.
    
    Query params (all optional):
    - school: Filter by school name (exact match)
    - grade: Filter by grade (e.g., "Grade 1")
    - assessment: Filter by assessment type (e.g., "child", "parent", "teacher_report")
    - file_name: CSV file name within data/ (defaults to latest export)
    """
    rows = csv_data.load_scores(file_name=file_name)
    filtered = csv_data.filter_records(rows, school=school, grade=grade, assessment=assessment)
    comparison = csv_data.compute_prepost_comparison(filtered)
    return {
        "filters": {
            "school": school,
            "grade": grade,
            "assessment": assessment,
            "file_name": file_name
        },
        "result": comparison
    }

