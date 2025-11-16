# Known Key-Value Structures

This document catalogs all known key-value pairs in the Master Agent system to help with security validation and documentation.

## API Request Models

### `AskRequest` (`/ask`, `/agent/ask`)

**Known Fields:**
```python
{
    "question": str,           # Required, 1-5000 chars
    "grade_level": Optional[str],  # Optional, max 50 chars, format: "Grade N"
    "student_id": Optional[str],   # Optional, max 100 chars, alphanumeric + ._-
    "classroom_id": Optional[str], # Optional, max 100 chars, alphanumeric + ._-
}
```

**Validation:**
- ✅ `question`: Validated via `InputSanitizer.sanitize_question()`
- ✅ `student_id`: Validated via `InputSanitizer.sanitize_identifier()`
- ✅ `classroom_id`: Validated via `InputSanitizer.sanitize_identifier()`
- ✅ `grade_level`: Validated via `InputSanitizer.sanitize_grade_level()`

---

### `PromptEvalRequest` (`/prompt-eval/receive`)

**Known Fields:**
```python
{
    "prompt": Optional[str],              # The evaluated prompt
    "question": Optional[str],            # Original educator question
    "response": Optional[str],            # LLM response
    "data_summary": Optional[Dict],       # See data_summary structure below
    "evaluation_metrics": Optional[Dict], # See evaluation_metrics structure below
    "timestamp": Optional[str],           # ISO format timestamp
    # ... extra = "allow" means additional fields may exist
}
```

**Validation:**
- ✅ `question`: Sanitized if present
- ✅ `data_summary`: Recursively sanitized via `DictSanitizer.sanitize_data_summary()`
- ✅ `evaluation_metrics`: Recursively sanitized via `DictSanitizer.sanitize_evaluation_metrics()`
- ⚠️ Unknown fields: Accepted (due to `extra = "allow"`) but values are sanitized

---

## Data Structures

### `data_summary` Structure

**Format:** `Dict[str, Any]` - Returned from `data_router.format_data_for_llm()`

**Known Keys:**
```python
{
    "emt_summary": Optional[{
        "record_count": int,
        "average_score": float,
        "latest_score": float,
        "records": List[{
            "student_id": str,
            "date": str,  # ISO format
            "score": float
        }]
    }],
    
    "real_summary": Optional[{
        "record_count": int,
        "average_score": float,
        "latest_score": float,
        "records": List[{
            "student_id": str,
            "date": str,  # ISO format
            "score": float
        }]
    }],
    
    "sel_summary": Optional[{
        "record_count": int,
        "average_scores": {
            "self_awareness": Optional[float],
            "self_management": Optional[float],
            "social_awareness": Optional[float],
            "relationship_skills": Optional[float],
            "responsible_decision_making": Optional[float]
        },
        "latest_assignment": Optional[{
            "student_id": str,
            "assignment_id": Optional[str],
            "date": str,  # ISO format
            "self_awareness": Optional[float],
            "self_management": Optional[float],
            "social_awareness": Optional[float],
            "relationship_skills": Optional[float],
            "responsible_decision_making": Optional[float],
            "sel_score": Optional[float],
            "observations": Optional[str]
        }],
        "records": List[{
            "student_id": str,
            "assignment_id": Optional[str],
            "date": str,
            # ... same fields as latest_assignment
        }]
    }]
}
```

**Validation:**
- ✅ Recursively sanitized via `DictSanitizer.sanitize_data_summary()`
- ✅ String values checked for injection patterns
- ✅ Known keys whitelisted, unknown keys allowed but validated

---

### `evaluation_metrics` Structure

**Format:** `Dict[str, Any]` - From external Prompt Eval Tool

**Known Keys:**
```python
{
    "timestamp": str,              # ISO format
    "question": str,               # Original question
    "prompt_length": int,          # Character count
    "data_sources_used": List[str], # e.g., ["EMT", "SEL"]
    "response_length": int,        # Character count
    "evaluation_score": Optional[float],
    "metrics": Optional[Dict],     # Additional metrics (structure unknown)
    # ... Additional fields may exist (from external tool)
}
```

**Validation:**
- ✅ Recursively sanitized via `DictSanitizer.sanitize_evaluation_metrics()`
- ✅ String values checked for injection patterns
- ⚠️ Structure is partially unknown (from external service)
- ⚠️ All values validated even if keys are unknown

---

### `metadata` Fields (Data Models)

**Location:** `EMTRecord.metadata`, `REALRecord.metadata`, `SELRecord.metadata`

**Format:** `Dict[str, Any]` - Intentionally flexible for extensibility

**Known Usage:**
```python
{
    "placeholder": bool,        # Indicates mock data
    "source": str,             # "EMT", "REAL", or "SEL"
    # ... Additional fields may be added as schemas evolve
}
```

**Validation:**
- ✅ Recursively sanitized via `DictSanitizer.sanitize_metadata()`
- ✅ No key whitelist (metadata is intentionally open)
- ✅ All string values validated for injection patterns

---

## Response Models

### `AskResponse`

**Known Fields:**
```python
{
    "answer": str,                    # LLM-generated response
    "data_sources": List[str],        # e.g., ["EMT", "SEL"]
    "confidence": Optional[str]       # "high", "medium", or "low"
}
```

**Validation:**
- ✅ Defined in Pydantic model (type-safe)
- ✅ No additional sanitization needed (generated by system)

