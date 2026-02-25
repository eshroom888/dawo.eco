# Mock Verification Patterns

**Purpose:** Document correct patterns for mocking external services in tests.
**Background:** Epic 4 revealed that mocks were returning `success=True` based on exception handling alone, missing semantic failures where `response.success=False`.

---

## The Problem

### Wrong Pattern (Epic 4 Bug)

```python
class MockRetryMiddleware:
    async def execute_with_retry(self, operation, context: str):
        try:
            response = await operation()
            # BUG: Always returns success=True if no exception
            return Mock(success=True, response=response, attempts=1)
        except Exception as e:
            return Mock(success=False, last_error=str(e), attempts=1)
```

This pattern fails because:
- External APIs can return `{ "success": false, "error": "..." }` without throwing exceptions
- HTTP 200 responses can contain semantic failures
- The mock incorrectly reports success when the operation actually failed

### Correct Pattern

```python
class MockRetryMiddleware:
    async def execute_with_retry(self, operation, context: str):
        try:
            response = await operation()
            # CHECK: Validate response.success attribute
            if hasattr(response, "success") and not response.success:
                return Mock(
                    success=False,
                    response=response,
                    attempts=1,
                    last_error=getattr(response, "error_message", "Operation failed"),
                )
            return Mock(success=True, response=response, attempts=1)
        except Exception as e:
            return Mock(success=False, last_error=str(e), attempts=1)
```

---

## Mock Implementation Guidelines

### 1. Always Validate Response Semantics

```python
# External service response
@dataclass
class PublishResponse:
    success: bool
    media_id: str | None = None
    error_message: str | None = None

# Mock must check this
if response.success:
    # Actually succeeded
else:
    # Semantic failure - handle appropriately
```

### 2. Mock Both Success and Failure Paths

```python
class MockExternalClient:
    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed

    async def call_api(self) -> Response:
        if self.should_succeed:
            return Response(success=True, data={...})
        else:
            # Return failure response, NOT exception
            return Response(success=False, error="API rate limited")

# Test both paths
class TestService:
    def test_success(self):
        mock = MockExternalClient(should_succeed=True)
        result = await service.process(mock)
        assert result.success is True

    def test_failure(self):
        mock = MockExternalClient(should_succeed=False)
        result = await service.process(mock)
        assert result.success is False
        assert "rate limited" in result.error
```

### 3. Mock Exceptions Separately from Failures

```python
class MockExternalClient:
    def __init__(self, should_succeed=True, should_raise=False):
        self.should_succeed = should_succeed
        self.should_raise = should_raise

    async def call_api(self):
        if self.should_raise:
            raise ConnectionError("Network unreachable")
        if not self.should_succeed:
            return Response(success=False, error="API error")
        return Response(success=True, data={...})

# Test all three cases
def test_success(): ...
def test_semantic_failure(): ...  # response.success=False
def test_exception(): ...          # raises exception
```

---

## Protocol-Based Mocking

Use Protocol classes to ensure mocks match interface contracts:

```python
from typing import Protocol

class InstagramClientProtocol(Protocol):
    async def create_container(self, image_url: str, caption: str) -> ContainerResponse: ...
    async def publish_container(self, container_id: str) -> PublishResponse: ...
    async def get_status(self, container_id: str) -> StatusResponse: ...

class MockInstagramClient:
    """Mock implementing InstagramClientProtocol."""

    def __init__(self, publish_success: bool = True):
        self.publish_success = publish_success
        self.calls: list[str] = []  # Track method calls

    async def create_container(self, image_url: str, caption: str) -> ContainerResponse:
        self.calls.append("create_container")
        return ContainerResponse(container_id="mock-123")

    async def publish_container(self, container_id: str) -> PublishResponse:
        self.calls.append("publish_container")
        if self.publish_success:
            return PublishResponse(success=True, media_id="media-456")
        return PublishResponse(success=False, error_message="Publishing failed")
```

---

## Test Assertion Patterns

### Explicit Success Checks

```python
# Good - explicit boolean check
assert response.success is True
assert response.success is False

# Bad - truthy check (can miss None, 0, etc.)
assert response.success
assert not response.success
```

### Verify Mock Interactions

```python
def test_publish_flow(self):
    mock_client = MockInstagramClient()
    publisher = InstagramPublisher(mock_client)

    await publisher.publish(item)

    # Verify correct methods called in order
    assert mock_client.calls == ["create_container", "publish_container"]
```

### Check Error Messages

```python
def test_failure_includes_error_details(self):
    mock_client = MockInstagramClient(publish_success=False)
    result = await publisher.publish(item)

    assert result.success is False
    assert result.error_message is not None
    assert "failed" in result.error_message.lower()
```

---

## Checklist for Mock Implementation

- [ ] Mock returns response objects with `success` attribute
- [ ] Mock can simulate both success and failure responses
- [ ] Mock can simulate exceptions (network errors, timeouts)
- [ ] Consumer code checks `response.success`, not just absence of exception
- [ ] Tests explicitly verify `is True` / `is False`, not truthy values
- [ ] Tests cover: success, semantic failure, and exception cases

---

## Reference Implementation

See [tests/core/publishing/test_instagram_publisher.py](../tests/core/publishing/test_instagram_publisher.py) for the corrected `MockRetryMiddleware` pattern.

---

*Created: 2026-02-09*
*Based on: Epic 4 test_publish_failure bug fix*
