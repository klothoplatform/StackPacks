import atexit
import json
import os

from src.util.logging import logger

rudder_analytics = None
if os.getenv("RUDDERSTACK_ENABLED", "true").lower() == "true":
    import rudderstack.analytics as rudder_analytics

    rudder_analytics.write_key = "2i3y1jaZNyDDYKbIavQOJsuvBWQ"
    rudder_analytics.dataPlaneUrl = "https://kloashibotqvww.dataplane.rudderstack.com"

    def flush():
        rudder_analytics.flush()

    atexit.register(flush)


def track(*args, **kwargs):
    """Send a track call."""
    try:
        if rudder_analytics:
            rudder_analytics.track(*args, **kwargs)
        else:
            logger.debug(
                json.dumps({"type": "track", "args": args, "kwargs": kwargs}, indent=2)
            )
    except Exception as e:
        logger.error(f"Error tracking event: {e}")