---

### `PromptEvalResponse`

**Known Fields:**
```python
{
    "status": str,    # "success" or "error"
    "message": str    # Human-readable message
}
```

**Validation:**
- ✅ Defined in Pydantic model (type-safe)

---

## Protection Strategy for Unknown Key-Values

### Current Approach

1. **Whitelist Known Keys** (where possible)
   - `data_summary`: Known keys whitelisted, unknown allowed
   - `evaluation_metrics`: Known keys whitelisted, unknown allowed
   - `metadata`: No whitelist (intentionally flexible)

2. **Recursive Sanitization** (`DictSanitizer`)
   - All string values checked for injection patterns
   - Nested structures sanitized recursively
   - Dictionary size limits prevent DoS
   - Maximum depth prevents stack overflow

3. **Pattern-Based Detection**
   - Prompt injection patterns: 20+ patterns
   - SQL injection patterns: 7+ patterns
   - Applied to all string values regardless of key

4. **Type Safety** (Pydantic)
   - Known structures defined as Pydantic models
   - Type validation at API boundary
   - Automatic coercion and validation

### Areas with Unknown Structures

| Structure | Known Keys | Unknown Keys | Protection Level |
|-----------|------------|--------------|------------------|
| `PromptEvalRequest` | 6 known | Yes (`extra="allow"`) | ⚠️ Sanitized but flexible |
| `evaluation_metrics` | 7 known | Yes (external tool) | ⚠️ Recursively sanitized |
| `data_summary` | ~15 known | Possibly (if DB schema changes) | ✅ Mostly known, sanitized |
| `metadata` fields | 2 known | Yes (intentional) | ⚠️ Recursively sanitized |

---

## Recommendations

### 1. Document All External API Contracts

**Action Items:**
- [ ] Get Prompt Eval Tool API specification
- [ ] Document all possible `evaluation_metrics` keys
- [ ] Document database schema fields (when available)
- [ ] Create Pydantic models for external data structures

### 2. Strengthen Validation

**Current:** Recursive sanitization with pattern detection

**Improvements:**
- [ ] Add schema validation for `evaluation_metrics` when structure is known
- [ ] Create Pydantic models for external tool responses
- [ ] Implement stricter mode for production (`strict_mode=True`)
- [ ] Add field-level validation rules (e.g., timestamp format, score ranges)

### 3. Discovery Process

**How to Find Unknown Key-Values:**

1. **API Documentation**
   - Check Prompt Eval Tool documentation
   - Review database schema documentation
   - Check integration contracts

2. **Logging & Monitoring**
   - Log all received keys in `evaluation_metrics`
   - Monitor for unexpected keys in `data_summary`
   - Alert on unknown keys in production

3. **Code Inspection**
   ```python
   # Add logging to discover unknown keys
   def log_unknown_keys(data: Dict, context: str):
       known_keys = {...}  # Known keys
       received_keys = set(data.keys())
       unknown = received_keys - known_keys
       if unknown:
           logger.info(f"Unknown keys in {context}: {unknown}")
   ```

4. **Testing**
   - Integration tests with actual external services
   - Test with sample data from production
   - Validate against real database schemas

### 4. Security for Unknown Keys

**Current Protection:**
- ✅ All string values sanitized (regardless of key)
- ✅ Injection pattern detection (keys and values)
- ✅ Dictionary size limits
- ✅ Recursive sanitization
- ✅ Key format validation

**What We Can't Protect:**
- ❌ Unknown keys might contain sensitive data (but values are sanitized)
- ❌ Unknown structure might bypass business logic (but not injection)
- ❌ Can't validate semantic meaning (e.g., is `score` really a number?)

**What We Can Do:**
- ✅ Sanitize all values to prevent injection
- ✅ Validate key format (alphanumeric + safe chars)
- ✅ Limit sizes to prevent DoS
- ✅ Log unknown keys for discovery

---

## Example: Unknown Key Handling

**Scenario:** Prompt Eval Tool sends new metric `custom_score`:

```python
{
    "evaluation_metrics": {
        "timestamp": "2024-01-01T12:00:00",
        "custom_score": 0.95,  # Unknown key!
        "new_field": "some value"  # Another unknown key!
    }
}
```

**What Happens:**
1. ✅ Pydantic accepts (due to `extra="allow"`)
2. ✅ `DictSanitizer.sanitize_evaluation_metrics()` recursively sanitizes
3. ✅ Key `"custom_score"` validated (alphanumeric + underscore ✓)
4. ✅ Value `0.95` passed through (not a string, safe ✓)
5. ✅ Key `"new_field"` validated
6. ✅ Value `"some value"` checked for injection patterns ✓
7. ✅ All values sanitized successfully

**Result:** Unknown keys are accepted and sanitized, protecting against injection even when structure is unknown.

---

## Next Steps

1. **Immediate:**
   - ✅ Recursive sanitization implemented
   - ✅ Pattern detection on all string values
   - ✅ Documentation of known structures

2. **Short-term:**
   - [ ] Get external API specifications
   - [ ] Add logging to discover unknown keys
   - [ ] Create comprehensive Pydantic models

3. **Long-term:**
   - [ ] Implement schema validation for all external data
   - [ ] Add monitoring/alerting for unknown keys
   - [ ] Create automated tests against real external services


