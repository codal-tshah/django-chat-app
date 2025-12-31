"""
Custom middleware to suppress verbose Redis connection error logging
"""
import logging
from channels.middleware import BaseMiddleware

logger = logging.getLogger(__name__)


class SuppressRedisErrorsMiddleware(BaseMiddleware):
    """
    Middleware to catch and suppress verbose Redis connection errors
    """
    async def __call__(self, scope, receive, send):
        try:
            return await super().__call__(scope, receive, send)
        except Exception as e:
            # Check if it's a Redis connection error
            error_str = str(e).lower()
            if 'redis' in error_str or 'connection' in error_str:
                # Log a simple warning instead of full stack trace
                logger.warning(f"Redis connection issue: {type(e).__name__} - {str(e)[:100]}")
                # Close the connection gracefully
                await send({
                    'type': 'websocket.close',
                    'code': 1011,  # Internal server error
                })
            else:
                # Re-raise other exceptions
                raise
