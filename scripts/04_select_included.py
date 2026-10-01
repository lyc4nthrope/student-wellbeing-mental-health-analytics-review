"""Write the metadata of the included studies, the input of the bibliometric analysis.

A record is kept when its screening decision in data/screening/extraction_all.csv
is INCLUDE. The output keeps the Scopus CSV layout that bibliometrix reads, but the
Abstract column is left empty: the figures do not use it, and abstracts are
copyrighted by their publishers, so they are not redistributed. The EID column
holds the record id (e.g. I001) that links each row to the screening data.

Usage: python3 scripts/04_select_included.py
"""
import csv

from paths import DATABASES, INCLUDED, SCREENING, clean_csv, included_csv, record_id, require_raw_exports

DROPPED_COLUMNS = ("Abstract",)


def screening_decisions():
    with open(SCREENING / "extraction_all.csv", encoding="utf-8", newline="") as f:
        return {row["id"]: row["screening"] for row in csv.DictReader(f)}


def main():
    require_raw_exports()
    decisions = screening_decisions()
    INCLUDED.mkdir(parents=True, exist_ok=True)
    for db in DATABASES:
        with open(clean_csv(db), encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            columns, records = reader.fieldnames, list(reader)
        kept = []
        for i, record in enumerate(records, 1):
            rid = record_id(db, i)
            if decisions[rid] != "INCLUDE":
                continue
            for column in DROPPED_COLUMNS:
                record[column] = ""
            record["EID"] = rid
            kept.append(record)
        with open(included_csv(db), "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(kept)
        print(f"{db}: {len(kept)} of {len(records)} records included")


if __name__ == "__main__":
    main()
