"""Apply the keyword thesaurus to the per-database API exports.

Only the "Author Keywords" and "Index Keywords" columns change; every other
column is copied unchanged. The raw exports are never modified: the output is
written to data/raw/bibliometria_<snapshot>_<db>_clean.csv. The script also
writes the same thesaurus in VOSviewer format.

Usage: python3 scripts/02_clean_keywords.py
"""
import csv

from paths import DATABASES, THESAURUS, clean_csv, raw_csv

KEYWORD_COLUMNS = ("Author Keywords", "Index Keywords")
# Sample keywords of the IEEE conference template that some authors never replaced
PLACEHOLDER_TERMS = {"component", "formatting", "style", "styling", "insert", "insert (key words)"}


def load_thesaurus(path):
    """Return {variant (lower case): canonical term}."""
    with open(path, encoding="utf-8", newline="") as f:
        return {row["variant"]: row["canonical"] for row in csv.DictReader(f)}


def clean_cell(cell, thesaurus):
    """Map variants to their canonical term, drop template placeholders and
    duplicates within the record."""
    seen, out = set(), []
    for term in cell.split(";"):
        term = term.strip()
        if not term or term.lower() in PLACEHOLDER_TERMS:
            continue
        term = thesaurus.get(term.lower(), term)
        if term.lower() not in seen:
            seen.add(term.lower())
            out.append(term)
    return "; ".join(out)


def clean_file(src, dst, thesaurus):
    """Write the cleaned copy of one export; return (records, changed cells)."""
    with open(src, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns, rows = reader.fieldnames, list(reader)
    changed = 0
    for row in rows:
        for col in KEYWORD_COLUMNS:
            new = clean_cell(row[col], thesaurus)
            changed += new != row[col]
            row[col] = new
    with open(dst, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), changed


def write_vosviewer_thesaurus(thesaurus, path):
    """VOSviewer format: tab-separated, header 'label<TAB>replace by'."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("label\treplace by\n")
        for variant, canonical in sorted(thesaurus.items()):
            f.write(f"{variant}\t{canonical}\n")


def main():
    thesaurus = load_thesaurus(THESAURUS / "keyword_thesaurus.csv")
    for db in DATABASES:
        if not raw_csv(db).exists():
            print(f"{db}: {raw_csv(db).name} not found, skipped")
            continue
        n, changed = clean_file(raw_csv(db), clean_csv(db), thesaurus)
        print(f"{db}: {n} records, {changed} keyword cells changed")
    write_vosviewer_thesaurus(thesaurus, THESAURUS / "vosviewer_thesaurus_keywords.txt")
    print(f"thesaurus: {len(thesaurus)} variants -> {len(set(thesaurus.values()))} terms")


if __name__ == "__main__":
    main()
