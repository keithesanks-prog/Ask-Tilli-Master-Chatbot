# External API Security Considerations

**Document Version:** 1.0  
**Last Updated:** 2024  
**Focus:** Gemini LLM API and other external API security

---

## Overview

This document outlines security considerations for external API calls, particularly the Gemini LLM API, and identifies security measures that should be implemented.

---

## 🔴 **CRITICAL SECURITY CONSIDERATIONS**

### 1. **API Key Management** 🔴 **CRITICAL**

**Current Implementation:**
- ✅ API key stored in environment variable (`GEMINI_API_KEY`)
- ✅ Not hardcoded in source code
- ✅ Falls back to mock if key is missing

**Missing/Needed:**

#### **1.1 Secret Management** ⚠️ **RECOMMENDED**
- ❌ **Not using secret management service** (AWS Secrets Manager, HashiCorp Vault, etc.)
- ❌ **No automatic rotation** - Manual rotation only
- ❌ **No key rotation policy** - Keys should be rotated regularly

**Recommended Implementation:**
```python
# Use AWS Secrets Manager (example)
import boto3
from botocore.exceptions import ClientError

def get_gemini_api_key():
    secret_name = "gemini/api-key"
    region_name = "us-east-1"
    
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        logger.error(f"Error retrieving API key: {str(e)}")
        raise
```

#### **1.2 API Key Security Best Practices**
- ✅ Store in environment variable (development)
- ⚠️ **Production:** Use secret management service
- ⚠️ **Never log API keys** - Check logs for accidental exposure
- ⚠️ **Rotate keys regularly** - Quarterly minimum
- ⚠️ **Monitor key usage** - Alert on unusual usage patterns
- ⚠️ **Revoke compromised keys immediately**

---

### 2. **API Rate Limiting & Quota Management** 🔴 **CRITICAL**

**Current Implementation:**
- ❌ **No rate limiting on Gemini API calls** - Could exhaust quota
- ❌ **No cost controls/budget limits** - Could incur unexpected costs
- ❌ **No quota monitoring** - No alerts on quota exhaustion

**Missing/Needed:**

#### **2.1 Rate Limiting for External API Calls** ⚠️ **RECOMMENDED**
```python
from functools import wraps
import time
from collections import deque

class GeminiRateLimiter:
    """Rate limiter for Gemini API calls."""
    
    def __init__(self, max_calls_per_minute: int = 60, max_calls_per_day: int = 10000):
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_day = max_calls_per_day
        self.minute_calls = deque()
        self.daily_calls = deque()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        
        # Clean old minute calls
        while self.minute_calls and self.minute_calls[0] < now - 60:
            self.minute_calls.popleft()
        
        # Clean old daily calls
        while self.daily_calls and self.daily_calls[0] < now - 86400:
            self.daily_calls.popleft()
        
        # Check minute limit
        if len(self.minute_calls) >= self.max_calls_per_minute:
            sleep_time = 60 - (now - self.minute_calls[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, waiting {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        # Check daily limit
        if len(self.daily_calls) >= self.max_calls_per_day:
            raise Exception("Daily API quota exceeded")
        
        # Record call
        self.minute_calls.append(now)
        self.daily_calls.append(now)
```

#### **2.2 Cost/Budget Controls** ⚠️ **RECOMMENDED**
```python
class BudgetMonitor:
    """Monitor API usage costs."""
    
    def __init__(self, daily_budget: float = 100.0, cost_per_1k_tokens: float = 0.001):
        self.daily_budget = daily_budget
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.daily_spend = 0.0
        self.last_reset = time.time()
    
    def check_budget(self, tokens: int):
        """Check if request would exceed budget."""
        # Reset daily spend if new day
        if time.time() - self.last_reset > 86400:
            self.daily_spend = 0.0
            self.last_reset = time.time()
        
        estimated_cost = (tokens / 1000) * self.cost_per_1k_tokens
        
        if self.daily_spend + estimated_cost > self.daily_budget:
            raise Exception(f"Daily budget exceeded: ${self.daily_spend:.2f}/{self.daily_budget:.2f}")
        
        self.daily_spend += estimated_cost
        return True
```

#### **2.3 Quota Monitoring & Alerting** ⚠️ **RECOMMENDED**
- Monitor API usage daily/hourly
- Alert when 80% of quota reached
- Alert on quota exhaustion
- Track cost trends

---

### 3. **API Response Validation** 🔴 **CRITICAL**

**Current Implementation:**
- ✅ Harmful content detection on responses (implemented)
- ✅ Response length checks (implicit)
- ⚠️ **No explicit size limits** on API responses
- ⚠️ **No response format validation** (JSON structure, etc.)
- ⚠️ **No timeout on API calls** - Could hang indefinitely

**Missing/Needed:**

