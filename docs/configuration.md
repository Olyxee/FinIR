# Configuration

Configuration comes from three layers, in increasing precedence:

1. Built-in defaults (a bare `Config()` is fully working: SQLite + mock provider).
2. A YAML/TOML file (`eif.yaml`, `--config`, or `EIF_CONFIG_FILE`).
3. Environment variables (`EIF_*` and provider-native keys).

## Example `eif.yaml`

```yaml
organization:
  id: acme
  currency: ZAR

materiality:
  absolute: 500000        # material if |expected value| >= this
  relative_revenue: 0.01  # or >= 1% of annual_revenue (if set)
  relative_cost: 0.02     # or >= 2% of annual_cost (if set)
  annual_revenue: null
  annual_cost: null

models:
  reasoning:  {provider: mock}
  extraction: {provider: mock}
  embeddings: {provider: local}

storage:
  database_url: sqlite:///./eif.db
  echo_sql: false

security:
  max_file_bytes: 26214400
  redact_pii: false

logging:
  level: INFO
  format: json

private_mode: false
```

## Environment variables

| Variable | Effect |
|----------|--------|
| `EIF_ORGANIZATION_ID`, `EIF_ORGANIZATION_CURRENCY` | Tenancy + currency. |
| `EIF_DATABASE_URL` | SQLAlchemy URL (`sqlite:///…`, `postgresql+psycopg://…`, or `memory`). |
| `EIF_DEFAULT_LLM_PROVIDER` | Overrides reasoning + extraction provider. |
| `EIF_MAX_FILE_BYTES`, `EIF_REDACT_PII` | Security controls. |
| `EIF_PRIVATE_MODE` | Refuse off-host providers. |
| `EIF_LOG_LEVEL`, `EIF_LOG_FORMAT` | Logging. |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` | Provider credentials. |

See [.env.example](../.env.example) for the full list. Load in code:

```python
from eif.config import Config
cfg = Config.load()            # file (if present) + env overlay
cfg = Config.load("eif.yaml")  # explicit file
```
