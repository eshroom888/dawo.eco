"""Log capture handler for agent execution output.

Story 7-8, Task 5.1: Captures log output during agent execution
for storage in execution logs.

Uses Python logging.Handler subclass attached to a named logger.
Thread-safe via logging.Handler's built-in lock.

Usage:
    from core.scheduling.log_capture import LogCaptureHandler

    handler = LogCaptureHandler.attach("root")
    # ... agent runs and emits logs ...
    output = handler.get_output()
    handler.detach()
"""

import logging
from io import StringIO

MAX_CAPTURE_LINES = 1000


class LogCaptureHandler(logging.Handler):
    """Logging handler that captures output to an in-memory buffer.

    Thread-safe via logging.Handler's built-in lock mechanism.
    Caps output at max_lines (keeps last N lines).

    Attributes:
        _buffer: StringIO buffer for captured log text
        _max_lines: Maximum lines to retain
        _line_count: Current line count
        _logger_name: Name of logger this handler is attached to
    """

    def __init__(self, max_lines: int = MAX_CAPTURE_LINES) -> None:
        """Initialize handler.

        Args:
            max_lines: Maximum lines to capture (default 1000)
        """
        super().__init__()
        self._buffer = StringIO()
        self._max_lines = max_lines
        self._line_count = 0
        self._logger_name: str | None = None

    def emit(self, record: logging.LogRecord) -> None:
        """Write a log record to the buffer.

        Thread-safe via logging.Handler.acquire()/release().

        Args:
            record: Log record to capture
        """
        try:
            msg = self.format(record)
            self._buffer.write(msg + "\n")
            self._line_count += 1
        except Exception:
            self.handleError(record)

    def get_output(self) -> str:
        """Get captured log output, capped at max_lines.

        Returns last max_lines if total exceeds limit.

        Returns:
            Captured log text as string.
        """
        content = self._buffer.getvalue()
        if not content:
            return ""

        lines = content.rstrip("\n").split("\n")
        if len(lines) > self._max_lines:
            lines = lines[-self._max_lines:]
        return "\n".join(lines)

    @classmethod
    def attach(cls, logger_name: str, max_lines: int = MAX_CAPTURE_LINES) -> "LogCaptureHandler":
        """Create handler and attach to named logger.

        Args:
            logger_name: Logger name to attach to
            max_lines: Maximum lines to capture

        Returns:
            The attached LogCaptureHandler instance.
        """
        handler = cls(max_lines=max_lines)
        handler._logger_name = logger_name
        target_logger = logging.getLogger(logger_name)
        target_logger.addHandler(handler)
        return handler

    def detach(self) -> None:
        """Remove this handler from its logger."""
        if self._logger_name is not None:
            target_logger = logging.getLogger(self._logger_name)
            target_logger.removeHandler(self)


__all__ = [
    "LogCaptureHandler",
]
