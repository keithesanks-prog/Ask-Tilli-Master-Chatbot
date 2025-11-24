# Master Chatbot Architecture Presentation Script

**Purpose:** Verbal walkthrough of the Master Chatbot architecture for presentations, demos, and stakeholder meetings.

**Duration:** ~10-15 minutes

**Audience:** Technical and non-technical stakeholders, educators, administrators

---

## Opening (30 seconds)

"Today I'm going to walk you through the architecture of the Tilli Master Chatbot - a secure, FERPA and UNICEF-compliant system that gives educators natural language access to student assessment data.

The key thing to understand is that this isn't just a chatbot - it's a **multi-layered security system** with a conversational interface. Every design decision prioritizes student data protection while making the system easy and intuitive for educators to use."

---

## Section 1: The Big Picture (2 minutes)

### Visual: High-Level Architecture Diagram

"Let me start with the 30,000-foot view. Here's how the system works:

**[Point to diagram]**

1. **At the top**, we have educators - teachers, administrators, counselors - who need quick answers about student performance.

2. **In the middle**, we have our FastAPI application. This is the brain of the system, and it's organized into three main layers:
   - **Security Middleware** - This is our fortress. Every request goes through seven layers of security before it even touches student data.
   - **Router Layer** - Think of this as our traffic controller, directing different types of requests to the right handlers.
   - **Service Layer** - This is where the magic happens - data routing, AI processing, and audit logging.

3. **At the bottom**, we have our data layer - student records from REAL assessments, emotional matching data from EMT, social-emotional learning data from SEL, and aggregated CSV exports.

**The key architectural principle here is 'defense in depth'** - if one security layer fails, six others are still protecting student data."

---

## Section 2: Security Architecture (3 minutes)

### Visual: Layered Security Model

"Now let's talk about security, because this is where the architecture really shines. We use a **seven-layer security model**:

**Layer 1: Transport Security**
'All communication is encrypted with TLS 1.3 - the same encryption your bank uses. No data travels over the internet in plain text.'

**Layer 2: Authentication**
'We've integrated with Auth0 - an enterprise-grade identity provider. This gives us two modes:
- **Production mode**: Uses Auth0 with RS256 JWT tokens verified against their public keys
- **Development mode**: Falls back to local JWT for testing
This hybrid approach means we're production-ready while still being developer-friendly.'

**Layer 3: Rate Limiting**
'We prevent abuse with per-endpoint rate limits. For example, the main `/ask` endpoint is limited to 10 requests per minute per user. This protects against both malicious attacks and accidental overuse.'

**Layer 4: Input Sanitization**
'Every question goes through our input sanitizer, which checks for 20+ prompt injection patterns and 7 SQL injection patterns. If someone tries to trick the AI or attack our database, we catch it here.'

**Layer 5: Harmful Content Detection**
'This is critical for UNICEF compliance. We scan both the educator's question AND the AI's response for 13 types of harmful content - things like self-harm indicators, bullying, abuse signals. If we detect something critical, we block the response and alert administrators immediately.'

**Layer 6: Data Access Control**
'Here's where we enforce the principle of least privilege. We have **school-level isolation** - educators from School A cannot access data from School B, period. The system checks:
- Is this user authenticated?
- What school are they assigned to?
- Does the requested data belong to their school?
If any check fails, they get a 403 Forbidden error, and we log the attempt.'

**Layer 7: Audit Logging**
'Every single data access is logged with:
- Who accessed it (user ID, email, role)
- What they accessed (student ID, classroom, data sources)
- When they accessed it (UTC timestamp)
- **Why they accessed it** (purpose - this is a UNICEF requirement)
These logs are immutable, append-only, and retained for 7 years for FERPA compliance.'

**The beauty of this layered approach** is that an attacker would have to bypass ALL seven layers to compromise student data. That's why we call it 'defense in depth.'"

---

## Section 3: Router Architecture (2 minutes)

### Visual: Router Layer Diagram

"Now let's talk about how we organize our API endpoints. We use **three separate routers**, and this is a deliberate architectural choice:

