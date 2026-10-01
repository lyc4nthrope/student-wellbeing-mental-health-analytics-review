"""Merge the abstract coding with the record metadata, harmonize it and validate it.

Inputs
    data/screening/coding/*.json   coding of every abstract (closed vocabulary, docs/CODEBOOK.md)
    data/raw/*_clean.csv           metadata of the records (title, year, DOI, document type)
    scripts/harmonize.py           documented post-coding corrections
Outputs
    data/screening/extraction_<db>.csv, extraction_all.csv
    data/screening/harmonization_log.txt   every correction applied

The script stops with exit code 1 if a record is missing, a field is missing or a
value is outside the codebook vocabulary.

Usage: python3 scripts/03_build_extraction.py
"""
import csv
import json
import sys

from harmonize import apply_rules
from paths import CODING, DATABASE_LABEL, DATABASES, SCREENING, clean_csv, record_id

KEYS = ["screening", "screening_reason", "study_type", "population", "outcome", "data_source",
        "method", "xai", "best_result", "country", "quality_note", "summary_en"]
VOCABULARY = {
    "screening": {"INCLUDE", "DOUBTFUL", "EXCLUDE", "RETRACTED"},
    "study_type": {"predictive_model", "factor_analysis", "system_framework", "review", "descriptive", "other"},
    "population": {"university", "secondary_school", "vocational", "mixed_unspecified", "not_students"},
    "outcome": {"depression", "anxiety", "stress", "suicide", "general_mh_risk", "wellbeing", "emotions",
                "addiction", "other"},
    "data_source": {"survey", "public_dataset", "large_scale_survey", "institutional_records",
                    "social_media_text", "sensors_physiological", "smartphone_digital", "multimodal",
                    "not_reported"},
    "method": {"classic_ml", "ensemble_boosting", "deep_learning", "reinforcement_learning", "nlp_sentiment",
               "association_clustering", "statistical", "not_reported"},
    "xai": {"yes", "no"},
    "quality_note": {"clear", "vague"},
}
FIELDS = ["id", "database", "year", "doc_type", "title", "doi"] + KEYS


def load_coding():
    """All coding files merged into {record id: {field: value}}."""
    coding = {}
    for path in sorted(CODING.glob("*.json")):
        coding.update(json.loads(path.read_text(encoding="utf-8")))
    return coding


def validate(rid, codes):
    """Return the list of problems found in one coded record."""
    missing = [k for k in KEYS if k not in codes]
    if missing:
        return [f"{rid}: missing fields {missing}"]
    return [f"{rid}: {field} has values outside the codebook: {sorted(bad)}"
            for field, allowed in VOCABULARY.items()
            if (bad := set(codes[field].split(";")) - allowed)]


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(rows)


def main():
    coding = load_coding()
    errors, log, all_rows, expected = [], [], [], set()
    for db in DATABASES:
        with open(clean_csv(db), encoding="utf-8", newline="") as f:
            records = list(csv.DictReader(f))
        rows = []
        for i, record in enumerate(records, 1):
            rid = record_id(db, i)
            expected.add(rid)
            codes = coding.get(rid)
            if codes is None:
                errors.append(f"{rid}: not coded")
                continue
            problems = validate(rid, codes)
            if problems:
                errors += problems
                continue
            log += [f"{rid}: {change}" for change in apply_rules(rid, codes)]
            errors += validate(rid, codes)  # corrections must also respect the codebook
            rows.append([rid, DATABASE_LABEL[db], record["Year"], record["Document Type"],
                         record["Title"], record["DOI"]] + [codes[k] for k in KEYS])
        write_csv(SCREENING / f"extraction_{db}.csv", rows)
        all_rows += rows
        print(f"{DATABASE_LABEL[db]}: {len(rows)}/{len(records)} records coded")

    errors += [f"{rid}: coded but not in the metadata" for rid in sorted(set(coding) - expected)]
    write_csv(SCREENING / "extraction_all.csv", all_rows)
    (SCREENING / "harmonization_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"harmonization changes: {len(log)}")
    print(f"errors: {len(errors)}")
    for error in errors[:30]:
        print(f"  {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
