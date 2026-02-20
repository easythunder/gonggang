"""
Polling interval enforcement library (T058)

Enforces server-side polling interval of 2-3 seconds.
Ignores client-provided interval_ms parameter.
"""
import random


class PollingIntervalEnforcer:
    """Manages server-enforced polling intervals."""
    
    MIN_INTERVAL_MS = 2000
    MAX_INTERVAL_MS = 3000
    
    @staticmethod
    def get_enforced_interval() -> int:
        """
        Get server-enforced polling interval.
        
        Returns:
            int: Polling interval in milliseconds (2000-3000)
        """
        # Return random value within range to avoid client synchronization
        return random.randint(
            PollingIntervalEnforcer.MIN_INTERVAL_MS,
            PollingIntervalEnforcer.MAX_INTERVAL_MS
        )
    
    @staticmethod
    def validate_and_ignore_client_interval(client_interval_ms: int = None) -> int:
        """
        Validate client's requested interval and ignore it.
        
        Args:
            client_interval_ms: Client's requested polling interval (ignored)
        
        Returns:
            int: Server-enforced interval (always 2000-3000)
        """
        # Log ignored client interval (optional)
        if client_interval_ms is not None:
            # Client tried to set interval, but we ignore it
            pass
        
        return PollingIntervalEnforcer.get_enforced_interval()
