"""
Debug Router

Internal endpoints to inspect PRE/POST data directly from the CSV.
Not intended for production use.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from ..services import csv_data
from ..middleware.auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/pre-post")
async def debug_pre_post(
	grade: str = Query(..., description="Grade label, e.g., 'Grade 1'"),
	assessment: Optional[str] = Query(None, description="Assessment type, e.g., 'child', 'parent', 'teacher_report'"),
	file_name: str = csv_data.DEFAULT_FILE_NAME,
	current_user: dict = Depends(require_admin),
) -> Dict[str, Any]:
	"""
	Return raw PRE and POST summaries and a comparison object for the given grade/assessment.
	"""
	try:
		pre_rows = csv_data.filter_scores(grade=grade, assessment=assessment, test_type="pre", file_name=file_name)
		post_rows = csv_data.filter_scores(grade=grade, assessment=assessment, test_type="post", file_name=file_name)
		
		pre_summary = csv_data.summarize_rows(pre_rows)
		post_summary = csv_data.summarize_rows(post_rows)
		compare = csv_data.build_comparison_summary(pre_rows, post_rows)
		
		return {
			"filters": {"grade": grade, "assessment": assessment, "file_name": file_name},
			"counts": {"rows_pre": len(pre_rows), "rows_post": len(post_rows)},
			"pre": pre_summary,
			"post": post_summary,
			"comparison": compare,
		}
	except FileNotFoundError as e:
		raise HTTPException(status_code=404, detail=str(e))
	except Exception as e:
		logger.error(f"debug_pre_post error: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail="Failed to compute pre/post debug summary")


