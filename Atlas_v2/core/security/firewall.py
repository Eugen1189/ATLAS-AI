import time
from collections import defaultdict, deque
from core.logger import logger

class SecurityViolation(Exception):
    """Exception raised for security policy violations."""
    pass

class AxisFirewall:
    """
    Multi-layer defense for AXIS:
    - Rate Limiter per source (Anti-DoS, Token Bucket)
    - Prompt Sanitizer (Anti-Injection)
    - Payload Validator (Anti-Context-Overflow)
    """
    def __init__(self, max_requests: int = 5, window_sec: int = 60):
        # Per-source request history: {source_id: deque}
        self._request_history: dict[str, deque] = defaultdict(deque)
        self.max_requests = max_requests
        self.window_sec = window_sec
        # Prompt injection and dangerous override patterns
        self.forbidden_patterns = [
            "ignore instructions",
            "ignore previous instructions",
            "override guard",
            "system override",
            "forget your rules",
            "sudo rm",
            "delete core",
            "jailbreak",
            "dan mode",
        ]

    def is_request_allowed(self, source: str = "terminal") -> bool:
        """
        Перевіряє ліміт запитів (Anti-DoS) використовуючи Token Bucket per source.
        source: unique identifier for the request origin (e.g. 'telegram', 'terminal')
        """
        now = time.time()
        history = self._request_history[source]
        # Evict timestamps outside the sliding window
        while history and history[0] < now - self.window_sec:
            history.popleft()

        if len(history) < self.max_requests:
            history.append(now)
            return True

        logger.warning(
            "firewall.rate_limit_exceeded",
            source=source,
            requests_in_window=len(history),
            window_sec=self.window_sec,
        )
        return False

    def sanitize_input(self, text: str, source: str = "terminal") -> str:
        """
        Multi-layer input sanitizer:
        1. Payload length check — Anti-Context-Overflow
        2. Injection pattern check — Anti-Prompt-Injection
        """
        if len(text) > 4000:
            logger.warning("firewall.payload_too_large", source=source, length=len(text))
            raise SecurityViolation("Payload too large. Maximum input length is 4000 characters.")

        text_lower = text.lower()
        for pattern in self.forbidden_patterns:
            if pattern in text_lower:
                logger.warning("firewall.injection_detected", source=source, pattern=pattern)
                raise SecurityViolation(f"Prompt injection blocked: suspicious pattern '{pattern}' detected.")

        return text

# Singleton shared instance for use across all modules
axis_firewall = AxisFirewall()
