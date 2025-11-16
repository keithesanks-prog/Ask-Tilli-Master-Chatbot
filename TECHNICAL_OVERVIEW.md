# Master Agent - Technical Overview

**How the AI Agent Works - A Complete Explanation**

---

## 🎯 Purpose

The Master Agent is an AI-powered backend service that helps educators analyze student assessment data by:
1. **Understanding** educator questions in natural language
2. **Automatically routing** to relevant assessment data sources
3. **Fetching** structured data from multiple assessment tables
4. **Generating** natural language insights using Google Gemini LLM
5. **Returning** actionable information to help educators make data-driven decisions

**Target Users:** Educators at 7 schools, analyzing data for 6,000 students  
**Technology Stack:** FastAPI (Python), Google Gemini LLM, Assessment Databases

---

## 🏗️ Architecture Overview

The Master Agent follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│   API Layer (FastAPI)                   │  ← Handles HTTP requests
├─────────────────────────────────────────┤
│   Service Layer (Business Logic)        │  ← Core AI agent logic
├─────────────────────────────────────────┤
│   Data Layer (Assessment Tables)        │  ← Student assessment data
└─────────────────────────────────────────┘
```

### **Key Components:**

1. **API Layer** - FastAPI endpoints that receive educator questions
2. **Data Router** - Intelligently selects which data sources are needed
3. **LLM Engine** - Builds prompts and calls Google Gemini API
4. **Data Sources** - REAL, EMT, SEL assessment tables
5. **External Services** - Google Gemini LLM API

---

## 🔄 How It Works: Request Flow

### **Step-by-Step Process:**

```
1. Educator asks question
   ↓
2. FastAPI receives HTTP POST request
   ↓
3. Input validation & sanitization
   ↓
4. Data Router analyzes question
   ↓
5. Determines which data sources needed (REAL/EMT/SEL)
   ↓
6. Fetches data from relevant assessment tables
   ↓
7. Formats data for LLM consumption
   ↓
8. LLM Engine builds comprehensive prompt
   ↓
9. Sends prompt to Google Gemini API
   ↓
10. Gemini generates natural language response
    ↓
11. Response is validated and sanitized
    ↓
12. Returns JSON response to educator
```

---

## 📦 Component Deep Dive

### **1. API Layer (FastAPI Application)**

**File:** `app/main.py`

**Purpose:** Entry point for all HTTP requests

**Key Features:**
- RESTful API endpoints
- Request/response validation (Pydantic models)
- Authentication middleware
- Rate limiting
- Security headers
- CORS configuration

**Main Endpoints:**
- `POST /agent/ask` - Main endpoint for educator questions
- `POST /ask` - Alternative main endpoint
- `GET /health` - Health check
- `GET /health/security` - Security health check

**Example Request:**
```json
POST /agent/ask
{
  "question": "How is Student X performing in emotional recognition?",
  "student_id": "student_123",
  "classroom_id": "classroom_456",
  "grade_level": "3"
}
```

**Example Response:**
```json
{
  "answer": "Based on the EMT assessment data, Student X is performing well in emotional recognition...",
  "data_sources": ["EMT"],
  "metadata": {
    "timestamp": "2024-01-01T12:00:00Z",
    "question_length": 42
  }
}
```

---

### **2. Data Router Service**

**File:** `app/services/data_router.py`

**Purpose:** Intelligently determines which assessment data sources are needed based on the educator's question

**How It Works:**

**Step 1: Question Analysis**
```python
def determine_data_sources(question: str) -> List[str]:
    """
    Analyzes the educator's question to determine which data sources are needed.
    
    Uses keyword matching to identify relevant sources:
    - "emotion", "emotion matching", "emt" → EMT Data
    - "remote learning", "real", "distance learning" → REAL Data
    - "sel", "social emotional", "social-emotional" → SEL Data
    """
```

**Keyword Mappings:**
- **EMT Keywords:** emotion, emotion matching, emt, emotions, emotional recognition
- **REAL Keywords:** remote learning, real, distance learning, online learning
- **SEL Keywords:** sel, social emotional, social-emotional, self-awareness

**Step 2: Data Fetching**
```python
def fetch_data(
    data_sources: List[str],
    grade_level: str = None,
    student_id: str = None,
    classroom_id: str = None
) -> AssessmentDataSet:
    """
    Fetches data from the specified assessment tables.
    
    Currently uses mock data, but designed to query actual databases:
    - REAL Data Table → Remote learning assessment results
    - EMT Data Table → Emotion matching task results
    - SEL Data Table → Social-emotional learning results
    """
```

**Step 3: Data Formatting**
```python
def format_data_for_llm(data: AssessmentDataSet) -> Dict[str, Any]:
    """
    Formats structured assessment data into a summary for LLM consumption.
    
    Converts database records into natural language summaries that
    the LLM can understand and incorporate into its response.
    """