**Agent Router** (`/agent/ask`)
'This is the production endpoint - where educators ask questions. It has:
- Strictest security (all 7 layers active)
- Lowest rate limits (10/minute)
- Full audit logging
- Harmful content detection
- Data access control

Think of this as the VIP entrance - maximum security, everything is logged.'

**Chat Router** (`/chat`)
'This is our conversational interface for SEL analysis. It mirrors the structure of the existing `emt-api` to allow seamless integration with Anjula's backend. It features:
- **Conversational Context** - Maintains history for multi-turn interactions
- **Bilingual Support** - Handles both English and Arabic
- **Full Security** - Same 7-layer security as the Agent Router
- **Specialized Logic** - Specifically tuned for SEL assessment data analysis

Think of this as the specialized consultant - an expert in one specific domain (SEL) who speaks multiple languages.'

**Query Router** (`/query/*`)
'This is for testing and administration. It includes endpoints like:
- `/query/sources` - What data sources would we use for this question?
- `/query/prepost` - Direct access to pre/post comparison data
- `/query/test-data` - Mock data for development

These endpoints have:
- Relaxed rate limits (30/minute)
- Admin-only access for some endpoints
- No LLM calls (direct data access)
- No harmful content scanning (not user-facing)

Think of this as the service entrance - still secure, but optimized for development and testing.'

**Prompt Eval Router** (`/prompt-eval/receive`)
'This is for machine-to-machine communication with our external Prompt Evaluation Tool. It:
- Uses token-based authentication (not JWT)
- Writes evaluation data to CSV asynchronously
- Doesn't block the main application

Think of this as the loading dock - specialized for a specific external integration.'

**Why separate routers?**
'Three reasons:
1. **Security isolation** - We can apply different security policies to each router
2. **Independent scaling** - We can rate-limit testing endpoints differently than production
3. **Fail-safe design** - If we need to disable testing endpoints in production, we just don't register that router. Simple.'"

---

## Section 4: Service Layer (3 minutes)

### Visual: Service Layer Components

"Now let's dive into the service layer - this is where the intelligence lives.

**Data Router** (`services/data_router.py`)
'This is our intelligent data orchestrator. When an educator asks a question like \"How is Sarah performing in math?\", the Data Router:

1. **Analyzes the question** using keyword matching
   - Sees \"performing\" → needs REAL assessment data
   - Sees \"math\" → needs subject-specific data
   - Returns: `[\"REAL\", \"CSV\"]`

2. **Fetches data** from the identified sources
   - Applies filters (student ID, classroom, grade level)
   - **Enforces school-level isolation** - only fetches data from the user's school
   - Returns an `AssessmentDataSet` with all relevant data

3. **Formats data for the AI**
   - Converts raw numbers into natural language
   - Example: \"Student scored 85% on pre-test, 92% on post-test (7% improvement)\"
   - Includes aggregated CSV data if available

**Why a separate Data Router?**
- Single point of control for all data access
- Easy to add new data sources (just update the router)
- Can add caching later without changing other code
- Enforces multi-tenant isolation (school-level boundaries)
- Independently testable'

**LLM Engine** (`services/llm_engine.py`)
'This is our AI interface. It:

