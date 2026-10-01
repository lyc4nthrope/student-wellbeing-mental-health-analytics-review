"""Single source of truth for the project's file layout.

Every script imports its paths from here, so the pipeline runs the same way
from any working directory.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Data snapshot: all records were retrieved on 2026-09-28.
SNAPSHOT = "20260928"
DATABASES = ("ieee", "sciencedirect", "springerlink")
ID_PREFIX = {"ieee": "I", "sciencedirect": "D", "springerlink": "S"}
DATABASE_LABEL = {"ieee": "IEEE Xplore", "sciencedirect": "ScienceDirect", "springerlink": "SpringerLink"}

DATA = ROOT / "data"
RAW = DATA / "raw"                  # API exports (not versioned, see README)
THESAURUS = DATA / "thesaurus"
SCREENING = DATA / "screening"
CODING = SCREENING / "coding"       # abstract coding, one JSON file per batch
INCLUDED = DATA / "included"        # metadata of included studies, without abstracts
RESULTS = ROOT / "results"
ARTICLE = ROOT / "article"


def raw_csv(db: str) -> Path:
    """API export in Scopus CSV layout."""
    return RAW / f"bibliometria_{SNAPSHOT}_{db}.csv"


def clean_csv(db: str) -> Path:
    """API export after applying the keyword thesaurus."""
    return RAW / f"bibliometria_{SNAPSHOT}_{db}_clean.csv"


def included_csv(db: str) -> Path:
    return INCLUDED / f"{db}_included.csv"


def record_id(db: str, row_number: int) -> str:
    """Identifier of a record: database prefix + 1-based row number in the clean CSV."""
    return f"{ID_PREFIX[db]}{row_number:03d}"


def require_raw_exports():
    """Stop with a clear message when the API exports of the snapshot are missing."""
    missing = [clean_csv(db).name for db in DATABASES if not clean_csv(db).exists()]
    if missing:
        raise SystemExit(
            f"Missing in data/raw/: {', '.join(missing)}\n"
            "The raw API exports are not published (they contain publisher abstracts). "
            "Run steps 01-02 to create them, or use `make published` to work from the published data.")
