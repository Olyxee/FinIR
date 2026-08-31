# Security Policy

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, open a private
[GitHub Security Advisory](https://github.com/Lethabo-Scofield/economic-intelligence-framework/security/advisories/new)
for this repository. We aim to acknowledge reports within 5 business days and to
provide a remediation timeline after triage.

Please include:

- A description of the vulnerability and its impact
- Steps to reproduce (a minimal, **synthetic** example — never real data)
- Affected version(s) and environment

## Supported versions

EIF is pre-1.0. Security fixes are applied to the latest released minor version.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅         |

## Scope and threat model

A full threat model lives in [docs/security.md](docs/security.md). In brief, EIF
processes potentially sensitive financial and business evidence, so it ships with
conservative defaults:

- Secrets are read only from environment variables; none are committed.
- File ingestion enforces size limits and a MIME allow-list, and handles paths
  safely.
- Persistence uses parameterized queries (SQLAlchemy); no string-built SQL.
- Optional PII redaction and content hashing are available for stored evidence.
- A **private mode** refuses to transmit evidence to any off-host model provider.

## What is out of scope

- Vulnerabilities in optional third-party providers (OpenAI, Anthropic, Gemini)
  or databases themselves — report those upstream.
- Findings that require running untrusted code you supplied to the framework.

## No certifications claimed

EIF does not claim any security certification (SOC 2, ISO 27001, etc.). It
provides sensible engineering defaults; operators remain responsible for securing
their own deployment.
