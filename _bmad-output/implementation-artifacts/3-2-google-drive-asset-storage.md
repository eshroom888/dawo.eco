# Story 3.2: Google Drive Asset Storage

Status: done

---

## Story

As an **operator**,
I want generated assets stored in organized Google Drive folders,
So that all visual content is accessible and properly archived.

---

## Acceptance Criteria

1. **Given** an asset is generated (Orshot graphic or Nano Banana image)
   **When** the asset storage agent saves it
   **Then** it's stored in the correct folder:
   - `DAWO.ECO/Assets/Generated/` for AI images
   - `DAWO.ECO/Assets/Orshot/` for branded graphics
   - `DAWO.ECO/Assets/Archive/` for used assets with performance data

2. **Given** an asset is saved
   **When** it's stored in Google Drive
   **Then** it includes metadata: generation date, prompt/template used, quality score
   **And** filename follows pattern: `{date}_{type}_{topic}_{id}.{ext}`

3. **Given** the folder structure doesn't exist
   **When** the first asset is saved
   **Then** the system creates the required folders automatically

---

## Tasks / Subtasks

- [x] Task 1: Implement Google Drive API client (AC: #1, #3)
  - [x] 1.1 Add google-auth and google-api-python-client to dependencies
  - [x] 1.2 Implement `_authenticate()` using service account credentials from constructor injection
  - [x] 1.3 Implement `_ensure_folder_structure()` to create DAWO.ECO/Assets/* folders
  - [x] 1.4 Cache folder IDs after creation to avoid repeated API lookups
  - [x] 1.5 Handle concurrent folder creation (check-then-create pattern)

- [x] Task 2: Complete upload_asset method (AC: #1, #2)
  - [x] 2.1 Create MediaFileUpload with proper MIME type detection
  - [x] 2.2 Route to correct folder based on AssetType enum
  - [x] 2.3 Set file metadata as custom properties (generation_date, prompt, quality_score)
  - [x] 2.4 Return DriveAsset with web_view_link and download_link
  - [x] 2.5 Wrap all API calls in retry middleware

- [x] Task 3: Implement filename generation (AC: #2)
  - [x] 3.1 Complete `_generate_filename()` with pattern: `{date}_{type}_{topic}_{id}.{ext}`
  - [x] 3.2 Sanitize topic for filename safety (remove special chars, limit length)
  - [x] 3.3 Use uuid4 for unique ID portion

- [x] Task 4: Implement get_asset method (AC: #1)
  - [x] 4.1 Retrieve file by ID with all metadata
  - [x] 4.2 Parse custom properties back to metadata dict
  - [x] 4.3 Return None with logging if file not found

- [x] Task 5: Implement move_to_archive method (AC: #1)
  - [x] 5.1 Move file from source folder to Archive folder
  - [x] 5.2 Append performance_data to existing metadata
  - [x] 5.3 Update DriveAsset with new folder_id

- [x] Task 6: Integrate retry middleware (AC: #1, #3)
  - [x] 6.1 Wrap all Drive API calls with RetryMiddleware from Story 1.5
  - [x] 6.2 Configure 3 retry attempts with exponential backoff
  - [x] 6.3 Handle rate limits via retry middleware
  - [x] 6.4 Log all retry attempts

- [x] Task 7: Register GoogleDriveClient in team_spec.py (AC: #1)
  - [x] 7.1 Add GoogleDriveClient as RegisteredService
  - [x] 7.2 Add capability tags: "asset_storage", "google_drive"
  - [x] 7.3 Configure for injection with credentials_path

- [x] Task 8: Create unit tests
  - [x] 8.1 Test folder structure creation with mock Drive service
  - [x] 8.2 Test upload routing to correct folder by AssetType
  - [x] 8.3 Test filename generation pattern
  - [x] 8.4 Test metadata storage and retrieval
  - [x] 8.5 Test move_to_archive preserves metadata
  - [x] 8.6 Test retry behavior with mocked failures
  - [x] 8.7 Test protocol compliance

- [x] Task 9: Create integration tests
  - [x] 9.1 Test end-to-end upload (skipped unless GOOGLE_DRIVE_INTEGRATION_TEST=1)
  - [x] 9.2 Test folder creation on first upload
  - [x] 9.3 Test file retrieval and metadata parsing
  - [x] 9.4 Test archive workflow

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Implementation-Patterns], [project-context.md#Integration-Clients]

This story completes the Google Drive integration client that was scaffolded in Epic 2. The existing `integrations/google_drive/client.py` has:
- `DriveAsset` dataclass with metadata support
- `AssetType` enum for folder routing
- `GoogleDriveClientProtocol` for type-safe injection
- `GoogleDriveClient` with TODO placeholders

**Key Task:** Replace TODO comments with actual Google Drive API calls.

### Existing Client Location

**Source:** [integrations/google_drive/client.py]

```
integrations/google_drive/
├── __init__.py        # Exports GoogleDriveClient, GoogleDriveClientProtocol, DriveAsset, AssetType
└── client.py          # GoogleDriveClient with placeholders (MODIFY THIS)
```

### Google Drive API Authentication

**Source:** Google Drive API v3 documentation

Use service account authentication for server-to-server access:

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

class GoogleDriveClient:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(
        self,
        credentials_path: str,
        root_folder_id: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
    ) -> None:
        if not credentials_path:
            raise ValueError("credentials_path is required")

        self._credentials_path = credentials_path
        self._root_folder_id = root_folder_id
        self._retry_config = retry_config or RetryConfig(
            max_attempts=3,
            backoff_base=1.0,
            backoff_multiplier=2.0,
        )
        self._folder_ids: dict[AssetType, str] = {}
        self._initialized = False
        self._service: Optional[Resource] = None

    def _authenticate(self) -> Resource:
        """Authenticate and return Drive service.

        Uses service account credentials for server-to-server access.
        """
        if self._service is not None:
            return self._service

        credentials = service_account.Credentials.from_service_account_file(
            self._credentials_path,
            scopes=self.SCOPES,
        )
        self._service = build('drive', 'v3', credentials=credentials)
        return self._service
```

### Folder Structure Creation (CRITICAL)

**Source:** [epics.md#Story-3.2], FR47

```python
async def _ensure_folder_structure(self) -> None:
    """Create folder structure if it doesn't exist.

    Folder hierarchy:
    - DAWO.ECO/
      - Assets/
        - Generated/  (AI images from Nano Banana)
        - Orshot/     (Branded graphics)
        - Archive/    (Used assets with performance data)
    """
    if self._initialized:
        return

    service = self._authenticate()

    # Create or find root folder
    root_id = await self._find_or_create_folder("DAWO.ECO", parent_id=self._root_folder_id)

    # Create Assets folder
    assets_id = await self._find_or_create_folder("Assets", parent_id=root_id)

    # Create type-specific folders
    for asset_type in AssetType:
        folder_name = {
            AssetType.AI_IMAGE: "Generated",
            AssetType.BRANDED_GRAPHIC: "Orshot",
            AssetType.ARCHIVE: "Archive",
        }[asset_type]

        folder_id = await self._find_or_create_folder(folder_name, parent_id=assets_id)
        self._folder_ids[asset_type] = folder_id
        logger.info("Folder %s ready: %s", folder_name, folder_id)

    self._initialized = True

async def _find_or_create_folder(
    self,
    name: str,
    parent_id: Optional[str] = None,
) -> str:
    """Find existing folder or create new one.

    Uses check-then-create pattern to handle race conditions.
    """
    service = self._authenticate()

    # Search for existing folder
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    try:
        results = await with_retry(
            lambda: service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
            ).execute(),
            config=self._retry_config,
        )

        files = results.get('files', [])
        if files:
            return files[0]['id']

        # Create folder if not found
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        folder = await with_retry(
            lambda: service.files().create(
                body=file_metadata,
                fields='id',
            ).execute(),
            config=self._retry_config,
        )
        return folder['id']

    except HttpError as e:
        logger.error("Drive API error during folder creation: %s", e)
        raise
```

### Upload Implementation (CRITICAL)

**Source:** [project-context.md#External-API-Calls]

```python
from googleapiclient.http import MediaFileUpload
import mimetypes

async def upload_asset(
    self,
    file_path: Path,
    asset_type: AssetType,
    metadata: dict[str, Any],
) -> DriveAsset:
    """Upload an asset to Google Drive.

    Routes to correct folder based on asset_type.
    Stores metadata as custom file properties.
    """
    await self._ensure_folder_structure()

    service = self._authenticate()
    folder_id = self._folder_ids[asset_type]

    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    mime_type = mime_type or 'application/octet-stream'

    # Generate filename
    topic = metadata.get('topic', 'content')
    extension = file_path.suffix.lstrip('.')
    filename = self._generate_filename(asset_type, topic, extension)

    # Prepare metadata as properties
    properties = {
        'generation_date': datetime.now(timezone.utc).isoformat(),
        'quality_score': str(metadata.get('quality_score', '')),
    }
    if 'prompt' in metadata:
        properties['prompt'] = metadata['prompt'][:500]  # Limit property size
    if 'template_id' in metadata:
        properties['template_id'] = metadata['template_id']

    file_metadata = {
        'name': filename,
        'parents': [folder_id],
        'properties': properties,
    }

    media = MediaFileUpload(
        str(file_path),
        mimetype=mime_type,
        resumable=True,
    )

    try:
        file = await with_retry(
            lambda: service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink, mimeType, createdTime, properties',
            ).execute(),
            config=self._retry_config,
        )

        return DriveAsset(
            id=file['id'],
            name=file['name'],
            folder_id=folder_id,
            web_view_link=file.get('webViewLink', ''),
            download_link=file.get('webContentLink', ''),
            mime_type=file['mimeType'],
            created_at=datetime.fromisoformat(file['createdTime'].rstrip('Z')).replace(tzinfo=timezone.utc),
            metadata=metadata,
        )

    except HttpError as e:
        logger.error("Drive API error during upload: %s", e)
        raise
```

### Filename Generation

**Source:** [epics.md#Story-3.2]

```python
import re
import uuid

def _generate_filename(
    self,
    asset_type: AssetType,
    topic: str,
    extension: str,
) -> str:
    """Generate filename following pattern: {date}_{type}_{topic}_{id}.{ext}

    Examples:
    - 20260207_generated_lionsmane_a1b2c3d4.png
    - 20260207_orshot_wellness_e5f6g7h8.jpg
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    # Sanitize topic: lowercase, alphanumeric only, max 30 chars
    safe_topic = re.sub(r'[^a-z0-9]', '', topic.lower())[:30]
    if not safe_topic:
        safe_topic = "content"

    # Generate short unique ID
    short_id = str(uuid.uuid4())[:8]

    return f"{date_str}_{asset_type.value}_{safe_topic}_{short_id}.{extension}"
```

### Move to Archive Pattern

**Source:** [epics.md#Story-3.9], FR50

```python
async def move_to_archive(
    self,
    file_id: str,
    performance_data: dict[str, Any],
) -> DriveAsset:
    """Move asset to archive with performance data.

    Preserves original metadata and appends performance metrics.
    """
    await self._ensure_folder_structure()

    service = self._authenticate()
    archive_folder_id = self._folder_ids[AssetType.ARCHIVE]

    try:
        # Get current file with metadata
        current = await with_retry(
            lambda: service.files().get(
                fileId=file_id,
                fields='id, name, parents, mimeType, createdTime, properties',
            ).execute(),
            config=self._retry_config,
        )

        # Build updated properties
        existing_props = current.get('properties', {})
        updated_props = {
            **existing_props,
            'archived_at': datetime.now(timezone.utc).isoformat(),
            'engagement_rate': str(performance_data.get('engagement_rate', '')),
            'conversions': str(performance_data.get('conversions', '')),
        }

        # Move to archive folder (remove from current parents, add to archive)
        current_parents = current.get('parents', [])

        file = await with_retry(
            lambda: service.files().update(
                fileId=file_id,
                addParents=archive_folder_id,
                removeParents=','.join(current_parents),
                body={'properties': updated_props},
                fields='id, name, webViewLink, webContentLink, mimeType, createdTime, properties',
            ).execute(),
            config=self._retry_config,
        )

        return DriveAsset(
            id=file['id'],
            name=file['name'],
            folder_id=archive_folder_id,
            web_view_link=file.get('webViewLink', ''),
            download_link=file.get('webContentLink', ''),
            mime_type=file['mimeType'],
            created_at=datetime.fromisoformat(file['createdTime'].rstrip('Z')).replace(tzinfo=timezone.utc),
            metadata={**existing_props, 'performance': performance_data},
        )

    except HttpError as e:
        logger.error("Drive API error during archive: %s", e)
        raise
```

### Retry Middleware Integration

**Source:** [project-context.md#External-API-Calls], Story 1.5

```python
from library.middleware.retry import with_retry, RetryConfig
from googleapiclient.errors import HttpError

# Rate limit handling: 403 userRateLimitExceeded should wait and retry
# but not count against max_attempts

async def _wrapped_api_call(self, api_call: Callable) -> Any:
    """Wrap API call with retry middleware and rate limit handling."""
    try:
        return await with_retry(api_call, config=self._retry_config)
    except HttpError as e:
        if e.resp.status == 403 and 'userRateLimitExceeded' in str(e):
            logger.warning("Rate limit hit, waiting 60s before retry")
            await asyncio.sleep(60)
            return await with_retry(api_call, config=self._retry_config)
        raise
```

### LLM Tier Assignment

**Source:** [project-context.md#LLM-Tier-Assignment]

This story does **NOT** involve LLM calls - it's pure API integration. No tier assignment needed.

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- `claude-haiku`, `claude-sonnet`, `claude-opus`
- Any hardcoded model IDs

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [3-1-shopify-product-data-integration.md#Completion-Notes]

| Learning | How to Apply |
|----------|--------------|
| Architecture Decision: Use API directly, not MCP tools | Use google-api-python-client directly, MCP is for Claude Code |
| Complete `__all__` exports from day 1 | Already done in `__init__.py` - verify no new exports needed |
| Config injection pattern | Accept credentials_path and root_folder_id via constructor |
| `datetime` deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| Add logging to exception handlers | All API errors logged before raising |
| F-string logging anti-pattern | Use % formatting for lazy evaluation |
| Integration tests separate | Create test_integration.py with proper skip markers |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], [architecture.md#Anti-Patterns]

1. **NEVER load credentials directly** - Accept credentials_path via injection
2. **NEVER make direct API calls** - Use retry middleware wrapper
3. **NEVER swallow exceptions without logging** - Log all API failures
4. **NEVER hardcode folder IDs** - Discover/create dynamically

### Dependencies

**Required packages (add to requirements.txt):**
```
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
```

### Environment Variables

**Source:** .env configuration

```env
GOOGLE_DRIVE_CREDENTIALS_PATH=credentials/google-drive-service-account.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=  # Optional: specific folder to use as root
```

### Registration in team_spec.py

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py (add to existing registrations)

from integrations.google_drive import GoogleDriveClient, GoogleDriveClientProtocol

SERVICES = [
    # ... existing services
    RegisteredService(
        name="google_drive_client",
        service_class=GoogleDriveClient,
        capabilities=["asset_storage", "google_drive"],
        config={
            "credentials_path": os.environ.get("GOOGLE_DRIVE_CREDENTIALS_PATH"),
            "root_folder_id": os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER_ID"),
        },
    ),
]
```

### Test Fixtures

**Source:** Story 1.5 patterns, [3-1-shopify-product-data-integration.md#Test-Fixtures]

```python
# tests/integrations/test_google_drive/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path

@pytest.fixture
def mock_drive_service():
    """Mock Google Drive service for unit tests."""
    service = MagicMock()

    # Mock files().list()
    service.files().list().execute.return_value = {
        'files': []  # Empty by default, folder doesn't exist
    }

    # Mock files().create()
    service.files().create().execute.return_value = {
        'id': 'mock_file_id_123',
        'name': 'test_file.png',
        'webViewLink': 'https://drive.google.com/file/d/mock_file_id_123/view',
        'webContentLink': 'https://drive.google.com/uc?id=mock_file_id_123',
        'mimeType': 'image/png',
        'createdTime': '2026-02-07T12:00:00.000Z',
        'properties': {},
    }

    return service

@pytest.fixture
def google_drive_client(mock_drive_service, tmp_path):
    """GoogleDriveClient with mocked service."""
    # Create fake credentials file
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text('{"type": "service_account"}')

    with patch('integrations.google_drive.client.service_account.Credentials.from_service_account_file'):
        with patch('integrations.google_drive.client.build', return_value=mock_drive_service):
            client = GoogleDriveClient(
                credentials_path=str(creds_file),
            )
            client._service = mock_drive_service
            return client

@pytest.fixture
def sample_image_file(tmp_path):
    """Create a sample image file for upload tests."""
    image_file = tmp_path / "test_image.png"
    # Write minimal PNG header
    image_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
    return image_file
```

### Project Structure Notes

- **Location**: `integrations/google_drive/` (existing module, modify in place)
- **Dependencies**: Retry middleware (Story 1.5), google-api-python-client
- **Used by**: Content generators (Stories 3.3-3.5), Asset tracker (Story 3.9)
- **Authentication**: Service account credentials (server-to-server)
- **Environment vars**: `GOOGLE_DRIVE_CREDENTIALS_PATH`, `GOOGLE_DRIVE_ROOT_FOLDER_ID`

### References

- [Source: epics.md#Story-3.2] - Original story requirements
- [Source: architecture.md#External-Integration-Points] - Integration patterns
- [Source: project-context.md#Integration-Clients] - Protocol + Implementation pattern
- [Source: project-context.md#External-API-Calls] - Retry middleware requirement
- [Source: integrations/google_drive/client.py] - Existing skeleton to complete
- [Source: 3-1-shopify-product-data-integration.md] - Previous story learnings

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No debug issues encountered

### Completion Notes List

- Implemented full Google Drive API client replacing TODO placeholders
- Service account authentication with cached service instance
- Folder structure auto-creation with asyncio.Lock for concurrent safety
- All API calls wrapped with RetryMiddleware from Story 1.5
- Filename pattern: `{date}_{type}_{topic}_{id}.{ext}` with sanitization
- 29 unit tests covering all functionality (100% pass rate)
- Integration tests with environment variable skip marker
- Registered GoogleDriveClient as service with capabilities ["asset_storage", "google_drive"]
- Created requirements.txt with google-auth and google-api-python-client

### Learnings

| Learning | Apply To Future Stories |
|----------|------------------------|
| RetryMiddleware uses execute_with_retry() not with_retry() | Check actual middleware implementation before coding |
| asyncio.Lock needed for _ensure_folder_structure | Use lock for any async initialization that mutates shared state |
| run_in_executor for sync Google API calls | Wrap synchronous SDK calls in executor for async compatibility |

### File List

- integrations/google_drive/client.py (MODIFIED - full implementation)
- integrations/google_drive/__init__.py (UNCHANGED)
- integrations/__init__.py (MODIFIED - added Google Drive exports)
- teams/dawo/team_spec.py (MODIFIED - added GoogleDriveClient registration)
- requirements.txt (CREATED - project dependencies including Google APIs)
- tests/integrations/__init__.py (CREATED - package init)
- tests/integrations/test_google_drive/__init__.py (CREATED)
- tests/integrations/test_google_drive/conftest.py (CREATED - test fixtures)
- tests/integrations/test_google_drive/test_client.py (CREATED - 29 unit tests)
- tests/integrations/test_google_drive/test_integration.py (CREATED - integration tests)

### Change Log

- 2026-02-07: Story 3.2 implementation complete - GoogleDriveClient with full CRUD operations, retry middleware, and comprehensive tests
- 2026-02-07: Code review fixes applied:
  - Fixed deprecated `asyncio.get_event_loop()` → `asyncio.get_running_loop()` (Python 3.12+ compat)
  - Added type annotation to SCOPES class variable
  - Removed unused imports (partial, HttpError)
  - Created missing `tests/integrations/__init__.py`
  - Updated File List to include `integrations/__init__.py`

