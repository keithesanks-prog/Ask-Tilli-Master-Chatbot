# Resource Bloat & Memory Leak Analysis

## Executive Summary
Following the implementation of log rotation, we conducted a code audit to identify other areas susceptible to unbounded resource usage (bloat) or memory leaks.

**Overall Status:** ✅ **Mostly Healthy**
One configuration-dependent risk was identified in the rate limiting middleware.

## Detailed Findings

### 1. Rate Limiting (Memory Bloat Risk) ⚠️
- **Component:** `app/middleware/rate_limit.py`
- **Issue:** The rate limiter defaults to in-memory storage (`memory://`) if `REDIS_URL` is not set.
- **Risk:** In a production environment or during a DDoS attack, tracking millions of unique IP addresses in memory could exhaust the server's RAM, leading to a crash.
- **Recommendation:** **Mandatory** use of Redis for rate limiting in production.
    - Set `REDIS_URL=redis://localhost:6379/0` in your environment.

### 2. CSV Data Service (Safe) ✅
- **Component:** `app/services/csv_data.py`
- **Mechanism:** Uses `@lru_cache(maxsize=4)` for loading CSV files.
- **Verdict:** **Safe**. The cache is strictly bounded to the last 4 accessed files. It will not grow indefinitely.

### 3. Harmful Content Detector (Safe) ✅
- **Component:** `app/services/harmful_content_detector.py`
- **Mechanism:** Uses Python's `re` module for pattern matching.
- **Verdict:** **Safe**. Regex compilation is handled efficiently by Python's internal cache. No request-specific state is stored in the class instance.

### 4. Prompt Eval Tool (Future Risk) ℹ️
- **Component:** `app/services/prompt_eval.py`
- **Issue:** Contains a placeholder `_write_to_csv` method.
- **Risk:** When implemented, if this simply appends to a CSV without rotation (like the original logs), it will create a new storage bloat issue.
- **Recommendation:** When implementing this feature, apply the same **Log Rotation** pattern used for audit logs.

### 5. LLM Engine & Data Router (Safe) ✅
- **Component:** `app/services/llm_engine.py`, `app/services/data_router.py`
- **Verdict:** **Safe**. These services are stateless request processors. They do not retain data in memory between requests.

## Action Plan
1.  **Production Config:** Ensure `REDIS_URL` is configured for production deployments.
2.  **Future Dev:** When implementing `PromptEvalTool`, copy the `ArchivingAuditHandler` pattern for its output files.
