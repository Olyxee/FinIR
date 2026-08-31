# Security & Threat Model

EIF processes potentially sensitive financial and business evidence. It ships with
conservative defaults. This document is the threat model referenced by
[SECURITY.md](../SECURITY.md).

> EIF claims **no** security certification (SOC 2, ISO 27001, etc.). It provides
> engineering defaults; operators remain responsible for their deployment.

## Assets

- Business/financial **evidence** (may contain PII and confidential figures).
- Derived **observations, events, and impacts**.
- **Provider credentials** (API keys).

## Trust boundaries

- Evidence content is **untrusted input**. It is parsed defensively and never
  executed.
- External model providers are a boundary: sending evidence to them transmits it
  off-host (mitigated by private mode).
- The database is a trust boundary; access it over TLS in production.

## Controls (built in)

| Control | Where |
|---------|-------|
| No committed secrets; credentials via env vars only | `.env.example`, config |
| File **size limit** and **MIME allow-list** on ingestion | `connectors/base.py` |
| Safe file/path handling; content **hashing** | `connectors/base.py`, `utils/hashing.py` |
| **Parameterized SQL** (SQLAlchemy) — no string-built queries | `storage/sql` |
| Typed input validation (Pydantic, `extra="forbid"`) | `eif.domain` |
| Optional **PII redaction** hooks + redaction reporting | `utils/redaction.py` |
| **Tenant/organization IDs** on evidence and events | `SecurityContext` |
| **Private mode** refuses off-host providers | `providers/factory.py` |
| Structured **audit logging** (run/event/org ids) | `eif.logging` |
| Dependency pinning ranges | `pyproject.toml` |

## Known limitations

- Regex-based PII redaction is a safe default, **not** a comprehensive PII engine.
- PDF/Excel parsing relies on third-party libraries; keep them patched.
- The API ships without built-in authentication — put it behind your own
  gateway/authn. (No auth UI is provided by design.)
- No sandboxing of provider outputs beyond schema validation.

## Reporting

Report vulnerabilities privately via a GitHub Security Advisory — see
[SECURITY.md](../SECURITY.md). Do not include real data in reports.