1. **Builds comprehensive prompts** with:
   - System instructions (\"You are an educational data assistant...\")
   - Data context (the formatted data from Data Router)
   - User question
   - Safety guidelines (\"Never reveal student names...\")

2. **Calls Google Gemini API**
   - Uses the Gemini 1.5 Flash model
   - Handles rate limiting and retries
   - Manages API keys securely

3. **Provides fallback responses**
   - If Gemini is unavailable, uses mock responses
   - Still uses real CSV data if available
   - Ensures the system never goes completely down

**Why separate LLM Engine?**
- **Provider abstraction** - We can swap from Gemini to OpenAI or Claude with minimal code changes
- **Prompt versioning** - All prompts are centralized, easy to update
- **Cost control** - Can add caching, usage tracking
- **Security** - Centralized prompt injection prevention'

**CSV Data Service** (`services/csv_data.py`)
'This handles aggregated assessment data from CSV exports. It:
- Loads CSV files with pre/post assessment scores
- Filters by school, grade level, assessment type
- Computes pre/post comparisons and trends
- Provides program-level insights (not just individual students)

**Why separate CSV service?**
- Different data format (aggregated vs individual records)
- Different use case (program evaluation vs student monitoring)
- Easy to swap CSV files without code changes
- Supports both individual and classroom-level queries'

**Audit Logger** (`services/audit_logger.py`)
'This is our compliance engine. It:
- Logs every data access with full context
- Supports multiple sinks (Splunk, OpenSearch, webhooks)
- Implements automatic log rotation and compression
- Ensures logs are immutable (append-only)
- Includes compliance flags (FERPA, UNICEF, GDPR, COPPA)

**Why separate audit logger?**
- **FERPA requirement** - Must maintain 7-year audit trail
- **UNICEF requirement** - Must track purpose of access
- **Security** - Centralized logging prevents bypass
- **Compliance** - Structured format for regulatory audits'"

---

## Section 5: Data Flow (2 minutes)

### Visual: Complete Request Flow Diagram

"Let me walk you through what happens when an educator asks a question. This is the complete journey of a request:

**Steps 1-5: Security Gauntlet**
'First, the request goes through our security layers:
1. TLS encryption
2. JWT authentication (Auth0 or local)
3. Rate limiting check
4. Input sanitization (SQL/prompt injection)
5. Harmful content detection on the question

If any of these fail, the request is rejected immediately. We fail fast.'

**Steps 6-9: Authorization**
'Next, we check permissions:
6. Agent Router receives the request
7. Extracts school ID from the user's JWT token
8. Compares against the requested data
9. If cross-school access is attempted → 403 Forbidden

**This happens BEFORE we touch any student data.** We never fetch data the user isn't allowed to see.'

**Steps 10-12: Data Gathering**
'Now we can safely fetch data:
10. Data Router determines which sources to use (REAL, EMT, SEL, CSV)
11. Fetches data from those sources (school-filtered)
12. Formats data into natural language for the AI'

**Steps 13-15: AI Processing**
'The AI generates a response:
13. LLM Engine builds a comprehensive prompt
14. Calls Google Gemini API
15. Receives the AI-generated response'

**Steps 16-18: Final Security & Logging**
'Before returning to the educator:
16. Harmful content detection on the AI response
17. Audit logging (who, what, when, why)
18. Return response to educator

**Total time: Usually under 2 seconds.**'

**Why this specific order?**
'Three principles:
1. **Security first** - Authenticate before processing anything
2. **Early validation** - Check permissions BEFORE fetching data
3. **Audit everything** - Log all access attempts, successful or not'"

---

## Section 6: Design Decisions (3 minutes)

### Key Architectural Choices

"Let me explain some of the key design decisions and why we made them:

**1. Why FastAPI instead of Flask or Django?**
'Four reasons:
- **Async/await support** - We make multiple I/O calls (database, LLM API, audit logs). Async lets us handle these concurrently without blocking.
- **Type safety** - Pydantic models catch errors at development time, not in production
- **Auto-documentation** - We get OpenAPI/Swagger docs for free
- **Performance** - FastAPI is as fast as Node.js or Go, much faster than traditional Python frameworks'

**2. Why Auth0 instead of building our own authentication?**
'Security best practice: Don't roll your own auth. Auth0 gives us:
- **Enterprise-grade security** - RS256 JWT with JWKS verification
- **MFA support** - Multi-factor authentication out of the box
- **SSO capability** - Can integrate with Google Workspace, Microsoft 365
- **Compliance** - Auth0 is SOC 2, GDPR, HIPAA compliant
- **Hybrid mode** - We still support local dev with HS256 tokens

We get bank-level security without having to build and maintain it ourselves.'

**3. Why school-level isolation instead of fine-grained permissions?**
'We implemented school-level isolation first because:
- **Highest impact** - Prevents the most serious data breach (cross-school access)
- **Simpler to implement** - One check: user's school == data's school
- **Easier to audit** - Clear boundaries for compliance
- **Performance** - Single database query vs complex permission checks

We can add classroom-level and student-level permissions later, but school-level isolation gives us 80% of the security value with 20% of the complexity.'

**4. Why SQLite for development instead of PostgreSQL?**
'Pragmatic choice for the development phase:
- **Zero setup** - No database server to install or configure
- **File-based** - Easy to backup, version control, share
- **Fast** - Local file access is faster than network database
- **ACID compliant** - Still reliable for access control

**Migration path:** When we're ready for production scale, we can migrate to PostgreSQL with minimal code changes. Same SQL syntax, just swap the connection string.'

**5. Why separate routers instead of one big router?**
'Separation of concerns:
- **Agent Router** - Production, maximum security, full audit logging
- **Query Router** - Testing/admin, relaxed limits, direct data access
- **Prompt Eval Router** - External integration, async processing

This lets us:
- Apply different security policies per router
- Set different rate limits per router
- Disable testing endpoints in production (just don't register that router)
- Keep code organized and maintainable'

**6. Why immutable audit logs?**
'FERPA and UNICEF compliance require:
- **7-year retention** - Can't delete logs
- **Tamper-proof** - Can't modify logs
- **Append-only** - Can only add new entries
- **Structured format** - Must be analyzable for audits

Standard Python logging doesn't guarantee any of this. Our custom audit logger uses:
- Append-only file writes
- Automatic rotation and compression
- External sink support (Splunk, OpenSearch)
- Compliance flags in every log entry'"

---

## Section 7: Scalability & Future (2 minutes)

### Current vs Future Architecture

"Let me show you how this architecture scales:

**Current Architecture (Single Server)**
'Right now, everything runs on one server:
- FastAPI application
- All routers and services
- SQLite database
- Local audit logs

**This is perfect for:**
- Development and testing
- Small to medium deployments (up to ~1000 concurrent users)
- Single school or small district

**Future Architecture (Distributed)**
'When we need to scale, here's the migration path:

1. **Replace SQLite with PostgreSQL**
   - Minimal code changes (same SQL syntax)
   - Add connection pooling
   - Enable read replicas for better performance

2. **Deploy multiple API servers**
   - Stateless design means we can run multiple instances
   - Each instance handles requests independently
   - No session state to synchronize

3. **Add load balancer**
   - Nginx or HAProxy distributes requests
   - Health checks ensure only healthy servers receive traffic
   - SSL termination at the load balancer

4. **Centralize audit logs**
   - All servers send logs to Splunk or OpenSearch
   - Centralized analysis and compliance reporting
   - No more local log files

**The key point:** Our architecture is designed to scale horizontally. We can add more servers without changing the code.'

**What doesn't need to change:**
- Router architecture (still three routers)
- Service layer (still the same services)
- Security layers (still seven layers)
- Data flow (same request journey)

**What scales automatically:**
- Number of concurrent requests (add more servers)
- Database throughput (PostgreSQL read replicas)
- Audit log volume (external sinks handle it)'"

---

## Section 8: Security Posture (1 minute)

### Current Security Score

"Let me give you our current security scorecard:

**Overall Security: 9/10 (Excellent)**

**What's Production-Ready:**
- ✅ **Authentication: 9/10** - Auth0 integration with hybrid fallback
- ✅ **Authorization: 9/10** - School-level data isolation
- ✅ **Transport Security: 9/10** - TLS 1.3, HSTS headers
- ✅ **Input Validation: 9/10** - 20+ prompt injection patterns, 7 SQL injection patterns
- ✅ **Audit Logging: Implemented** - FERPA/UNICEF compliant
- ✅ **Harmful Content Detection: Implemented** - 13 harm types, UNICEF-aligned

**What's Remaining:**
- ⚠️ **PII Redaction: 3/10** - Not yet implemented (critical for production)
- ⚠️ **Fine-grained Access Control: Partial** - School-level done, classroom-level pending
- ⚠️ **MFA: Not configured** - Auth0 supports it, just needs to be enabled (5 minutes)

**Bottom line:** We're production-ready for authentication and authorization. The main remaining work is PII redaction in AI responses."

---

## Closing (1 minute)

"So to summarize, the Master Chatbot architecture is built on six key principles:

1. **Defense in Depth** - Seven layers of security, not just one
2. **Separation of Concerns** - Routers, services, and middleware each have clear responsibilities
3. **Fail-Safe Design** - Reject by default, allow explicitly
4. **Audit Everything** - Comprehensive logging for FERPA/UNICEF compliance
5. **Type Safety** - Pydantic models prevent runtime errors
6. **Scalability** - Designed to scale horizontally from day one

**The result is a system that:**
- ✅ Protects student data with enterprise-grade security
- ✅ Complies with FERPA and UNICEF requirements
- ✅ Scales from single school to district-wide deployment
- ✅ Maintains sub-2-second response times
- ✅ Provides comprehensive audit trails for compliance

**Questions?**"

---

## Q&A Preparation

### Common Questions & Answers

**Q: "Why not use a commercial chatbot platform like ChatGPT or Claude directly?"**
A: "Three reasons: 
1. **Data privacy** - We can't send student data to third-party platforms
2. **Compliance** - We need FERPA-compliant audit logging and access control
3. **Integration** - We need to connect to our specific data sources (REAL, EMT, SEL)

We use Google Gemini as the LLM engine, but we wrap it in our security and compliance layers."

**Q: "How do you prevent the AI from revealing student names or sensitive information?"**
A: "Three-layer approach:
1. **Prompt engineering** - We explicitly instruct the AI never to reveal names
2. **Data formatting** - We anonymize data before sending to the AI when possible
3. **PII redaction** - (Coming soon) We'll scan AI responses and redact any detected PII

This is defense in depth - multiple safeguards, not just one."

**Q: "What happens if Auth0 goes down?"**
A: "We have a hybrid authentication mode:
- **Primary**: Auth0 with RS256 JWT
- **Fallback**: Local JWT with HS256

If Auth0 is unavailable, we can switch to local mode. This requires manual configuration change, but ensures the system can stay operational."

**Q: "How do you handle data from multiple schools without mixing them up?"**
A: "School-level isolation is enforced at multiple points:
1. **JWT token** - Contains user's school_id
2. **Data Router** - Only fetches data for user's school
3. **Access control** - Rejects cross-school requests with 403 Forbidden
4. **Audit logging** - Logs all access attempts (successful and denied)

It's architecturally impossible for a user to access another school's data."

**Q: "Can this scale to handle thousands of schools?"**
A: "Yes, with the distributed architecture:
- **Horizontal scaling** - Add more API servers behind a load balancer
- **Database scaling** - PostgreSQL with read replicas
- **Caching** - Can add Redis for frequently accessed data
- **CDN** - Can add CloudFront or Cloudflare for static assets

The architecture is designed for this from day one."

**Q: "How long does it take to get a response?"**
A: "Typical response time: **1-2 seconds**

Breakdown:
- Security checks: ~50ms
- Data fetching: ~200ms
- LLM API call: ~1000ms
- Audit logging: ~50ms (async)

The LLM call is the bottleneck, but 1-2 seconds is acceptable for a conversational interface."

---

## Presentation Tips

### For Technical Audiences:
- Emphasize architectural patterns (defense in depth, separation of concerns)
- Dive deeper into specific technologies (FastAPI, Pydantic, Auth0)
- Discuss trade-offs and alternatives considered
- Show code examples if time permits

### For Non-Technical Audiences:
- Use analogies (fortress, VIP entrance, loading dock)
- Focus on outcomes (security, compliance, speed)
- Minimize jargon
- Use visual diagrams heavily

### For Executive Audiences:
- Lead with business value (FERPA compliance, risk mitigation)
- Emphasize security posture (9/10 score)
- Discuss scalability and future-proofing
- Keep technical details high-level

### For Compliance/Legal Audiences:
- Focus on FERPA and UNICEF compliance
- Emphasize audit logging and immutability
- Discuss data access controls and isolation
- Highlight 7-year retention capability

---

**End of Script**
