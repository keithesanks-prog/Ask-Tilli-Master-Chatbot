"""
CSV Data Service

Loads assessment score exports from `data/` and provides utilities
to filter records and compute PRE vs POST comparisons.
"""
import csv
import os
from functools import lru_cache
from typing import Dict, List, Any, Optional, Tuple

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

# Default file name pattern (latest export can be passed explicitly)
DEFAULT_FILE_NAME = "scores_export_2025-11-16.csv"


def _to_int(value: str) -> int:
	"""Convert CSV numeric field to int safely."""
	try:
		return int(value)
	except Exception:
		return 0


@lru_cache(maxsize=4)
def load_scores(file_name: str = DEFAULT_FILE_NAME) -> List[Dict[str, Any]]:
	"""
	Load the scores CSV into a list of dict rows.
	Results are memoized per file name.
	"""
	file_path = file_name
	if not os.path.isabs(file_path):
		file_path = os.path.join(DATA_DIR, file_name)
	
	if not os.path.exists(file_path):
		raise FileNotFoundError(f"Scores CSV not found: {file_path}")
	
	with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
		reader = csv.DictReader(f)
		rows: List[Dict[str, Any]] = []
		for row in reader:
			# Normalize and convert numeric fields
			normalized: Dict[str, Any] = {
				"id": row.get("ID"),
				"school": row.get("School"),
				"grade": row.get("Grade"),
				"assessment": row.get("Assessment"),
				"total_students": _to_int(row.get("Total Students", "0")),
				"test_type": row.get("Test Type"),  # PRE or POST
			}
			
			# All metric columns start after Test Type in this export
			for key, val in row.items():
				if key in ["ID", "School", "Grade", "Assessment", "Total Students", "Test Type"]:
					continue
				metric_key = key.strip().lower().replace(" ", "_")
				normalized[metric_key] = _to_int(val)
			
			rows.append(normalized)
	
	return rows


def filter_records(
	rows: List[Dict[str, Any]],
	school: Optional[str] = None,
	grade: Optional[str] = None,
	assessment: Optional[str] = None,
	test_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
	"""Filter rows by school, grade, and assessment if provided."""
	result = []
	for r in rows:
		if school and (r.get("school") or "").lower() != school.lower():
			continue
		if grade and (r.get("grade") or "").lower() != grade.lower():
			continue
		if assessment and (r.get("assessment") or "").lower() != assessment.lower():
			continue
		if test_type and (r.get("test_type") or "").lower() != test_type.lower():
			continue
		result.append(r)
	return result


def _split_pre_post(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
	pre = [r for r in rows if (r.get("test_type") or "").upper() == "PRE"]
	post = [r for r in rows if (r.get("test_type") or "").upper() == "POST"]
	return pre, post


def _metric_keys(row: Dict[str, Any]) -> List[str]:
	"""Return all metric keys present in a row (numeric fields only)."""
	skip = {"id", "school", "grade", "assessment", "total_students", "test_type"}
	return [k for k, v in row.items() if k not in skip and isinstance(v, int)]


def compute_prepost_comparison(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
	"""
	Compute PRE vs POST aggregates and deltas for each metric.
	If multiple rows exist per bucket (e.g., multiple assessments), sums are used.
	"""
	if not rows:
		return {"summary": {"total_pre": 0, "total_post": 0}, "metrics": {}, "notes": ["No matching records"]}
	
	pre_rows, post_rows = _split_pre_post(rows)
	
	# Gather metric keys from the first available row
	sample = next((r for r in rows if r), None) or {}
	metrics = _metric_keys(sample)
	
	def sum_metric(rows_local: List[Dict[str, Any]], key: str) -> int:
		return sum(int(r.get(key, 0) or 0) for r in rows_local)
	
	out: Dict[str, Any] = {
		"summary": {
			"total_pre": sum(int(r.get("total_students", 0)) for r in pre_rows),
			"total_post": sum(int(r.get("total_students", 0)) for r in post_rows),
			"rows_pre": len(pre_rows),
			"rows_post": len(post_rows),
		},
		"metrics": {},
	}
	
	for key in metrics:
		pre_val = sum_metric(pre_rows, key)
		post_val = sum_metric(post_rows, key)
		out["metrics"][key] = {
			"pre": pre_val,
			"post": post_val,
			"delta": post_val - pre_val,
		}
	
	return out


def summarize_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
	"""
	Summarize a set of rows by summing each metric and total_students.
	"""
	if not rows:
		return {"total_students": 0, "metrics": {}}
	sample = rows[0]
	metrics = _metric_keys(sample)
	sums: Dict[str, int] = {k: 0 for k in metrics}
	for r in rows:
		for k in metrics:
			sums[k] += int(r.get(k, 0) or 0)
	return {
		"total_students": sum(int(r.get("total_students", 0)) for r in rows),
		"metrics": sums,
	}


def filter_scores(
	grade: Optional[str] = None,
	test_type: Optional[str] = None,
	school: Optional[str] = None,
	assessment: Optional[str] = None,
	file_name: str = DEFAULT_FILE_NAME,
) -> List[Dict[str, Any]]:
	"""
	Load and filter scores in one step (convenience for agent).
	"""
	rows = load_scores(file_name=file_name)
	return filter_records(
		rows,
		school=school,
		grade=grade,
		assessment=assessment,
		test_type=test_type,
	)


def build_comparison_summary(
	pre_rows: List[Dict[str, Any]],
	post_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
	"""
	Produce a concise comparison summary object with pre, post, and delta per metric.
	"""
	pre_summary = summarize_rows(pre_rows)
	post_summary = summarize_rows(post_rows)
	# Union of metric keys
	all_keys = set(pre_summary.get("metrics", {}).keys()) | set(post_summary.get("metrics", {}).keys())
	metrics = {}
	for k in sorted(all_keys):
		pre_val = int(pre_summary.get("metrics", {}).get(k, 0))
		post_val = int(post_summary.get("metrics", {}).get(k, 0))
		metrics[k] = {
			"pre": pre_val,
			"post": post_val,
			"delta": post_val - pre_val,
		}
	return {
		"pre": {"total_students": pre_summary["total_students"]},
		"post": {"total_students": post_summary["total_students"]},
		"metrics": metrics,
	}


