"""Generate article/corpus.bib with the included studies cited in the article.

The citation keys are the record ids (S###, D###, I###), so every citation in
the article traces back to data/screening/extraction_all.csv. Metadata come from
data/included/<db>_included.csv. Both language versions are scanned.

Usage: python3 scripts/07_make_corpus_bib.py
"""
import csv
import re

from paths import ARTICLE, DATABASES, included_csv

TEX_FILES = ("main.tex", "main_es.tex")


def cited_keys():
    keys = set()
    for name in TEX_FILES:
        tex = (ARTICLE / name).read_text(encoding="utf-8")
        for group in re.findall(r"\\cite[tp]?\{([^}]*)\}", tex):
            keys.update(k.strip() for k in group.split(","))
    return sorted(k for k in keys if re.fullmatch(r"[SDI]\d{3}", k))


def latex_escape(text):
    for char in "&%_#":
        text = text.replace(char, "\\" + char)
    return text


def bib_entry(key, record):
    conference = record["Document Type"] == "Conference Paper"
    fields = {
        "author": " and ".join(a.strip() for a in record["Authors"].split(";") if a.strip()),
        "title": "{" + latex_escape(record["Title"]) + "}",
        "year": record["Year"],
        "booktitle" if conference else "journal": latex_escape(record["Source title"]),
    }
    if record["DOI"]:
        fields["doi"] = record["DOI"]
    body = ",\n".join(f"  {name} = {{{value}}}" for name, value in fields.items())
    return f"@{'inproceedings' if conference else 'article'}{{{key},\n{body}\n}}"


def main():
    records = {}
    for db in DATABASES:
        with open(included_csv(db), encoding="utf-8", newline="") as f:
            records.update({row["EID"]: row for row in csv.DictReader(f)})
    keys = cited_keys()
    missing = [k for k in keys if k not in records]
    if missing:
        raise SystemExit(f"cited records that are not included studies: {missing}")
    entries = [bib_entry(k, records[k]) for k in keys]
    (ARTICLE / "corpus.bib").write_text("\n\n".join(entries) + "\n", encoding="utf-8")
    print(f"corpus.bib: {len(entries)} entries")


if __name__ == "__main__":
    main()
