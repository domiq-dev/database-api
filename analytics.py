import os
from amplitude import Amplitude, BaseEvent

# Global client instance (singleton pattern)
_client: Amplitude | None = None

def init_analytics() -> None:
    """Initialize the Amplitude client with API key from environment"""
    global _client
    if _client is None:
        api_key = os.getenv("AMPLITUDE_API_KEY")
        if api_key:
            _client = Amplitude(api_key)
            print("Amplitude client initialized successfully")
        else:
            print("Warning: AMPLITUDE_API_KEY not found in environment variables")
            print("Analytics tracking will be disabled")

def track(user_id: str, event_type: str, props=None, *, 
          device_id=None, session_id=None):
    """
    Track an event to Amplitude
    
    Args:
        user_id (str): Unique identifier for the user
        event_type (str): Name of the event being tracked
        props (dict, optional): Event properties dictionary
        device_id (str, optional): Device identifier for cross-platform tracking
        session_id (str, optional): Session identifier for grouping events
    """
    # Ensure client is initialized
    if _client is None:
        init_analytics()
    
    # If still no client (missing API key), skip tracking
    if _client is None:
        print(f"Skipping event tracking: {event_type} (no Amplitude client)")
        return
    
    try:
        # Create and send the event
        event = BaseEvent(
            event_type=event_type,
            user_id=user_id,
            device_id=device_id,
            session_id=session_id,
            event_properties=props or {},
        )
        
        _client.track(event)
        print(f"Event tracked: {event_type} for user {user_id}")
        
    except Exception as e:
        print(f"Error tracking event {event_type}: {e}")

def flush():
    """Manually flush pending events (useful for testing or shutdown)"""
    global _client
    if _client:
        try:
            _client.flush()
            print("Amplitude events flushed")
        except Exception as e:
            print(f"Error flushing Amplitude events: {e}")

def shutdown():
    """Shutdown the Amplitude client gracefully"""
    global _client
    if _client:
        try:
            _client.shutdown()
            print("Amplitude client shutdown")
        except Exception as e:
            print(f"Error shutting down Amplitude client: {e}")
        finally:
            _client = None