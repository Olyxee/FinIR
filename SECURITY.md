# Security Policy

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Open a private
[GitHub Security Advisory](https://github.com/Olyxee/finir/security/advisories/new)
for this repository. We aim to acknowledge within 5 business days.

Please include a description, a minimal reproduction (synthetic data only), and the
affected version(s).

## Supported versions

FinIR is pre-1.0. Security fixes target the latest released minor version.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅         |

## Scope and posture

FinIR is a library/runtime for financial computation. It:

- has **no network requirement** for its core, and makes no outbound calls;
- reads only files you point it at (a `.finir` model or a JSON model);
- parses its IR with a small, explicit parser — it does **not** `eval` arbitrary
  Python or execute untrusted code;
- treats a loaded `.finir`/JSON model as data, not code.

### Untrusted models

A `.finir` or model JSON file is executable configuration: it can reference kernels
and drive computation. Treat model files from untrusted sources with the same care
as any code input. FinIR does not sandbox custom kernels you register.

## No certifications claimed

FinIR claims no security certification. It provides sensible engineering defaults;
operators are responsible for securing their own deployment.
