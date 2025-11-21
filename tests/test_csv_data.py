"""
Tests for CSV Data Service
"""
import pytest
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import csv_data

def test_load_scores_existing_file():
    """Test loading the existing default CSV file."""
    rows = csv_data.load_scores(file_name="scores_export_2025-11-16.csv")
    assert len(rows) > 0
    assert "school" in rows[0]
    assert "test_type" in rows[0]

def test_filter_records():
    """Test filtering records."""
    rows = [
        {"school": "A", "grade": "1", "test_type": "PRE"},
        {"school": "B", "grade": "2", "test_type": "POST"},
        {"school": "A", "grade": "2", "test_type": "PRE"},
    ]
    
    # Filter by school
    filtered = csv_data.filter_records(rows, school="A")
    assert len(filtered) == 2
    assert all(r["school"] == "A" for r in filtered)
    
    # Filter by grade
    filtered = csv_data.filter_records(rows, grade="2")
    assert len(filtered) == 2
    assert all(r["grade"] == "2" for r in filtered)

def test_compute_prepost_comparison():
    """Test pre/post comparison logic."""
    rows = [
        {"test_type": "PRE", "total_students": 10, "metric_a": 5},
        {"test_type": "POST", "total_students": 10, "metric_a": 8},
    ]
    
    result = csv_data.compute_prepost_comparison(rows)
    
    assert result["summary"]["total_pre"] == 10
    assert result["summary"]["total_post"] == 10
    assert result["metrics"]["metric_a"]["pre"] == 5
    assert result["metrics"]["metric_a"]["post"] == 8
    assert result["metrics"]["metric_a"]["delta"] == 3
