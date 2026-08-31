# Privacy & Local Mode

Financial evidence is sensitive. EIF is designed so a company can run it entirely
on its own infrastructure, sending nothing to external model providers.

## Fully local by default

Out of the box EIF uses:

- the **deterministic mock provider** (no network),
- **local embeddings** (hash-based),
- a **local database** (SQLite).

`pip install economic-intelligence-framework` with no extras and no keys gives you
a working, fully-local system.

## Private mode

Set `private_mode: true` (or `EIF_PRIVATE_MODE=true`). Any attempt to construct a
provider that would transmit evidence off-host raises `PrivacyViolationError`.
Local and mock providers remain available. This is a hard guard, enforced in
`providers/factory.py`, not a soft preference.

## Where external APIs may receive data

If you deliberately configure a hosted provider (OpenAI, Anthropic, Gemini) for a
role, then the evidence text sent to that role's calls leaves your host. EIF marks
such providers with `sends_data_offhost = True`. To keep everything local while
still using models, point the OpenAI-compatible provider at a **local endpoint**
(vLLM, Ollama, LM Studio) via `OPENAI_BASE_URL` — EIF treats a configured base URL
as local.

## Data minimization

- Only the roles you configure with a hosted provider send data; extraction can be
  fully deterministic and never calls any model.
- Optional PII redaction (`redact_pii: true`) masks emails, card/IBAN/phone
  patterns in stored evidence content, and records *that* PII was present without
  storing it.
- Evidence carries tenancy (`organization_id`, `business_unit`) and a
  classification label so you can enforce access controls at your boundary.

## Recommendation

For regulated or highly sensitive deployments: keep `private_mode: true`, use a
local model endpoint for interpretation (or the deterministic extractor alone),
and run PostgreSQL within your own network.
