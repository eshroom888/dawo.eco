# Immutable Evidence Storage Design

**Purpose:** Design approach for storing violation evidence with integrity guarantees for Stories 6-8 and 6-9.
**Requirement:** Evidence must be tamper-proof, legally defensible, and searchable.

---

## Design Principles

1. **Immutability** - Evidence records cannot be modified after creation
2. **Integrity verification** - SHA-256 hashes verify screenshot authenticity
3. **Audit trail** - All access/verification attempts are logged
4. **Searchability** - Filter by competitor, violation type, date, severity
5. **Follows existing patterns** - PostgreSQL + SQLAlchemy models, Protocol-based DI

---

## Data Model

### Evidence Table

```python
class Evidence(Base):
    """Immutable violation evidence record.

    Once created, content fields (screenshot_path, screenshot_hash,
    claim_text, source_url) cannot be modified.
    """
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())

    # Source identification
    competitor_name: Mapped[str] = mapped_column(String(255), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50))  # "instagram_post", "website_page"

    # Violation details
    claim_text: Mapped[str] = mapped_column(Text)
    claim_category: Mapped[str] = mapped_column(String(50))  # treatment, prevention, enhancement, wellness
    violation_type: Mapped[str] = mapped_column(String(50), index=True)  # VIOLATION, SUSPECT, COMPLIANT
    severity: Mapped[str] = mapped_column(String(20), index=True)  # HIGH, MEDIUM, LOW
    regulation_violated: Mapped[str | None] = mapped_column(Text)  # e.g., "EC 1924/2006 Article 10"
    detection_reasoning: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)  # 0.0-1.0

    # Screenshot evidence
    screenshot_path: Mapped[str] = mapped_column(Text)  # Local storage path
    screenshot_hash: Mapped[str] = mapped_column(String(64))  # SHA-256 hex
    screenshot_size_bytes: Mapped[int] = mapped_column(Integer)

    # Timestamps
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # When screenshot was taken
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Metadata (flexible, JSONB)
    evidence_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Includes: engagement_metrics, hashtags, account_followers, page_title, etc.

    # Relationships
    audit_logs: Mapped[list["EvidenceAuditLog"]] = relationship(back_populates="evidence")

    __table_args__ = (
        Index("ix_evidence_captured_at", "captured_at", postgresql_using="btree"),
        Index("ix_evidence_competitor_date", "competitor_name", "captured_at"),
    )
```

### Evidence Audit Log Table

```python
class EvidenceAuditLog(Base):
    """Tracks all access and verification attempts on evidence."""
    __tablename__ = "evidence_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))

    action: Mapped[str] = mapped_column(String(50))  # "created", "verified", "downloaded", "report_included", "modification_blocked"
    actor: Mapped[str] = mapped_column(String(100))  # "system", "operator", "report_generator"
    details: Mapped[dict | None] = mapped_column(JSONB)  # Action-specific details
    hash_verified: Mapped[bool | None] = mapped_column(Boolean)  # Was hash correct at time of access?

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    evidence: Mapped["Evidence"] = relationship(back_populates="audit_logs")
```

---

## Immutability Enforcement

### Approach: Database-Level Triggers + Application-Level Guards

**Layer 1: Application guard (EvidenceRepository)**
```python
class EvidenceRepository:
    async def update(self, evidence_id: UUID, **kwargs) -> Never:
        """Evidence records are immutable. Updates are blocked."""
        await self._log_audit(evidence_id, "modification_blocked", details=kwargs)
        raise ImmutableEvidenceError(f"Evidence {evidence_id} cannot be modified")
```

**Layer 2: PostgreSQL trigger (migration)**
```sql
CREATE OR REPLACE FUNCTION prevent_evidence_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Allow audit_log additions (new rows) but block content changes
    IF OLD.screenshot_hash != NEW.screenshot_hash
       OR OLD.claim_text != NEW.claim_text
       OR OLD.source_url != NEW.source_url
       OR OLD.screenshot_path != NEW.screenshot_path THEN
        RAISE EXCEPTION 'Evidence records are immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER evidence_immutable_guard
BEFORE UPDATE ON evidence
FOR EACH ROW EXECUTE FUNCTION prevent_evidence_update();
```