#### **3.1 Response Size Limits** ⚠️ **RECOMMENDED**
```python
MAX_RESPONSE_SIZE = 10000  # 10KB max response
MAX_TOKENS = 1000

def generate_response(self, question: str, data_summary: Dict[str, Any], max_tokens: int = MAX_TOKENS):
    # Enforce token limit
    if max_tokens > MAX_TOKENS:
        max_tokens = MAX_TOKENS
        logger.warning(f"Token limit capped at {MAX_TOKENS}")
    
    # ... API call ...
    
    if response and response.text:
        response_text = response.text.strip()
        
        # Check size limit
        if len(response_text) > MAX_RESPONSE_SIZE:
            logger.warning(f"Response too large: {len(response_text)} bytes")
            response_text = response_text[:MAX_RESPONSE_SIZE] + "... [truncated]"
        
        return response_text
```

#### **3.2 Timeout Handling** ⚠️ **RECOMMENDED**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError

TIMEOUT_SECONDS = 30  # 30 second timeout

def generate_response_with_timeout(self, question: str, data_summary: Dict[str, Any]):
    """Generate response with timeout protection."""
    try:
        with ThreadPoolExecutor() as executor:
            future = executor.submit(
                self.model.generate_content,
                self.build_prompt(question, data_summary),
                generation_config=self.generation_config
            )
            response = future.result(timeout=TIMEOUT_SECONDS)
            return response.text if response and response.text else None
    except TimeoutError:
        logger.error(f"Gemini API call timed out after {TIMEOUT_SECONDS}s")
        raise Exception("API call timed out. Please try again.")
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        raise
```

#### **3.3 Response Format Validation** ⚠️ **RECOMMENDED**
- Validate response is valid text (not binary)
- Check for unexpected characters
- Validate response structure (if structured response expected)

---

### 4. **Data Privacy & FERPA/UNICEF Compliance** 🔴 **CRITICAL**

**Current Implementation:**
- ✅ Student data is sent to Gemini (required for functionality)
- ✅ Harmful content detection on responses
- ⚠️ **No data anonymization before sending to Gemini**
- ⚠️ **Need to verify Gemini's data usage policy** (does Gemini train on sent data?)
- ⚠️ **No audit logging of data sent to external APIs**

**Missing/Needed:**

#### **4.1 Data Anonymization** ⚠️ **RECOMMENDED**
```python
def anonymize_data_for_api(data_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Anonymize student data before sending to external API.
    
    Replaces student_id with anonymized tokens.
    Removes personally identifiable information.
    """
    anonymized = copy.deepcopy(data_summary)
    
    # Replace student_id with anonymized token
    if 'student_id' in anonymized:
        anonymized['student_id'] = hash_student_id(anonymized['student_id'])
    
    # Remove PII from metadata
    if 'metadata' in anonymized:
        anonymized['metadata'] = {
            k: v for k, v in anonymized['metadata'].items()
            if k not in ['email', 'phone', 'address', 'name']
        }
    
    return anonymized
```

#### **4.2 Gemini Data Usage Policy Compliance** ⚠️ **REQUIRED**
- ✅ **Check Gemini's data usage policy** - Does Gemini train on sent data?
- ⚠️ **Configure Gemini to not use data for training** (if possible)
- ⚠️ **Use Gemini's enterprise tier** (if available) for better data privacy
- ⚠️ **Document data sharing agreement** with Google/Gemini

#### **4.3 Audit Logging of External API Calls** ⚠️ **REQUIRED**
```python
# Log all external API calls for compliance
audit_logger.log_external_api_call(
    api_name="gemini",
    endpoint="generate_content",
    tokens_sent=len(prompt),
    tokens_received=len(response_text),
    cost=estimated_cost,
    user_id=user_id,
    school_id=school_id,
    student_id=student_id  # Anonymized
)
```

---

### 5. **Network Security** ⚠️ **RECOMMENDED**

**Current Implementation:**
- ✅ HTTPS used for API calls (good)
- ⚠️ **No certificate pinning** - Could be vulnerable to MITM attacks
- ⚠️ **No proxy configuration** - May need for corporate environments
- ⚠️ **No IP allowlisting** - If available from Gemini

**Missing/Needed:**

#### **5.1 Certificate Pinning** ⚠️ **OPTIONAL (Advanced)**
- Pin Gemini API certificates
- Prevent MITM attacks
- More complex to manage (certificate rotation)

#### **5.2 Proxy Configuration** ⚠️ **IF NEEDED**
```python
# Configure proxy for corporate environments
import os

proxy_config = {
    'http': os.getenv('HTTP_PROXY'),
    'https': os.getenv('HTTPS_PROXY'),
}

if proxy_config['https']:
    genai.configure(
        api_key=api_key,
        transport=proxy_config
    )
```

---

### 6. **Error Handling & Resilience** ⚠️ **RECOMMENDED**

**Current Implementation:**
- ✅ Basic error handling (try/except)
- ✅ Falls back to mock responses on error
- ⚠️ **No retry logic with exponential backoff**
- ⚠️ **No circuit breaker pattern** - Could overwhelm API if it's down

**Missing/Needed:**

#### **6.1 Retry Logic with Exponential Backoff** ⚠️ **RECOMMENDED**
```python
import time
from functools import wraps

def retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    
                    logger.warning(
                        f"API call failed (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator
```

#### **6.2 Circuit Breaker Pattern** ⚠️ **RECOMMENDED**
```python
class CircuitBreaker:
    """Circuit breaker to prevent overwhelming failing services."""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # 'closed', 'open', 'half_open'
    
    def call(self, func, *args, **kwargs):
        """Call function with circuit breaker protection."""
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'half_open'
            else:
                raise Exception("Circuit breaker is open. Service unavailable.")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'half_open':
                self.state = 'closed'
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'open'
            
            raise
```

---

### 7. **Monitoring & Observability** ⚠️ **RECOMMENDED**

**Current Implementation:**
- ✅ Basic logging (info, error, warning)
- ⚠️ **No structured metrics** - No API call volume tracking
- ⚠️ **No performance monitoring** - No latency tracking
- ⚠️ **No cost tracking** - No cost per request tracking

**Missing/Needed:**

#### **7.1 API Call Metrics** ⚠️ **RECOMMENDED**
- Track API call volume (per hour/day)
- Track API latency (p50, p95, p99)
- Track error rates (4xx, 5xx responses)
- Track token usage (input/output tokens)

#### **7.2 Cost Tracking** ⚠️ **RECOMMENDED**
- Track cost per request
- Track daily/monthly costs
- Alert on cost anomalies
- Generate cost reports

#### **7.3 Health Monitoring** ⚠️ **RECOMMENDED**
- Health check endpoint for Gemini API
- Monitor API availability
- Alert on service degradation

---

## 📊 **SECURITY CHECKLIST**

### **API Key Management:**
- [x] API key stored in environment variable (development)
- [ ] API key stored in secret management service (production)
- [ ] API key rotation policy implemented
- [ ] API key monitoring (unusual usage alerts)
- [ ] Never log API keys

### **Rate Limiting & Quota:**
- [ ] Rate limiting on external API calls
- [ ] Daily/monthly quota limits
- [ ] Cost/budget controls
- [ ] Quota exhaustion alerts
- [ ] Usage monitoring dashboard

### **Response Validation:**
- [x] Harmful content detection (implemented)
- [ ] Response size limits
- [ ] Timeout handling
- [ ] Response format validation
- [ ] Malformed response handling

### **Data Privacy:**
- [ ] Data anonymization before sending to API
- [ ] Verify Gemini's data usage policy
- [ ] Configure Gemini to not use data for training
- [ ] Audit logging of external API calls
- [ ] Data sharing agreement documented

### **Network Security:**
- [x] HTTPS used for API calls
- [ ] Certificate pinning (optional)
- [ ] Proxy configuration (if needed)
- [ ] IP allowlisting (if available)

### **Error Handling:**
- [x] Basic error handling (implemented)
- [x] Fallback to mock responses
- [ ] Retry logic with exponential backoff
- [ ] Circuit breaker pattern
- [ ] Graceful degradation

### **Monitoring:**
- [x] Basic logging (implemented)
- [ ] API call metrics
- [ ] Cost tracking
- [ ] Performance monitoring
- [ ] Health checks

---

## 🚨 **IMMEDIATE PRIORITIES**

### **🔴 CRITICAL (Before Production):**

1. **API Key Management**
   - Move to secret management service (AWS Secrets Manager, etc.)
   - Implement key rotation policy
   - Never log API keys

2. **Data Privacy Compliance**
   - Verify Gemini's data usage policy
   - Configure Gemini to not use data for training
   - Audit log all external API calls

3. **Rate Limiting & Quota**
   - Implement rate limiting on Gemini API calls
   - Set daily/monthly quota limits
   - Add quota exhaustion alerts

### **🟡 IMPORTANT (Should Implement Soon):**

4. **Timeout Handling**
   - Add timeout on API calls (30 seconds)
   - Handle timeout errors gracefully

5. **Error Handling**
   - Retry logic with exponential backoff
   - Circuit breaker pattern

6. **Response Validation**
   - Response size limits
   - Response format validation

### **🟢 RECOMMENDED (Implement Over Time):**

7. **Monitoring & Observability**
   - API call metrics
   - Cost tracking
   - Performance monitoring

8. **Advanced Security**
   - Certificate pinning (if needed)
   - Data anonymization (if required by policy)

---

## 🔗 **References**

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Gemini API Security Best Practices](https://ai.google.dev/docs/safety_setting)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [HashiCorp Vault](https://www.vaultproject.io/)

---

**Document Version:** 1.0  
**Last Updated:** 2024


