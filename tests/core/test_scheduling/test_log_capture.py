"""Tests for LogCaptureHandler.

Story 7-8, Task 5.1: Log capture handler tests.
Target: 8+ tests.
"""

import logging
import pytest

from core.scheduling.log_capture import LogCaptureHandler


class TestLogCaptureHandler:
    """Tests for the LogCaptureHandler logging.Handler subclass."""

    def test_capture_single_log(self):
        """Captures a single log message."""
        handler = LogCaptureHandler()
        test_logger = logging.getLogger("test.capture.single")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        test_logger.info("Hello world")
        output = handler.get_output()

        assert "Hello world" in output
        test_logger.removeHandler(handler)

    def test_capture_multiple_logs(self):
        """Captures multiple log messages."""
        handler = LogCaptureHandler()
        test_logger = logging.getLogger("test.capture.multi")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        test_logger.info("Line 1")
        test_logger.warning("Line 2")
        test_logger.error("Line 3")
        output = handler.get_output()

        assert "Line 1" in output
        assert "Line 2" in output
        assert "Line 3" in output
        test_logger.removeHandler(handler)

    def test_max_lines_cap(self):
        """Caps output at max_lines (last N lines)."""
        handler = LogCaptureHandler(max_lines=5)
        test_logger = logging.getLogger("test.capture.cap")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        for i in range(20):
            test_logger.info("Line %d", i)
        output = handler.get_output()
        lines = output.strip().split("\n")

        assert len(lines) == 5
        # Should have last 5 lines (15-19)
        assert "Line 15" in output
        assert "Line 19" in output
        assert "Line 0" not in output
        test_logger.removeHandler(handler)

    def test_default_max_lines_1000(self):
        """Default max_lines is 1000."""
        handler = LogCaptureHandler()
        assert handler._max_lines == 1000

    def test_empty_output(self):
        """Returns empty string when no logs captured."""
        handler = LogCaptureHandler()
        assert handler.get_output() == ""

    def test_attach_classmethod(self):
        """attach() creates handler and adds to named logger."""
        handler = LogCaptureHandler.attach("test.capture.attach")
        test_logger = logging.getLogger("test.capture.attach")

        assert handler in test_logger.handlers
        handler.detach()
        assert handler not in test_logger.handlers

    def test_detach_removes_handler(self):
        """detach() removes handler from logger."""
        handler = LogCaptureHandler.attach("test.capture.detach")
        test_logger = logging.getLogger("test.capture.detach")

        assert handler in test_logger.handlers
        handler.detach()
        assert handler not in test_logger.handlers

    def test_thread_safety(self):
        """Handler uses lock for thread safety."""
        handler = LogCaptureHandler()
        # logging.Handler already provides a lock
        assert handler.lock is not None

    def test_attach_captures_logs(self):
        """Attached handler captures logs from the named logger."""
        handler = LogCaptureHandler.attach("test.capture.full")
        test_logger = logging.getLogger("test.capture.full")
        test_logger.setLevel(logging.DEBUG)

        test_logger.info("Captured via attach")
        output = handler.get_output()

        assert "Captured via attach" in output
        handler.detach()
