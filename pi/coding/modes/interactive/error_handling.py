"""Error handling utilities for interactive mode."""
import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AgentError(Exception):
    """Base exception for agent-related errors."""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class APIError(AgentError):
    """Exception raised for API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[str] = None,
    ):
        self.status_code = status_code
        super().__init__(message, details)


class AuthenticationError(APIError):
    """Exception raised for authentication failures."""

    pass


class RateLimitError(APIError):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        self.retry_after = retry_after
        super().__init__(message)


class ConfigurationError(AgentError):
    """Exception raised for configuration issues."""

    pass


async def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs: Any,
) -> T:
    """
    Retry a function with exponential backoff.

    Args:
        func: The async function to retry
        *args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function call

    Raises:
        The last exception if all retries fail
    """
    last_exception = None
    delay = base_delay

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except APIError as e:
            last_exception = e

            # Don't retry authentication errors
            if isinstance(e, AuthenticationError):
                raise

            # Don't retry client errors (4xx) except rate limit
            if e.status_code and 400 <= e.status_code < 500:
                if not isinstance(e, RateLimitError):
                    raise

            # Log retry attempt
            if attempt < max_retries:
                logger.warning(
                    f"API error on attempt {attempt + 1}/{max_retries + 1}: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(min(delay, max_delay))
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"Max retries exceeded: {e}")
        except Exception as e:
            last_exception = e
            logger.error(f"Unexpected error: {e}")
            break

    raise last_exception or AgentError("Unknown error occurred")


def handle_errors(
    default_message: str = "An error occurred",
    reraise: bool = False,
) -> Callable:
    """
    Decorator for handling errors in async functions.

    Args:
        default_message: Default message to show on error
        reraise: Whether to reraise the exception after handling

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except AgentError as e:
                logger.error(f"Agent error in {func.__name__}: {e}")
                if reraise:
                    raise
                return {"error": True, "message": e.message}
            except Exception as e:
                logger.exception(f"Unexpected error in {func.__name__}: {e}")
                if reraise:
                    raise
                return {"error": True, "message": default_message}

        return wrapper

    return decorator


def format_error(error: Exception) -> str:
    """
    Format an exception for user display.

    Args:
        error: The exception to format

    Returns:
        User-friendly error message
    """
    if isinstance(error, AuthenticationError):
        return "Authentication failed. Please check your API credentials."

    if isinstance(error, RateLimitError):
        msg = "Rate limit exceeded. Please wait before trying again."
        if error.retry_after:
            msg += f" Retry after {error.retry_after} seconds."
        return msg

    if isinstance(error, APIError):
        msg = f"API error: {error.message}"
        if error.details:
            msg += f"\nDetails: {error.details}"
        return msg

    if isinstance(error, ConfigurationError):
        return f"Configuration error: {error.message}"

    return f"Unexpected error: {str(error)}"


async def safe_execute(
    func: Callable[..., T],
    *args: Any,
    default: Optional[T] = None,
    error_callback: Optional[Callable[[Exception], None]] = None,
    **kwargs: Any,
) -> Optional[T]:
    """
    Safely execute a function, catching and logging errors.

    Args:
        func: The async function to execute
        *args: Arguments to pass to the function
        default: Default value to return on error
        error_callback: Optional callback for error handling
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function, or default on error
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in {func.__name__}: {e}")
        if error_callback:
            error_callback(e)
        return default


__all__ = [
    "AgentError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "ConfigurationError",
    "retry_with_backoff",
    "handle_errors",
    "format_error",
    "safe_execute",
]
