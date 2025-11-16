"""
Service Manager - Fail-Safe Service State Management

Manages service state and implements fail-safe behavior:
- When service is stopping, reject all new requests (fail-safe)
- Complete in-flight requests gracefully
- Ensure audit logs are written before shutdown
- Prevent new data access during shutdown
"""
import asyncio
import logging
from enum import Enum
from typing import Optional
import signal
import sys
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service state enumeration."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"  # Fail-safe: Reject new requests
    STOPPED = "stopped"


class ServiceManager:
    """
    Manages service state with fail-safe behavior.
    
    Fail-Safe Behavior:
    - When service enters STOPPING state, all new requests are rejected
    - In-flight requests are allowed to complete
    - New data access is prevented during shutdown
    - Ensures audit logs are written before shutdown
    """
    
    def __init__(self):
        """Initialize the service manager."""
        self._state = ServiceState.STARTING
        self._in_flight_requests = 0
        self._max_shutdown_wait = 30  # Maximum seconds to wait for graceful shutdown
        self._shutdown_event = asyncio.Event()
        
    @property
    def state(self) -> ServiceState:
        """Get current service state."""
        return self._state
    
    @property
    def is_accepting_requests(self) -> bool:
        """
        Check if service is accepting new requests.
        
        Returns:
            True if service is in RUNNING state, False otherwise (fail-safe)
        """
        return self._state == ServiceState.RUNNING
    
    @property
    def in_flight_count(self) -> int:
        """Get number of in-flight requests."""
        return self._in_flight_requests
    
    def start(self):
        """Mark service as started and accepting requests."""
        self._state = ServiceState.RUNNING
        logger.info("Service state: RUNNING - Accepting requests")
    
    def stop(self):
        """
        Mark service as stopping (fail-safe mode).
        
        This triggers fail-safe behavior:
        - New requests are rejected
        - In-flight requests can complete
        """
        if self._state != ServiceState.RUNNING:
            return
        
        self._state = ServiceState.STOPPING
        logger.warning(
            f"Service state: STOPPING - Rejecting new requests "
            f"(fail-safe mode). {self._in_flight_requests} in-flight requests remaining."
        )
        self._shutdown_event.set()
    
    def wait_for_shutdown(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for all in-flight requests to complete.
        
        Args:
            timeout: Maximum seconds to wait (default: self._max_shutdown_wait)
            
        Returns:
            True if all requests completed, False if timeout
        """
        timeout = timeout or self._max_shutdown_wait
        
        if self._in_flight_requests == 0:
            self._state = ServiceState.STOPPED
            logger.info("Service state: STOPPED - All requests completed")
            return True
        
        logger.info(f"Waiting up to {timeout}s for {self._in_flight_requests} in-flight requests to complete...")
        
        # Wait for requests to complete (polling)
        import time
        start_time = time.time()
        
        while self._in_flight_requests > 0:
            if time.time() - start_time > timeout:
                logger.warning(
                    f"Shutdown timeout: {self._in_flight_requests} requests still in-flight "
                    f"after {timeout}s"
                )
                return False
            
            time.sleep(0.5)  # Poll every 0.5 seconds
        
        self._state = ServiceState.STOPPED
        logger.info("Service state: STOPPED - All requests completed gracefully")
        return True
    
    def enter_request(self):
        """
        Mark that a new request is starting.
        
        Returns:
            True if request is accepted, False if service is stopping (fail-safe)
            
        Raises:
            RuntimeError: If service is not in RUNNING state
        """
        if self._state == ServiceState.STOPPING:
            logger.warning("Request rejected: Service is stopping (fail-safe)")
            return False
        
        if self._state != ServiceState.RUNNING:
            raise RuntimeError(f"Service is not in RUNNING state: {self._state.value}")
        
        self._in_flight_requests += 1
        return True
    
    def exit_request(self):
        """Mark that a request has completed."""
        if self._in_flight_requests > 0:
            self._in_flight_requests -= 1

# Global service manager instance
_service_manager = ServiceManager()


def get_service_manager() -> ServiceManager:
    """Get the global service manager instance."""
    return _service_manager


def setup_signal_handlers(app):
    """
    Setup signal handlers for graceful shutdown.
    
    Registers handlers for SIGTERM and SIGINT to trigger fail-safe shutdown.
    """
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        logger.warning(f"Received signal {signum}. Initiating graceful shutdown (fail-safe)...")
        service_manager = get_service_manager()
        service_manager.stop()
        
        # Give requests time to complete, then force exit
        if not service_manager.wait_for_shutdown():
            logger.error("Force shutdown: In-flight requests did not complete in time")
        
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Signal handlers registered for graceful shutdown")


@asynccontextmanager
async def lifespan(app):
    """
    Lifespan context manager for FastAPI app.
    
    Handles startup and shutdown events with fail-safe behavior.
    """
    # Startup
    logger.info("Service starting...")
    service_manager = get_service_manager()
    service_manager.start()
    
    # Setup signal handlers
    setup_signal_handlers(app)
    
    logger.info("Service started and ready to accept requests")
    
    yield
    
    # Shutdown
    logger.info("Service shutting down...")
    service_manager = get_service_manager()
    service_manager.stop()
    
    # Wait for in-flight requests to complete
    if not service_manager.wait_for_shutdown():
        logger.warning("Some requests did not complete during shutdown")
    
    logger.info("Service shutdown complete")


