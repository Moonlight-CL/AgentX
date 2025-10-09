import json
from typing import Dict, Any

class EventSerializer:
    """
    A class to handle serialization of agent events for transmission over HTTP.
    """
    
    @staticmethod
    def prepare_event_for_serialization(event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare an event for serialization by handling non-serializable objects.
        
        :param event: The event to prepare for serialization.
        :return: A serializable version of the event.
        """
        # Create a copy of the event to avoid modifying the original
        serializable_event = {}
        
        for key, value in event.items():
            # Handle special cases
            if key == 'agent':
                # Skip agent object as it's not serializable
                continue
            elif key == 'event_loop_cycle_trace' or key == 'event_loop_cycle_span' or key == 'event_loop_parent_span':
                # Skip trace and span objects as they're not serializable
                continue
            elif key == 'event_loop_cycle_id' or key == 'event_loop_parent_cycle_id':
                # Convert UUID to string
                if value is not None:
                    serializable_event[key] = str(value)
            elif key == 'traces':
                # Skip traces as they're not serializable
                continue
            elif isinstance(value, dict):
                # Recursively process nested dictionaries
                serializable_event[key] = EventSerializer.prepare_event_for_serialization(value)
            elif isinstance(value, list):
                # Process lists
                serializable_event[key] = [
                    EventSerializer.prepare_event_for_serialization(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # For other types, try to serialize directly
                try:
                    # Test if the value is JSON serializable
                    json.dumps({key: value})
                    serializable_event[key] = value
                except (TypeError, OverflowError):
                    # If not serializable, convert to string representation
                    serializable_event[key] = str(value)
        
        return serializable_event
    
    @staticmethod
    def serialize_event(event: Dict[str, Any]) -> str:
        """
        Serialize an event to a JSON string for SSE transmission.
        
        :param event: The event to serialize.
        :return: A JSON string representation of the event.
        """
        serializable_event = EventSerializer.prepare_event_for_serialization(event)
        return json.dumps(serializable_event)
    
    @staticmethod
    def format_as_sse(event: Dict[str, Any]) -> str:
        """
        Format an event as a Server-Sent Event (SSE).
        
        :param event: The event to format.
        :return: A string formatted as an SSE.
        """
        serialized = EventSerializer.serialize_event(event)
        return f"data: {serialized}\n\n"