**Layer 3: File system (screenshot storage)**
- Screenshots saved to dedicated directory: `evidence/screenshots/<YYYY-MM>/<uuid>.png`
- Files set read-only after creation (`os.chmod(path, 0o444)`)
- Directory structure prevents accidental deletion

---

## Screenshot Storage

### File Layout

```
evidence/
├── screenshots/
│   ├── 2026-02/
│   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.png
│   │   └── ...
│   └── 2026-03/
│       └── ...
└── reports/
    └── ...
```

### Integrity Hash Generation

```python
import hashlib
from pathlib import Path

async def capture_and_hash(screenshot_bytes: bytes, output_path: Path) -> str:
    """Save screenshot and return SHA-256 hash."""
    # 1. Hash the raw bytes BEFORE writing to disk
    sha256_hash = hashlib.sha256(screenshot_bytes).hexdigest()

    # 2. Write to disk
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(screenshot_bytes)

    # 3. Set read-only
    output_path.chmod(0o444)

    # 4. Verify by re-reading
    verification_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
    assert sha256_hash == verification_hash, "Hash mismatch after write"

    return sha256_hash
```

### Verification

```python
async def verify_evidence_integrity(evidence: Evidence) -> bool:
    """Verify screenshot hasn't been tampered with."""
    screenshot_path = Path(evidence.screenshot_path)
    if not screenshot_path.exists():
        return False

    current_hash = hashlib.sha256(screenshot_path.read_bytes()).hexdigest()
    return current_hash == evidence.screenshot_hash
```

---

## Repository Protocol

```python
@runtime_checkable
class EvidenceRepositoryProtocol(Protocol):
    async def create(self, evidence: EvidenceCreate) -> Evidence: ...
    async def get_by_id(self, evidence_id: UUID) -> Evidence | None: ...
    async def search(self, filters: EvidenceFilters) -> list[Evidence]: ...
    async def verify_integrity(self, evidence_id: UUID) -> bool: ...
    async def get_by_competitor(self, competitor_name: str) -> list[Evidence]: ...
    async def get_audit_log(self, evidence_id: UUID) -> list[EvidenceAuditLog]: ...
    async def download_package(self, evidence_id: UUID) -> EvidencePackage: ...
```

### Filter Schema

```python
@dataclass(frozen=True)
class EvidenceFilters:
    competitor_name: str | None = None
    violation_type: str | None = None  # VIOLATION, SUSPECT
    severity: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    claim_keywords: str | None = None
    limit: int = 50
    offset: int = 0
```

---

## Why Not External Immutable Storage?

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Local PostgreSQL + files | Simple, no external deps, fast | Single point of failure | **Selected for MVP** |
| Google Drive (existing) | Already integrated | Not truly immutable, API rate limits | Future consideration |
| S3 + Object Lock | True immutability, scalable | AWS dependency, cost, complexity | Overkill for MVP |
| IPFS | Content-addressed, distributed | Complexity, latency, overkill | Not suitable |

**Rationale:** PostgreSQL triggers + application guards + file system permissions provide sufficient immutability for regulatory evidence. The SHA-256 hash chain provides integrity verification. If external audit requirements increase, migration to S3 Object Lock is a natural evolution.

---

## Integration Points

| Story | Integration |
|-------|-------------|
| 6-7 (Violation Detection) | Creates Evidence records when violations are detected |
| 6-8 (Evidence Collection) | Captures screenshots, generates hashes, saves to storage |
| 6-9 (Evidence Database) | Exposes search/filter API, integrity verification |
| 6-10 (Violation Reports) | Reads evidence for PDF report generation |

---

*Created: 2026-02-12*
*Based on: Epic 6 Story requirements + existing DAWO.ECO architecture patterns*
