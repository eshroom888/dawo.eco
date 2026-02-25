# PDF Generation Library Evaluation

**Date:** 2026-02-12
**Purpose:** Epic 6, Story 6-10 - On-Demand Violation Reports
**Decision:** WeasyPrint (Primary), ReportLab (Fallback)

---

## Decision Summary

**WeasyPrint** is recommended. HTML/CSS templates via Jinja2 provide the fastest development velocity for formal document layout.

| Criterion | WeasyPrint | ReportLab | FPDF2 | Playwright PDF |
|-----------|-----------|-----------|-------|---------------|
| Template approach | HTML/CSS + Jinja2 | Python code | Python code | HTML/CSS |
| Output quality | Excellent | Excellent | Adequate | Excellent |
| CSS Paged Media | Yes (@page, counters) | Manual PageTemplate | No | Limited |
| Image embedding | `<img>` + base64 URIs | `Image` flowable | `pdf.image()` | `<img>` tags |
| System deps | Cairo, Pango, GDK-PixBuf | **None** | **None** | Chromium (~280MB) |
| Windows install | Hard (GTK3/MSYS2) | **Trivial** | **Trivial** | Medium |
| Docker install | Easy (`apt-get`) | **Trivial** | **Trivial** | Medium |
| PDF/A archival | Yes (v57+) | No (PLUS only) | No | No |
| License | BSD | BSD | LGPL | Apache 2.0 |

## Why WeasyPrint

1. **Report structure maps naturally to HTML** — headings, tables, images, lists
2. **CSS `@page`** provides page numbers, running headers, controlled page breaks
3. **Jinja2 templates** enable layout iteration without touching Python code
4. **Base64 data URIs** for evidence screenshots avoid filesystem path issues
5. **PDF/A support** for regulatory archival submissions

## Architecture

```python
@runtime_checkable
class PDFGenerator(Protocol):
    async def generate_violation_report(self, report_data: ViolationReportData) -> bytes: ...
```

Implementation: `WeasyPrintPDFGenerator` with Jinja2 + `asyncio.to_thread(HTML(string=html).write_pdf)`

## Dependencies
```
weasyprint>=62.0
Jinja2>=3.1
```

Docker: `apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 fonts-noto-core`

## Fallback: ReportLab

If WeasyPrint's system dependencies prove problematic on Windows, ReportLab produces equivalent quality with zero native deps but requires 3-5x more code.

---

*Alternatives evaluated: ReportLab (fallback), FPDF2 (too limited), borb (AGPL risk), xhtml2pdf (poor CSS), wkhtmltopdf (deprecated)*
