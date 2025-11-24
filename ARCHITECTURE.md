# Master Chatbot Architecture

This document explains the architectural design of the Master Chatbot, including the rationale behind key technical decisions and how components interact.

## Table of Contents

- [System Overview](#system-overview)
- [Core Components](#core-components)
- [Router Architecture](#router-architecture)
- [Service Layer](#service-layer)
- [Security Architecture](#security-architecture)
- [Data Flow](#data-flow)
- [Design Decisions](#design-decisions)

---

## System Overview

The Master Chatbot is a **multi-layered, secure API service** that provides educators with natural language access to student assessment data. It combines:

- **FastAPI** for high-performance async HTTP handling
- **LLM integration** (Google Gemini) for natural language understanding
- **Multi-source data routing** to aggregate data from REAL, EMT, and SEL assessments
- **FERPA/UNICEF-compliant security** with audit logging and access control

### High-Level Architecture

```
┌─────────────┐
│  Educator   │ (Frontend/Client)
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│  ┌────────────────────────────────┐     │
│  │   Security Middleware Layer    │     │
│  │  • TLS/HTTPS                   │     │
│  │  • Authentication (JWT)        │     │
│  │  • Rate Limiting               │     │
│  │  • Input Sanitization          │     │
│  │  • Harmful Content Detection   │     │
│  │  • Data Access Control         │     │
│  └────────────────────────────────┘     │
│                                         │
│  ┌────────────────────────────────┐     │
│  │      Router Layer              │     │
│  │  • Agent Router (/agent/ask)   │     │
│  │  • Chat Router (/chat)         │     │
│  │  • Query Router (/query/*)     │     │
│  │  • Prompt Eval Router          │     │
│  └────────────────────────────────┘     │
│                                         │
│  ┌────────────────────────────────┐     │
│  │      Service Layer             │     │
│  │  • Data Router                 │     │
│  │  • LLM Engine                  │     │
│  │  • CSV Data Service            │     │
│  │  • Audit Logger                │     │
│  └────────────────────────────────┘     │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Data Layer                      │
│  • REAL Data (student records)          │
│  • EMT Data (emotion matching)          │
│  • SEL Data (social-emotional)          │
│  • CSV Exports (aggregated)             │
│  • Access Control DB (SQLite)           │
└─────────────────────────────────────────┘
```

---

## Core Components

### 1. FastAPI Application (`main.py`)

**Purpose:** Entry point and application orchestration

**Responsibilities:**
- Initialize FastAPI app with lifespan management
- Register routers (agent, query, prompt-eval)
- Configure middleware (CORS, rate limiting, security headers)
- Set up fail-safe shutdown behavior
- Configure logging and audit systems

**Technical Decision:** FastAPI was chosen for:
- **Async/await support** - handles concurrent requests efficiently
- **Automatic OpenAPI documentation** - self-documenting API
- **Pydantic validation** - type-safe request/response models
- **Dependency injection** - clean separation of concerns

### 2. Router Layer

The application uses **multiple routers** instead of a monolithic endpoint structure. This is a deliberate architectural choice.

#### Agent Router (`routers/agent.py`)

**Endpoint:** `POST /agent/ask`

**Purpose:** Main production endpoint for educator questions

**Why separate from Query Router?**
1. **Security isolation** - Production endpoints have stricter security
2. **Rate limiting** - Different limits for production vs testing
3. **Audit requirements** - All production queries must be logged
4. **Access control** - Enforces data access permissions
5. **Harmful content detection** - Scans questions and responses

**Request Flow:**
```
1. Authentication (JWT verification)
2. Input sanitization (SQL injection, prompt injection)
3. Harmful content detection (question)
4. Data access authorization (BEFORE data retrieval)
5. Data routing (determine sources)
6. Data fetching (from REAL, EMT, SEL, CSV)
7. LLM response generation
8. Harmful content detection (response)
9. Audit logging (FERPA/UNICEF compliance)
10. Return response
```

#### Query Router (`routers/query.py`)

**Endpoints:**
- `GET /query/sources` - Identify data sources for a question
- `GET /query/test-data` - Fetch mock data for testing
- `GET /query/prepost` - Pre/Post comparison from CSV

**Purpose:** Testing, debugging, and administrative queries

**Why separate from Agent Router?**
1. **Development/testing** - Safe endpoints for development
2. **Admin-only access** - Some endpoints require admin role
3. **No LLM calls** - Direct data access without AI processing
4. **Different rate limits** - More permissive for testing
5. **No harmful content scanning** - Not user-facing

**Technical Decision:** Separating production from testing endpoints:
- **Prevents accidental exposure** of debug endpoints
- **Allows different security policies** per router
- **Simplifies monitoring** - production vs testing metrics
- **Enables gradual rollout** - can disable testing endpoints in production

#### Prompt Eval Router (`routers/prompt_eval.py`)

**Endpoint:** `POST /prompt-eval/receive`

**Purpose:** Receive evaluation data from external Prompt Eval Tool

**Why separate router?**
- **External integration** - different authentication requirements
- **Async processing** - writes to CSV, doesn't block
- **No user interaction** - machine-to-machine communication

---

## Service Layer

### Data Router (`services/data_router.py`)

**Purpose:** Intelligent data source selection and aggregation

**Key Functions:**

1. **`determine_data_sources(question)`**
   - Analyzes question using keyword matching
   - Returns list of relevant sources (REAL, EMT, SEL)
   - Example: "How is the student's emotional state?" → `["EMT", "SEL"]`

2. **`fetch_data(sources, filters)`**
   - Fetches data from selected sources
   - Applies filters (student_id, classroom_id, grade_level)
   - Returns `AssessmentDataSet` with all data

3. **`format_data_for_llm(dataset)`**
   - Converts raw data to natural language summary
   - Formats for LLM consumption
   - Includes aggregated CSV data if available

**Why a separate Data Router?**
- **Single Responsibility** - only handles data routing logic
- **Testability** - can test routing logic independently
- **Extensibility** - easy to add new data sources
- **Caching potential** - can add caching layer later
- **Multi-tenant support** - enforces school-level isolation

### LLM Engine (`services/llm_engine.py`)

**Purpose:** LLM interaction and prompt management

**Key Functions:**

1. **`generate_response(question, data_summary)`**
   - Builds comprehensive prompt with data
   - Calls Google Gemini API
   - Returns natural language response

2. **`_build_prompt(question, data_summary)`**
   - Constructs prompt with:
     - System instructions
     - Data context
     - User question
     - Safety guidelines

3. **`_generate_mock_response(data_summary)`**
   - Fallback when Gemini API unavailable
   - Uses CSV data if available
   - Returns structured response

**Why separate LLM Engine?**
- **API abstraction** - can swap LLM providers
- **Prompt versioning** - centralized prompt management
- **Testing** - mock responses for development
- **Cost control** - can add caching, rate limiting
- **Security** - prompt injection prevention

### CSV Data Service (`services/csv_data.py`)

**Purpose:** Load and process aggregated assessment data from CSV exports

**Key Functions:**
- `load_scores()` - Load CSV file
- `filter_scores()` - Filter by school, grade, assessment type
- `compute_prepost_comparison()` - Calculate Pre vs Post metrics

**Why separate CSV service?**
- **Data format isolation** - CSV logic separate from database logic
- **Aggregated data** - different from individual student records
- **Program-level insights** - class/school-level trends
- **Easy updates** - can swap CSV files without code changes

### Audit Logger (`services/audit_logger.py`)

**Purpose:** FERPA/UNICEF-compliant audit logging

**Key Features:**
- **Immutable logs** - append-only, tamper-proof
- **Automatic rotation** - size-based with compression
- **Multiple sinks** - file, Splunk, OpenSearch, webhooks
- **Compliance flags** - FERPA, UNICEF, GDPR, COPPA

**Why separate audit logger?**
- **Compliance requirement** - FERPA mandates audit trail
- **Security** - centralized logging prevents bypass
- **Retention** - 7-year retention for FERPA
- **Monitoring** - external sink integration

---

## Security Architecture

### Layered Security Model

The application uses **defense in depth** with multiple security layers:

```
Layer 1: Transport Security (TLS/HTTPS)
         ↓
Layer 2: Authentication (JWT verification)
         ↓
Layer 3: Rate Limiting (per-endpoint, per-user)
         ↓
Layer 4: Input Sanitization (SQL/prompt injection)
         ↓
Layer 5: Harmful Content Detection (child safety)
         ↓
Layer 6: Data Access Control (authorization)
         ↓
Layer 7: Audit Logging (compliance)
```

### Why Multiple Security Layers?

**Defense in Depth:** If one layer fails, others provide protection

**Example Attack Scenarios:**

1. **SQL Injection Attempt:**
   - Layer 4 (Input Sanitization) blocks malicious input
   - Layer 7 (Audit Logging) records the attempt

2. **Unauthorized Data Access:**
   - Layer 2 (Authentication) verifies user identity
   - Layer 6 (Data Access Control) checks permissions
   - Layer 7 (Audit Logging) records access denied event

3. **Harmful Content:**
   - Layer 5 (Harmful Content Detection) scans question
   - Layer 5 (again) scans LLM response
   - Layer 7 (Audit Logging) records detection for UNICEF compliance

### Data Access Control

**Purpose:** Ensure educators only access data for their assigned students

**Architecture:**

```
┌─────────────────────────────────────────┐
│  Educator Authentication (JWT)          │
│  • user_id: "educator_alice"            │
│  • role: "educator"                     │
│  • school_id: "school_1"                │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Data Access Middleware                 │
│  1. Check if user is admin              │
│     → YES: Allow (school-scoped)        │
│     → NO: Continue to step 2            │
│  2. Check educator-student relationship │
│     → Query: educator_classrooms        │
│     → Query: student_classrooms         │
│     → Check overlap                     │
│  3. Allow or Deny (403 Forbidden)       │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Audit Logger                           │
│  • Log access granted/denied            │
│  • Include purpose (UNICEF requirement) │
│  • Immutable, append-only               │
└─────────────────────────────────────────┘
```

**Why SQLite for Access Control?**
- **Embedded** - no separate database server needed
- **ACID compliant** - reliable for access control
- **Fast** - local file access
- **Easy migration** - can move to PostgreSQL later
- **Development-friendly** - zero setup required

---

## Data Flow

### Complete Request Flow

```
1. Educator sends question
   ↓
2. TLS/HTTPS encryption
   ↓
3. FastAPI receives request
   ↓
4. Authentication middleware (JWT)
   ↓
5. Rate limiting check
   ↓
6. Agent Router receives request
   ↓
7. Input sanitization
   ↓
8. Harmful content detection (question)
   ↓
9. Data access authorization
   ↓
10. Data Router determines sources
   ↓
11. Fetch data from REAL, EMT, SEL, CSV
   ↓
12. Format data for LLM
   ↓
13. LLM Engine builds prompt
   ↓
14. Call Gemini API
   ↓
15. Receive LLM response
   ↓
16. Harmful content detection (response)
   ↓
17. Audit logging (FERPA/UNICEF)
   ↓
18. Return response to educator
```

**Why this specific order?**
- **Security first** - authentication before any processing
- **Early validation** - data access check BEFORE data retrieval
- **Fail fast** - reject invalid requests early
- **Audit everything** - log all access attempts

---

## Design Decisions

### 1. Why FastAPI instead of Flask/Django?

**FastAPI advantages:**
- **Async/await** - better concurrency for I/O-bound operations (LLM calls, database queries)
- **Type safety** - Pydantic models prevent runtime errors
- **Auto-documentation** - OpenAPI/Swagger out of the box
- **Performance** - comparable to Node.js/Go
- **Modern Python** - uses Python 3.7+ features

### 2. Why separate routers instead of one monolithic router?

**Separation of concerns:**
- **Agent Router** - production, high security, audit logging
- **Query Router** - testing, admin-only, no LLM
- **Prompt Eval Router** - external integration, async processing

**Benefits:**
- Different security policies per router
- Different rate limits per router
- Easier to disable testing endpoints in production
- Clearer code organization
- Independent testing

### 3. Why Data Router instead of direct database access?

**Abstraction benefits:**
- **Single point of control** - all data access goes through one service
- **Multi-source aggregation** - combines REAL, EMT, SEL, CSV
- **Caching potential** - can add caching layer
- **Access control enforcement** - enforces permissions
- **Testing** - can mock data sources

### 4. Why SQLite for access control instead of PostgreSQL?

**Development phase:**
- **Zero setup** - no database server required
- **File-based** - easy to backup and version
- **Fast** - local file access
- **ACID compliant** - reliable for access control

**Migration path:**
- Can easily migrate to PostgreSQL/MySQL later
- Same SQL syntax
- Minimal code changes required

### 5. Why middleware for security instead of decorators?

**Middleware advantages:**
- **Automatic application** - applies to all endpoints
- **Layered security** - multiple middleware layers
- **Request/response interception** - can modify both
- **Fail-safe** - can't forget to apply security

**Decorator disadvantages:**
- Must remember to apply to each endpoint
- Easy to miss an endpoint
- Harder to enforce consistency

### 6. Why separate Audit Logger instead of standard logging?

**Compliance requirements:**
- **FERPA** - requires 7-year retention
- **UNICEF** - requires purpose tracking
- **Immutable** - append-only, tamper-proof
- **Structured** - JSON format for analysis
- **External sinks** - Splunk, OpenSearch integration

**Standard logging insufficient:**
- No retention guarantees
- Can be modified/deleted
- Not structured for compliance
- No external sink support

---

## Scalability Considerations

### Current Architecture (Single Server)

```
┌─────────────┐
│   Educator  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  FastAPI Server │
│  • All routers  │
│  • All services │
│  • SQLite DB    │
└─────────────────┘
```

### Future Architecture (Distributed)

```
┌─────────────┐
│   Educator  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Load Balancer  │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ API 1  │ │ API 2  │
└───┬────┘ └───┬────┘
    │          │
    └────┬─────┘
         ▼
┌─────────────────┐
│  PostgreSQL DB  │
│  (Access Control)│
└─────────────────┘
```

**Migration path:**
1. Replace SQLite with PostgreSQL
2. Add connection pooling
3. Deploy multiple API servers
4. Add load balancer (nginx/HAProxy)
5. Centralize audit logs (Splunk/OpenSearch)

---

## Summary

The Master Chatbot architecture is designed for:

✅ **Security** - Multiple layers of defense
✅ **Compliance** - FERPA/UNICEF audit logging
✅ **Scalability** - Can scale horizontally
✅ **Maintainability** - Clear separation of concerns
✅ **Testability** - Each component independently testable
✅ **Extensibility** - Easy to add new data sources/features

**Key architectural principles:**
- **Defense in depth** - multiple security layers
- **Separation of concerns** - routers, services, middleware
- **Fail-safe design** - reject by default, allow explicitly
- **Audit everything** - comprehensive logging for compliance
- **Type safety** - Pydantic models prevent errors
