"""
cricket_nrr.loaders
~~~~~~~~~~~~~~~~~~~~
Data ingestion facade.

Provides three loaders:

- :func:`from_csv`          — summary-level matches CSV
- :func:`from_cricsheet_csv` — Cricsheet ball-by-ball CSV
- :func:`from_cricsheet_json` — Cricsheet standard JSON
- :func:`from_dict`          — raw Python dict (no file I/O)
"""

from .csv_loader import from_csv
from .cricsheet_loader import from_cricsheet_csv, from_cricsheet_json
from .dict_loader import from_dict

__all__ = [
    "from_csv",
    "from_cricsheet_csv",
    "from_cricsheet_json",
    "from_dict",
]
