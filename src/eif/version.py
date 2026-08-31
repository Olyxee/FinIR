"""Single source of truth for the EIF version."""

from __future__ import annotations

__version__ = "0.1.0"

# Schema version for persisted domain objects. Bump when the on-disk / on-wire
# representation of a core domain object changes in a backward-incompatible way.
SCHEMA_VERSION = "1"