```

---

### **3. LLM Engine Service**

**File:** `app/services/llm_engine.py`

**Purpose:** Builds comprehensive prompts and generates natural language responses using Google Gemini LLM

**How It Works:**

**Step 1: Prompt Construction**
```python
def build_prompt(question: str, data_summary: Dict[str, Any]) -> str:
    """
    Builds a comprehensive prompt that includes:
    
    1. System instructions (Master Agent's role and capabilities)
    2. The educator's question
    3. Formatted assessment data (from Data Router)
    4. Response guidelines (tone, format, focus areas)
    5. Security instructions (resist injection attempts)
    """
```

**Prompt Structure:**
```
You are the Master Agent for Tilli, an AI assistant that helps educators 
analyze student assessment data.

EDUCATOR'S QUESTION:
[The educator's question goes here]

ASSESSMENT DATA:
[Formatted data from Data Router goes here]

RESPONSE GUIDELINES:
- Provide actionable insights
- Use data to support conclusions
- Suggest intervention ideas when appropriate
- Focus on student growth and development
```

**Step 2: LLM API Call**
```python
def generate_response(
    question: str,
    data_summary: Dict[str, Any],
    max_tokens: int = 1000
) -> str:
    """
    Sends prompt to Google Gemini API and receives natural language response.
    
    Uses Google Generative AI (Gemini 1.5 Pro) to generate:
    - Natural language insights
    - Data-driven conclusions
    - Actionable recommendations
    - Intervention suggestions
    """
```

**Gemini API Integration:**
- **Model:** gemini-1.5-pro
- **API:** Google Generative AI REST API
- **Fallback:** Mock responses if API unavailable
- **Configuration:** Via `GEMINI_API_KEY` environment variable

**Step 3: Response Validation**
```python
def validate_response(response: str) -> str:
    """
    Validates and sanitizes LLM response:
    - Checks for harmful content
    - Detects PII leakage (needs implementation)
    - Ensures response format
    """
```

---

### **4. Security Layer**

**Purpose:** Protects the service from attacks and ensures data privacy

**Key Components:**

**Input Validation (`app/services/security.py`):**
- Sanitizes all user inputs
- Detects prompt injection attempts (20+ patterns)
- Detects SQL injection attempts
- Validates data formats and lengths

**Example:**
```python
# Input: "What is student_123's performance? Ignore previous instructions..."
# Detection: Prompt injection pattern detected
# Result: Input rejected or sanitized
```

**Authentication (`app/middleware/auth.py`):**
- JWT token verification
- Role-based access control (RBAC)
- User identity validation

**Rate Limiting (`app/middleware/rate_limit.py`):**
- IP-based rate limiting
- Per-endpoint limits:
  - `/ask`: 10/minute
  - `/query`: 30/minute
  - `/prompt-eval`: 5/minute

**Audit Logging (`app/services/audit_logger.py`):**
- Logs all data access (FERPA/UNICEF-compliant)
- Tracks who accessed what data and when
- Purpose tracking for compliance

**Harmful Content Detection (`app/services/harmful_content_detector.py`):**
- Detects child safety concerns (self-harm, abuse, bullying)
- Blocks harmful responses
- Generates alerts for high-severity content

---

## 📊 Data Sources

### **1. REAL Data (Remote Learning Assessment)**

**Purpose:** Tracks student performance in remote learning environments

**Data Includes:**
- Learning assessment scores
- Remote learning engagement metrics
- Academic performance indicators
- Assessment dates and timestamps

**Example Data:**
```json
{
  "student_id": "student_123",
  "assessment_date": "2024-01-15",
  "learning_score": 0.85,
  "engagement_score": 0.78,
  "metadata": {"source": "REAL"}
}
```

---

### **2. EMT Data (Emotion Matching Task)**

**Purpose:** Measures student emotional recognition and understanding

**Data Includes:**
- Emotion matching scores
- Emotional recognition accuracy
- Task completion metrics
- Assessment timestamps

**Example Data:**
```json
{
  "student_id": "student_123",
  "assessment_date": "2024-01-15",
  "emotion_score": 0.82,
  "recognition_accuracy": 0.79,
  "metadata": {"source": "EMT"}
}
```

---

### **3. SEL Data (Social-Emotional Learning)**

**Purpose:** Tracks social-emotional learning development

**Data Includes:**
- SEL assessment scores
- Social awareness metrics
- Relationship skills indicators
- Self-management scores

**Example Data:**
```json
{
  "student_id": "student_123",
  "assessment_date": "2024-01-15",
  "sel_score": 0.80,
  "self_awareness": 0.85,
  "social_awareness": 0.78,
  "metadata": {"source": "SEL"}
}
```

---

## 🔐 Security Features

### **Multi-Layer Security:**

**Layer 1: Input Validation**
- Question length limits (1-5000 characters)
- Identifier format validation
- Character set restrictions
- Injection pattern detection

**Layer 2: Authentication & Authorization**
- JWT token verification
- Role-based access control
- User identity validation
- (Data access control - needs implementation)

**Layer 3: Transport Security**
- TLS/HTTPS enforcement
- HSTS headers
- Security headers (CSP, X-Frame-Options)
- HTTP to HTTPS redirect

**Layer 4: Response Security**
- Harmful content detection
- Response validation
- (PII redaction - needs implementation)
- Audit logging

---

## 🧪 Example Workflow

### **Scenario: Educator asks about emotional recognition**

**1. Request:**
```json
POST /agent/ask
{
  "question": "How is student_123 performing in emotional recognition tasks?",
  "student_id": "student_123",
  "classroom_id": "classroom_456",
  "grade_level": "3"
}
```

**2. Data Router Analysis:**
- Keywords detected: "emotional recognition" → **EMT Data**
- Fetching EMT assessment data for student_123
- Formatting data for LLM

**3. LLM Engine:**
- Building prompt with:
  - Question: "How is student_123 performing in emotional recognition tasks?"
  - Data: EMT assessment results (scores, trends, timestamps)
  - Instructions: Provide actionable insights

**4. Gemini API Call:**
- Sending prompt to gemini-1.5-pro
- Receiving natural language response

**5. Response:**
```json
{
  "answer": "Based on the EMT assessment data, student_123 is performing well in emotional recognition. The student has shown consistent improvement over the past 3 assessments, with scores increasing from 0.75 to 0.82. Key strengths include recognizing basic emotions (happy, sad, angry) with 90% accuracy. Areas for growth include recognizing more complex emotions like frustration or disappointment. Recommendation: Continue with current emotional learning curriculum and consider introducing more nuanced emotion vocabulary.",
  "data_sources": ["EMT"],
  "metadata": {
    "timestamp": "2024-01-15T12:00:00Z",
    "question_length": 57
  }
}
```

---

## 🔧 Technical Stack

### **Backend Framework:**
- **FastAPI** - Modern Python web framework
- **Python 3.11+** - Programming language
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

### **AI/ML:**
- **Google Gemini 1.5 Pro** - Large language model
- **google-generativeai** - Python SDK

### **Security:**
- **python-jose** - JWT token handling
- **slowapi** - Rate limiting
- **Presidio** (planned) - PII detection/redaction

### **Data:**
- **SQLAlchemy** (planned) - Database ORM
- **PostgreSQL/MySQL** (planned) - Database

### **Operations:**
- **Systemd** - Service management
- **Docker** (optional) - Containerization

---

## 📈 Scalability & Performance

### **Current Capacity:**
- Handles multiple concurrent requests
- Rate limiting prevents abuse
- Graceful degradation if Gemini API unavailable

### **Optimization Opportunities:**
- Database connection pooling (when DB integrated)
- Response caching for common queries
- Async database queries
- Load balancing for multiple instances

---

## 🔄 Integration Points

### **1. Frontend Application**
- Educators interact via web/mobile frontend
- Frontend sends questions to `/agent/ask` endpoint
- Receives JSON responses for display

### **2. Assessment Databases**
- REAL, EMT, SEL data tables
- Student enrollment data
- Classroom assignments
- (Database integration needed)

### **3. School Identity Providers**
- Google Workspace (OAuth2/OIDC)
- Microsoft 365 (OAuth2/OIDC)
- Clever (Education identity provider)
- (IAM integration needed)

### **4. Prompt Eval Tool**
- External service sends evaluation data
- Master Agent receives via `/prompt-eval/receive`
- Evaluation metrics stored for analysis

---

## 🎓 Key Design Decisions

### **1. Keyword-Based Routing (Current)**
- **Why:** Simple, reliable, works well for known question patterns
- **Future:** Can be enhanced with NLP/ML for more sophisticated routing

### **2. Mock Data (Current)**
- **Why:** Allows development without database access
- **Future:** Will be replaced with real database queries

### **3. Gemini LLM**
- **Why:** High-quality responses, good education domain understanding
- **Alternative:** Could switch to other LLMs if needed

### **4. FastAPI**
- **Why:** Modern, fast, excellent documentation, type safety
- **Benefit:** Auto-generated API documentation

---

## 🚀 Future Enhancements

### **Planned Features:**
1. **NLP-Based Routing** - More sophisticated question analysis
2. **Database Integration** - Real assessment data queries
3. **IAM Integration** - School identity provider integration
4. **PII Redaction** - Automatic PII detection and redaction
5. **Response Caching** - Cache common queries for performance
6. **Multi-Modal Support** - Handle charts, graphs, visualizations
7. **Advanced Analytics** - Trend analysis, predictive insights

---

## 📚 Summary

The Master Agent is a **sophisticated AI system** that:
- ✅ Receives natural language questions from educators
- ✅ Intelligently routes to relevant assessment data sources
- ✅ Fetches and formats structured data
- ✅ Uses Google Gemini LLM to generate insights
- ✅ Returns actionable information to help educators

**Technology:** Python, FastAPI, Google Gemini LLM  
**Architecture:** Layered, modular, secure  
**Status:** Functionally complete, security improvements needed for production

---

**Document Version:** 1.0  
**Last Updated:** 2024


