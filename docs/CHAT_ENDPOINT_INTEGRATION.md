# Chat Endpoint Integration Guide

**Document Version:** 1.0  
**Last Updated:** 2025-11-24  
**Purpose:** Complete integration guide for the `/chat` endpoint that mirrors the emt-api structure

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [API Specification](#api-specification)
- [Request/Response Format](#requestresponse-format)
- [Integration Steps](#integration-steps)
- [Security Features](#security-features)
- [Code Examples](#code-examples)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## Overview

The `/chat` endpoint provides a conversational interface for SEL (Social Emotional Learning) assessment analysis. It mirrors the emt-api `chat()` function structure, allowing Anjula's backend to call the Master Chatbot as a service.

### Key Features

- ✅ **Conversational Interface**: Supports multi-turn conversations with history
- ✅ **SEL Assessment Analysis**: Processes 4 assessment types (child, parent, teacher_report, teacher_survey)
- ✅ **Bilingual Support**: Responds in Arabic or English based on input language
- ✅ **Security Integration**: Full Auth0, sanitization, harmful content detection, audit logging
- ✅ **emt-api Compatible**: Exact same request/response structure

### Scope for UNRWA Pilot

**Included**: REAL and SEL assessments  
**Excluded**: EMT (Emotion Matching Tasks) - not part of UNRWA pilot

---

## Architecture

### System Flow

```
┌─────────────────┐
│  Frontend/      │
│  Backend Client │
└────────┬────────┘
         │
         │ POST /chat
         │ {message, scores, history}
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Master Chatbot API                                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Security Layers                                │   │
│  │  • Auth0 JWT Verification                       │   │
│  │  • Input Sanitization                           │   │
│  │  • Harmful Content Detection                    │   │
│  │  • Rate Limiting (10 req/min)                   │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                              │
│                          ▼                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Chat Router (/chat)                            │   │
│  │  • Validate ChatRequest                         │   │
│  │  • Build conversation context                   │   │
│  │  • Add system instruction for SEL               │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                              │
│                          ▼                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  LLM Engine                                     │   │
│  │  • generate_chat_response()                     │   │
│  │  • Gemini 2.5 Pro API                           │   │
│  │  • Conversation history support                 │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                              │
│                          ▼                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Audit Logger                                   │   │
│  │  • Log all chat interactions                    │   │
│  │  • FERPA compliance                             │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         │
         │ ChatResponse
         │ {response: "text"}
         │
         ▼
┌─────────────────┐
│  Client         │
│  Receives       │
│  Response       │
└─────────────────┘
```

### Component Breakdown

| Component | File | Purpose |
|-----------|------|---------|
| **Chat Models** | `app/models/chat_models.py` | Pydantic models for request/response |
| **Chat Router** | `app/routers/chat.py` | FastAPI endpoint handler |
| **LLM Engine** | `app/services/llm_engine.py` | Gemini API integration |
| **Security** | `app/middleware/auth.py` | Authentication & authorization |
| **Audit Logger** | `app/services/audit_logger.py` | FERPA-compliant logging |

---

## API Specification

### Endpoint

```
POST /chat
```

### Authentication

**Required**: Yes (unless `ENABLE_AUTH=false` in development)

**Method**: Bearer token (JWT)

**Headers**:
```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Token Requirements**:
- `user_id` or `sub`: User identifier
- `role`: User role (educator, admin)
- `school_id`: School identifier for data isolation

### Rate Limiting

**Limit**: 10 requests per minute per user

**Response on Limit Exceeded**:
```json
{
  "error": "Rate limit exceeded"
}
```

---

## Request/Response Format

### Request Structure

```json
{
  "message": "string",
  "scores": {
    "child": { /* assessment data */ },
    "parent": { /* assessment data */ },
    "teacher_report": { /* assessment data */ },
    "teacher_survey": { /* assessment data */ }
  },
  "history": [
    {
      "role": "user",
      "text": "previous question"
    },
    {
      "role": "assistant",
      "text": "previous response"
    }
  ]
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✅ Yes | Current user question/message |
| `scores` | object | ❌ No | SEL assessment scores (4 assessment types) |
| `history` | array | ❌ No | Previous conversation messages |

### SEL Scores Structure

Each assessment (child, parent, teacher_report, teacher_survey) follows this structure:

```json
{
  "testType": "PRE",  // or "POST"
  "totalStudents": 25,
  "school": "Lincoln High School",
  "assessment": "child",  // child, parent, teacher_report, teacher_survey
  "skills": {
    "self_awareness": {
      "beginner": 5,
      "growth": 12,
      "expert": 8
    },
    "self_management": {
      "beginner": 3,
      "growth": 15,
      "expert": 7
    },
    "social_awareness": {
      "beginner": 4,
      "growth": 13,
      "expert": 8
    },
    "relationship_skills": {
      "beginner": 6,
      "growth": 11,
      "expert": 8
    },
    "responsible_decision_making": {
      "beginner": 5,
      "growth": 10,
      "expert": 10
    }
  }
}
```

### Response Structure

```json
{
  "response": "string"
}
```

**Simple**: Just a plain text response (matches emt-api format)

### Example Request/Response

**Request**:
```json
{
  "message": "How are students performing in self-awareness?",
  "scores": {
    "child": {
      "testType": "PRE",
      "totalStudents": 25,
      "school": "Lincoln High School",
      "assessment": "child",
      "skills": {
        "self_awareness": {"beginner": 5, "growth": 12, "expert": 8}
      }
    }
  },
  "history": []
}
```

**Response**:
```json
{
  "response": "Based on the child assessment data for 25 students at Lincoln High School, self-awareness shows a positive distribution: 8 students (32%) are at expert level, 12 students (48%) are showing growth, and 5 students (20%) are at beginner level. This indicates that 80% of students have developed or are developing self-awareness skills. Consider providing additional support for the 5 students at beginner level through targeted activities focused on emotion recognition and self-reflection."
}
```

---

## Integration Steps

### Step 1: Authentication Setup

**Option A: Using Auth0 (Recommended for Production)**

1. Set up Auth0 tenant (see `docs/AUTH0_SETUP_GUIDE.md`)
2. Configure environment variables:
   ```bash
   export AUTH0_DOMAIN=your-tenant.us.auth0.com
   export AUTH0_AUDIENCE=https://api.tilli.com/chatbot
   export ENABLE_AUTH=true
   ```
3. Obtain JWT token from Auth0
4. Include token in requests

**Option B: Local Development (Testing Only)**

1. Disable authentication:
   ```bash
   export ENABLE_AUTH=false
   ```
2. Make requests without token

### Step 2: Make API Request

**Python Example**:
```python
import requests

url = "http://localhost:8000/chat"
headers = {
    "Authorization": "Bearer <your-jwt-token>",
    "Content-Type": "application/json"
}

payload = {
    "message": "How are students performing in self-awareness?",
    "scores": {
        "child": {
            "testType": "PRE",
            "totalStudents": 25,
            "school": "Lincoln High School",
            "assessment": "child",
            "skills": {
                "self_awareness": {"beginner": 5, "growth": 12, "expert": 8}
            }
        }
    },
    "history": []
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

**JavaScript Example**:
```javascript
const response = await fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer <your-jwt-token>',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'How are students performing in self-awareness?',
    scores: {
      child: {
        testType: 'PRE',
        totalStudents: 25,
        school: 'Lincoln High School',
        assessment: 'child',
        skills: {
          self_awareness: { beginner: 5, growth: 12, expert: 8 }
        }
      }
    },
    history: []
  })
});

const data = await response.json();
console.log(data.response);
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How are students performing in self-awareness?",
    "scores": {
      "child": {
        "testType": "PRE",
        "totalStudents": 25,
        "school": "Lincoln High School",
        "assessment": "child",
        "skills": {
          "self_awareness": {"beginner": 5, "growth": 12, "expert": 8}
        }
      }
    },
    "history": []
  }'
```

### Step 3: Handle Conversation History

**Multi-turn Conversation Example**:

```python
# First message
history = []
response1 = make_chat_request(
    message="How are students performing in self-awareness?",
    scores=sel_scores,
    history=history
)

# Add to history
history.append({
    "role": "user",
    "text": "How are students performing in self-awareness?"
})
history.append({
    "role": "assistant",
    "text": response1["response"]
})

# Second message (with context)
response2 = make_chat_request(
    message="What about self-management skills?",
    scores=sel_scores,
    history=history
)

# Continue building history...
```

---

## Security Features

### 1. Authentication & Authorization

**Enforcement**:
- JWT token verification (Auth0 RS256 or local HS256)
- User identity validation
- School-level data isolation

**Configuration**:
```bash
export ENABLE_AUTH=true
export AUTH0_DOMAIN=your-tenant.us.auth0.com
export AUTH0_AUDIENCE=https://api.tilli.com/chatbot
```

### 2. Input Sanitization

**Protection Against**:
- Prompt injection attacks
- SQL injection attempts
- XSS attacks
- Malicious input patterns

**Implementation**: Automatic (handled by middleware)

### 3. Harmful Content Detection

**Detects**:
- Self-harm indicators
- Abuse/bullying content
- Inappropriate language
- Data misuse attempts

**Action**: Blocks request and logs incident

### 4. Rate Limiting

**Limits**:
- 10 requests per minute per endpoint
- IP-based and user-based tracking
- Redis-backed for production

### 5. Audit Logging

**Logs**:
- All chat interactions
- User identity and school
- Timestamps and request details
- Security events

**Compliance**: FERPA 7-year retention

---

## Code Examples

### Complete Integration Example

```python
"""
Complete example of integrating with the Master Chatbot /chat endpoint
"""
import requests
from typing import List, Dict, Any, Optional

class MasterChatbotClient:
    """Client for Master Chatbot /chat endpoint"""
    
    def __init__(self, base_url: str, auth_token: str):
        """
        Initialize client.
        
        Args:
            base_url: Base URL of Master Chatbot API (e.g., http://localhost:8000)
            auth_token: JWT authentication token
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.history: List[Dict[str, str]] = []
    
    def chat(
        self,
        message: str,
        scores: Optional[Dict[str, Any]] = None,
        include_history: bool = True
    ) -> str:
        """
        Send a chat message and get response.
        
        Args:
            message: User's question/message
            scores: SEL assessment scores (optional)
            include_history: Whether to include conversation history
            
        Returns:
            Response text from the chatbot
        """
        url = f"{self.base_url}/chat"
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": message,
            "scores": scores or {},
            "history": self.history if include_history else []
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        response_text = data["response"]
        
        # Update history
        if include_history:
            self.history.append({"role": "user", "text": message})
            self.history.append({"role": "assistant", "text": response_text})
        
        return response_text
    
    def reset_history(self):
        """Clear conversation history"""
        self.history = []

# Usage example
if __name__ == "__main__":
    # Initialize client
    client = MasterChatbotClient(
        base_url="http://localhost:8000",
        auth_token="your-jwt-token-here"
    )
    
    # Sample SEL scores
    sel_scores = {
        "child": {
            "testType": "PRE",
            "totalStudents": 25,
            "school": "Lincoln High School",
            "assessment": "child",
            "skills": {
                "self_awareness": {"beginner": 5, "growth": 12, "expert": 8},
                "self_management": {"beginner": 3, "growth": 15, "expert": 7}
            }
        }
    }
    
    # First question
    response1 = client.chat(
        message="How are students performing in self-awareness?",
        scores=sel_scores
    )
    print(f"Response 1: {response1}\n")
    
    # Follow-up question (uses history)
    response2 = client.chat(
        message="What about self-management?",
        scores=sel_scores
    )
    print(f"Response 2: {response2}\n")
    
    # Reset for new conversation
    client.reset_history()
```

### Error Handling Example

```python
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout

def safe_chat_request(message: str, scores: dict, history: list, auth_token: str):
    """
    Make a chat request with comprehensive error handling.
    """
    url = "http://localhost:8000/chat"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "message": message,
        "scores": scores,
        "history": history
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()["response"]
        
    except HTTPError as e:
        if e.response.status_code == 401:
            print("Authentication failed. Check your token.")
        elif e.response.status_code == 403:
            print("Access denied. Check your permissions.")
        elif e.response.status_code == 422:
            print("Invalid request format. Check your payload.")
        elif e.response.status_code == 429:
            print("Rate limit exceeded. Wait before retrying.")
        else:
            print(f"HTTP error: {e}")
        return None
        
    except ConnectionError:
        print("Cannot connect to server. Is it running?")
        return None
        
    except Timeout:
        print("Request timed out. Try again.")
        return None
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

---

## Testing

### Manual Testing

**1. Start the server**:
```bash
cd Master-Chatbot
python -m uvicorn app.main:app --reload
```

**2. Test with provided script**:
```bash
python test_chat_endpoint.py
```

**3. Test with cURL**:
```bash
# Without authentication (development mode)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How are students performing?",
    "scores": {},
    "history": []
  }'
```

### Automated Testing

**Unit Tests** (to be created):
```python
# tests/test_chat_endpoint.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_endpoint_basic():
    """Test basic chat endpoint functionality"""
    response = client.post("/chat", json={
        "message": "How are students performing?",
        "scores": {},
        "history": []
    })
    assert response.status_code in [200, 401]  # 401 if auth enabled

def test_chat_with_history():
    """Test chat with conversation history"""
    response = client.post("/chat", json={
        "message": "What about self-management?",
        "scores": {},
        "history": [
            {"role": "user", "text": "How are students doing?"},
            {"role": "assistant", "text": "Students are doing well."}
        ]
    })
    assert response.status_code in [200, 401]
```

---

## Production Deployment

### Environment Configuration

**Required Environment Variables**:
```bash
# Authentication
export ENABLE_AUTH=true
export AUTH0_DOMAIN=your-tenant.us.auth0.com
export AUTH0_AUDIENCE=https://api.tilli.com/chatbot

# LLM API
export GEMINI_API_KEY=your-gemini-api-key

# Security
export ENVIRONMENT=production
export REQUIRE_TLS=true
export ENFORCE_HTTPS=true

# CORS
export ALLOWED_ORIGINS=https://your-frontend.com

# Rate Limiting
export REDIS_URL=redis://your-redis:6379/0

# Audit Logging
export AUDIT_SINKS=splunk,webhook
export SPLUNK_HEC_URL=https://splunk.example.com:8088/services/collector
export SPLUNK_HEC_TOKEN=your-token
```

### Deployment Checklist

- [ ] Set `ENABLE_AUTH=true`
- [ ] Configure Auth0 credentials
- [ ] Set `GEMINI_API_KEY` for real LLM responses
- [ ] Configure CORS origins (no wildcards)
- [ ] Set up Redis for rate limiting
- [ ] Configure audit log sinks
- [ ] Enable TLS/HTTPS
- [ ] Test authentication flow
- [ ] Test rate limiting
- [ ] Verify audit logging
- [ ] Load testing
- [ ] Security scan

### Cloud Deployment

See `CLOUD_DEPLOYMENT.md` for detailed cloud deployment instructions for:
- Google Cloud Run
- AWS ECS Fargate
- Kubernetes (GKE/EKS/AKS)

---

## Troubleshooting

### Common Issues

#### 1. Authentication Errors (401 Unauthorized)

**Symptoms**:
```json
{"detail": "Not authenticated"}
```

**Solutions**:
- Verify `ENABLE_AUTH` is set correctly
- Check JWT token is valid and not expired
- Ensure token includes required claims (user_id, role, school_id)
- Verify Auth0 configuration (domain, audience)

#### 2. Rate Limit Exceeded (429)

**Symptoms**:
```json
{"error": "Rate limit exceeded"}
```

**Solutions**:
- Wait 1 minute before retrying
- Implement exponential backoff
- Consider upgrading rate limits for production

#### 3. Validation Errors (422)

**Symptoms**:
```json
{"detail": [{"loc": ["body", "message"], "msg": "field required"}]}
```

**Solutions**:
- Verify request payload matches schema
- Ensure `message` field is present
- Check `scores` and `history` are properly formatted

#### 4. Server Not Responding

**Symptoms**:
- Connection refused
- Timeout errors

**Solutions**:
- Verify server is running: `curl http://localhost:8000/health`
- Check server logs for errors
- Ensure correct port (default: 8000)

#### 5. Empty or Error Responses

**Symptoms**:
```json
{"response": "Chat functionality requires Gemini API configuration..."}
```

**Solutions**:
- Set `GEMINI_API_KEY` environment variable
- Verify API key is valid
- Check Gemini API quota/billing

---

## Additional Resources

- **Main Documentation**: `README.md`
- **Auth0 Setup**: `docs/AUTH0_SETUP_GUIDE.md`
- **Security Guide**: `SECURITY_ASSESSMENT.md`
- **Audit Logging**: `AUDIT_LOGGING.md`
- **Cloud Deployment**: `CLOUD_DEPLOYMENT.md`
- **API Reference**: Interactive docs at `/docs` when server is running

---

## Support

For issues or questions:
1. Check this documentation
2. Review server logs
3. Test with `/health` endpoint
4. Check security health at `/health/security`

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-24
