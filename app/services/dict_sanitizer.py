"""
Dictionary Sanitizer

Recursively sanitizes unknown/dynamic dictionary structures to prevent injection
attacks even when we don't know all possible key-value pairs.
"""
import re
import logging
from typing import Any, Dict, List, Union, Optional
from .security import InputSanitizer, SecurityError

logger = logging.getLogger(__name__)


class DictSanitizer:
    """
    Sanitizes dictionaries and nested structures to prevent injection attacks.
    
    Works recursively on unknown structures, ensuring all string values are safe
    even when we don't know all possible keys in advance.
    """
    
    # Maximum nesting depth to prevent stack overflow attacks
    MAX_DEPTH = 10
    
    # Maximum length for dictionary keys
    MAX_KEY_LENGTH = 200
    
    # Maximum size for entire dictionary (to prevent DoS)
    MAX_DICT_SIZE = 1_000_000  # 1MB in characters
    
    @classmethod
    def sanitize_dict(
        cls,
        data: Union[Dict[str, Any], List[Any], Any],
        max_depth: int = MAX_DEPTH,
        allowed_keys: Optional[set] = None,
        strict_mode: bool = False
    ) -> Union[Dict[str, Any], List[Any], Any]:
        """
        Recursively sanitize a dictionary or list structure.
        
        Args:
            data: The data structure to sanitize (dict, list, or primitive)
            max_depth: Maximum nesting depth (prevents stack overflow)
            allowed_keys: Optional set of allowed keys (whitelist approach)
            strict_mode: If True, reject unknown keys (not just warn)
            
        Returns:
            Sanitized data structure
            
        Raises:
            SecurityError: If data contains malicious patterns or exceeds limits
        """
        # Check depth to prevent stack overflow
        if max_depth <= 0:
            raise SecurityError("Maximum nesting depth exceeded")
        
        # Check dictionary size (approximate)
        if isinstance(data, dict):
            dict_str = str(data)
            if len(dict_str) > cls.MAX_DICT_SIZE:
                raise SecurityError(f"Dictionary too large (max {cls.MAX_DICT_SIZE} characters)")
        
        # Handle dictionaries
        if isinstance(data, dict):
            sanitized = {}
            
            for key, value in data.items():
                # Sanitize the key itself
                sanitized_key = cls._sanitize_key(key, allowed_keys, strict_mode)
                
                # Recursively sanitize the value
                sanitized_value = cls.sanitize_dict(
                    value,
                    max_depth=max_depth - 1,
                    allowed_keys=allowed_keys,
                    strict_mode=strict_mode
                )
                
                sanitized[sanitized_key] = sanitized_value
            
            return sanitized
        
        # Handle lists
        elif isinstance(data, list):
            return [
                cls.sanitize_dict(
                    item,
                    max_depth=max_depth - 1,
                    allowed_keys=allowed_keys,
                    strict_mode=strict_mode
                )
                for item in data
            ]
        
        # Handle strings (most important for injection prevention)
        elif isinstance(data, str):
            return cls._sanitize_string_value(data)
        
        # Handle other types (int, float, bool, None) - pass through as-is
        else:
            return data
    
    @classmethod
    def _sanitize_key(
        cls,
        key: str,
        allowed_keys: Optional[set] = None,
        strict_mode: bool = False
    ) -> str:
        """
        Sanitize dictionary key.
        
        Args:
            key: The key to sanitize
            allowed_keys: Optional whitelist of allowed keys
            strict_mode: If True, reject keys not in whitelist
            
        Returns:
            Sanitized key
            
        Raises:
            SecurityError: If key is invalid or not in whitelist
        """
        if not isinstance(key, str):
            # Convert non-string keys to string (with validation)
            key = str(key)
            logger.warning(f"Non-string dictionary key converted: {type(key)}")
        
        # Check key length
        if len(key) > cls.MAX_KEY_LENGTH:
            raise SecurityError(f"Dictionary key too long (max {cls.MAX_KEY_LENGTH} characters): {key[:50]}...")
        
        # Check for allowed keys whitelist
        if allowed_keys is not None:
            if key not in allowed_keys:
                if strict_mode:
                    raise SecurityError(f"Unknown key not allowed: {key}")
                else:
                    logger.debug(f"Unknown key detected (non-strict mode): {key}")
        
        # Check key for dangerous patterns
        key_lower = key.lower()
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, key_lower):
                raise SecurityError(f"Invalid key pattern detected: {key}")
        
        # Basic key format validation (alphanumeric, underscores, dots, hyphens)
        if not re.match(r'^[A-Za-z0-9_.-]+$', key):
            # Allow some special chars but log warning
            logger.warning(f"Dictionary key contains unusual characters: {key}")
            # Still allow it but sanitize special chars
            key = re.sub(r'[^\w.-]', '_', key)
        
        return key
    
    @classmethod
    def _sanitize_string_value(cls, value: str) -> str:
        """
        Sanitize string values in dictionaries.
        
        This is the critical part - ensures all string values are safe
        even if we don't know what they represent.
        
        Args:
            value: String value to sanitize
            
        Returns:
            Sanitized string
            
        Raises:
            SecurityError: If string contains malicious patterns
        """
        # Check length (more lenient than question field)
        if len(value) > 50000:  # 50KB limit per string
            raise SecurityError(f"String value too long (max 50000 characters)")
        
        # Check for prompt injection patterns
        value_lower = value.lower()
        for pattern in InputSanitizer.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f"Prompt injection pattern in dictionary value: {pattern}")
                raise SecurityError(
                    "Invalid content detected in data. Please check your input."
                )
        
        # Check for SQL injection patterns (defense in depth)
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f"SQL injection pattern in dictionary value: {pattern}")
                raise SecurityError(
                    "Invalid content detected in data. Please check your input."
                )
        
        # Normalize whitespace (but be less aggressive than question sanitization)
        # Don't remove all newlines - just normalize
        value = value.replace('\r\n', '\n').replace('\r', '\n')
        
        # Limit consecutive newlines (prevent log injection)
        value = re.sub(r'\n{10,}', '\n' * 10, value)
        
        return value
    
    @classmethod
    def sanitize_data_summary(cls, data_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize data_summary structure with known expected keys.
        
        Args:
            data_summary: Data summary dictionary from data_router
            
        Returns:
            Sanitized data summary
        """
        # Known expected keys in data_summary
        known_keys = {
            "emt_summary", "real_summary", "sel_summary",
            # Nested keys
            "record_count", "average_score", "latest_score", "records",
            "average_scores", "self_awareness", "self_management",
            "social_awareness", "relationship_skills", "responsible_decision_making",
            "student_id", "date", "score", "observations", "sel_score",
            "assignment_id"
        }
        
        return cls.sanitize_dict(
            data_summary,
            allowed_keys=known_keys,
            strict_mode=False  # Allow unknown keys but validate them
        )
    
    @classmethod
    def sanitize_evaluation_metrics(cls, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize evaluation_metrics from Prompt Eval Tool.
        
        Args:
            metrics: Evaluation metrics dictionary
            
        Returns:
            Sanitized evaluation metrics
        """
        # Known expected keys (can be extended as we learn more)
        known_keys = {
            "timestamp", "question", "prompt_length", "data_sources_used",
            "response_length", "evaluation_score", "metrics",
            # Allow nested structures
        }
        
        return cls.sanitize_dict(
            metrics,
            allowed_keys=known_keys,
            strict_mode=False  # Allow unknown metrics but validate content
        )
    
    @classmethod
    def sanitize_metadata(cls, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata fields from data models.
        
        Args:
            metadata: Metadata dictionary (can contain anything)
            
        Returns:
            Sanitized metadata
        """
        # Metadata is intentionally flexible, but we still sanitize values
        return cls.sanitize_dict(
            metadata,
            allowed_keys=None,  # No whitelist - metadata is open
            strict_mode=False
        )


