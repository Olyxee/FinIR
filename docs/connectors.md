# Connectors

A connector turns an external source (file, payload, directory, inbox) into one or
more `Evidence` objects in the common format.

## Reference connectors (offline, no credentials)

| Connector | Handles | Extra |
|-----------|---------|-------|
| `TextConnector` | `.txt`/`.md`/`.log` files and raw strings | — |
| `EmailConnector` | `.eml` (RFC-822), extracts headers + body + date | — |
| `JsonConnector` | `.json` files and in-memory dict/list | — |
| `CsvConnector` | `.csv`/`.tsv` → pipe-rendered table + summary | — |
| `ExcelConnector` | `.xlsx`/`.xlsm` (one Evidence per sheet) | `[excel]` |
| `PdfConnector` | `.pdf` text extraction | `[pdf]` |
| `AudioConnector` | audio via a `TranscriptionProvider` | — |
| `ImageConnector` | images via a `VisionProvider` | — |
| `DirectoryConnector` | recursively ingests supported files in a dir | — |

The `default_registry()` wires all of these with specific-first dispatch.

## Integration placeholders (typed interfaces)

For integrations that need live credentials, EIF ships **documented interfaces**,
not fake implementations: `InboxConnector`, `ChatConnector` (Slack/Teams),
`CrmConnector`, `ErpConnector`, `DatabaseConnector`, `CloudStorageConnector`. Each
raises a clear `NotImplementedError` describing what a real subclass must do. This
keeps EIF installable and testable offline.

## Writing a connector

```python
from eif.connectors import EIFConnector
from eif.domain.enums import Modality, SourceType

class MyConnector(EIFConnector):
    modality = Modality.API
    source_type = SourceType.API

    def can_handle(self, source):
        return isinstance(source, MyPayload)

    def load(self, source):
        return [self.make_text_evidence(source.render(), source="my-system")]
```

`make_text_evidence` handles hashing, size limits, MIME checks, optional PII
redaction, and tenancy for you. Register it:

```python
from eif.connectors import default_registry
reg = default_registry()
reg.register(MyConnector(), first=True)
```

## Security

All file reads enforce a size limit and MIME allow-list and use safe path
handling. See [security.md](security.md).
