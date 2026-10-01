#!/usr/bin/env python3
"""Collect bibliographic metadata from IEEE Xplore, Springer Nature and
ScienceDirect (via Scopus, Elsevier-published records), enrich it with
OpenAlex, deduplicate by DOI and export per database one RIS (for Zotero)
and one Scopus-format CSV (for bibliometrix).
Only journal articles, conference papers and early access articles that
have an abstract are kept.

Keys are read from the .env file at the repository root (or the environment);
see .env.example. Keys are never written to the output files or the log.
    IEEE_API_KEY, SPRINGER_META_API_KEY, ELSEVIER_API_KEY,
    ELSEVIER_INSTTOKEN (optional), OPENALEX_API_KEY (optional),
    OPENALEX_MAILTO (optional)

Usage:
    python3 scripts/01_fetch_metadata.py                      # all sources, all results
    python3 scripts/01_fetch_metadata.py --max-per-source 50  # quick test
    python3 scripts/01_fetch_metadata.py --sources ieee       # only IEEE

Output: data/raw/<prefix>_<db>.ris and .csv (default prefix: bibliometria_<today>).
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from paths import RAW, ROOT

YEAR_FROM, YEAR_TO = 2021, 2026
SLEEP_SECONDS = 1.0
MAX_RETRIES = 4

# Topic: "Student well-being and mental health analytics".
# Search equation (approved), same concepts in each API's syntax:
#   (STUDENTS) AND (WELLBEING) AND (ANALYTICS), 2021-2026
STUDENTS = ['student*', '"higher education"', 'universit*', 'college*']
WELLBEING = ['"well-being"', 'wellbeing', '"mental health"',
             '"psychological well-being"', '"emotional well-being"']
ANALYTICS = ['analytics', '"learning analytics"', '"data analytics"',
             '"predictive analytics"', '"data mining"', '"machine learning"',
             '"big data"']
# Springer keyword: field does not expand wildcards
STUDENTS_SPRINGER = ['student', 'students', '"university students"',
                     '"college students"', '"higher education"']
# IEEE searches "All Metadata" by default, including author affiliations
# (universit* then matches any university author); scope to title/abstract/terms
IEEE_FIELDS = ['"Document Title"', '"Abstract"', '"Index Terms"']


# Document types kept (journal articles, conference papers, early access).
# Values are the raw type labels each API returns.
IEEE_TYPES = {"Conferences", "Journals", "Early Access Articles"}
SPRINGER_TYPES = {"Article", "Chapter ConferencePaper"}
SCOPUS_SUBTYPES = {"Article", "Conference Paper"}  # "in press" is also "Article"


def _or(terms, field=""):
    return "(" + " OR ".join(field + t for t in terms) + ")"


def _or_fields(terms, fields):
    return "(" + " OR ".join(f"{f}:{t}" for t in terms for f in fields) + ")"


QUERIES = {
    "ieee": " AND ".join(_or_fields(b, IEEE_FIELDS)
                         for b in (STUDENTS, WELLBEING, ANALYTICS)),
    # Springer free-text search matches full text (100k+ noisy hits) and
    # title: is a premium feature, so every group uses the keyword field.
    "springer": " AND ".join(_or(b, "keyword:")
                             for b in (STUDENTS_SPRINGER, WELLBEING, ANALYTICS)),
    "scopus": (f"TITLE-ABS-KEY({_or(STUDENTS)} AND {_or(WELLBEING)} AND {_or(ANALYTICS)})"
               f" AND PUBYEAR > {YEAR_FROM - 1} AND PUBYEAR < {YEAR_TO + 1}"
               " AND PUBLISHER(elsevier)"),
}


# --------------------------------------------------------------------------
# Infrastructure
# --------------------------------------------------------------------------
def load_env():
    env = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if v})
    return env


class SourceUnavailable(Exception):
    """Raised when a source cannot be used (bad/inactive key, no access)."""


def http_json(url, headers=None):
    """GET JSON with retry on 429/5xx. Raises SourceUnavailable on 401/403."""
    headers = {"User-Agent": "bibliometria-script/1.0", **(headers or {})}
    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode(errors="replace")
            if e.code in (401, 403):
                raise SourceUnavailable(f"HTTP {e.code}: {body}")
            if e.code == 429 or e.code >= 500:
                wait = SLEEP_SECONDS * 2 ** attempt
                print(f"    HTTP {e.code}, retry {attempt}/{MAX_RETRIES} in {wait:.0f}s")
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {e.code}: {body}")
        except (urllib.error.URLError, TimeoutError) as e:
            wait = SLEEP_SECONDS * 2 ** attempt
            print(f"    network error ({e}), retry {attempt}/{MAX_RETRIES} in {wait:.0f}s")
            time.sleep(wait)
    raise RuntimeError(f"giving up after {MAX_RETRIES} retries: {url.split('?')[0]}")


def new_record(source):
    return {"source": source, "type": "JOUR", "title": "", "authors": [],
            "affiliations": [], "year": "", "journal": "", "doi": "",
            "abstract": "", "keywords": [], "index_terms": [], "url": "",
            "cited_by": "",
            "enriched_openalex": False}


def to_last_first(full_name):
    """'Jane M. Doe' -> 'Doe, Jane M.' (keeps names already in 'Last, First')."""
    name = " ".join(full_name.split())
    if not name or "," in name:
        return name
    parts = name.split(" ")
    return name if len(parts) == 1 else f"{parts[-1]}, {' '.join(parts[:-1])}"


def ris_type(text):
    t = (text or "").lower()
    if "conference" in t or "proceeding" in t:
        return "CPAPER"
    if "chapter" in t or "book" in t:
        return "CHAP"
    return "JOUR"


def unique(seq):
    seen, out = set(), []
    for x in seq:
        key = x.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(x.strip())
    return out


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------
def fetch_ieee(env, limit):
    key = env.get("IEEE_API_KEY")
    if not key:
        raise SourceUnavailable("IEEE_API_KEY missing in .env")
    records, start, page = [], 1, 200
    while len(records) < limit:
        params = {"querytext": QUERIES["ieee"], "start_year": YEAR_FROM,
                  "end_year": YEAR_TO, "max_records": min(page, limit - len(records)),
                  "start_record": start, "apikey": key}
        data = http_json("https://ieeexploreapi.ieee.org/api/v1/search/articles?"
                         + urllib.parse.urlencode(params))
        items = data.get("articles", [])
        if start == 1:
            print(f"    total available: {data.get('total_records')}")
        if not items:
            break
        for a in items:
            if a.get("content_type") not in IEEE_TYPES:
                continue
            r = new_record("IEEE Xplore")
            r["type"] = ris_type(a.get("content_type"))
            r["title"] = a.get("title", "")
            authors = a.get("authors", {}).get("authors", [])
            r["authors"] = [to_last_first(x.get("full_name", "")) for x in authors]
            r["affiliations"] = unique(x.get("affiliation", "") for x in authors)
            r["year"] = str(a.get("publication_year", ""))
            r["journal"] = a.get("publication_title", "")
            r["doi"] = a.get("doi", "")
            r["abstract"] = a.get("abstract", "")
            terms = a.get("index_terms", {})
            # Author keywords stay separate from IEEE's controlled vocabulary,
            # which adds generic terms (e.g. "Accuracy", "Printing", "Timing")
            r["keywords"] = unique(terms.get("author_terms", {}).get("terms", []))
            r["index_terms"] = unique(terms.get("ieee_terms", {}).get("terms", []))
            r["url"] = a.get("html_url", "")
            r["cited_by"] = str(a.get("citing_paper_count", ""))
            records.append(r)
        start += len(items)
        # IEEE keeps returning records past total_records; stop at the total
        if start > int(data.get("total_records") or 0):
            break
        time.sleep(SLEEP_SECONDS)
    return records


def _springer_abstract(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):  # {"h1": "Abstract", "p": [...]}
        p = value.get("p", "")
        return " ".join(p) if isinstance(p, list) else str(p)
    return ""


def fetch_springer(env, limit):
    key = env.get("SPRINGER_META_API_KEY") or env.get("SPRINGER_API_KEY")
    if not key:
        raise SourceUnavailable("SPRINGER_META_API_KEY missing in .env")
    query = (f"{QUERIES['springer']} AND datefrom:{YEAR_FROM}-01-01"
             f" AND dateto:{YEAR_TO}-12-31")
    records, start, page = [], 1, 25  # free plan: max 25 per page
    while len(records) < limit:
        params = {"q": query, "p": page, "s": start, "api_key": key}
        data = http_json("https://api.springernature.com/meta/v2/json?"
                         + urllib.parse.urlencode(params))
        items = data.get("records", [])
        if start == 1:
            result = (data.get("result") or [{}])[0]
            print(f"    total available: {result.get('total', 'unknown')}")
        if not items:
            break
        for a in items[: limit - len(records)]:
            if a.get("contentType") not in SPRINGER_TYPES:
                continue
            r = new_record("SpringerLink")
            r["type"] = ris_type(a.get("contentType"))
            r["title"] = a.get("title", "")
            r["authors"] = [to_last_first(c.get("creator", ""))
                            for c in a.get("creators", [])]
            r["year"] = (a.get("publicationDate") or "")[:4]
            r["journal"] = a.get("publicationName", "")
            r["doi"] = a.get("doi", "")
            r["abstract"] = _springer_abstract(a.get("abstract"))
            r["keywords"] = unique(a.get("keyword", []))
            urls = a.get("url", [])
            r["url"] = urls[0].get("value", "") if urls else ""
            records.append(r)
        start += len(items)
        time.sleep(SLEEP_SECONDS)
    return records


def fetch_scopus(env, limit):
    """ScienceDirect content via Scopus Search, filtered to Elsevier.

    The free key has no ScienceDirect Search entitlement; with an institutional
    token (ELSEVIER_INSTTOKEN) Scopus may also return richer views.
    """
    key = env.get("ELSEVIER_API_KEY")
    if not key:
        raise SourceUnavailable("ELSEVIER_API_KEY missing in .env")
    headers = {"X-ELS-APIKey": key, "Accept": "application/json"}
    if env.get("ELSEVIER_INSTTOKEN"):
        headers["X-ELS-Insttoken"] = env["ELSEVIER_INSTTOKEN"]
    records, start, page = [], 0, 25  # STANDARD view: max 25 per page
    while len(records) < limit:
        params = {"query": QUERIES["scopus"], "count": page, "start": start}
        data = http_json("https://api.elsevier.com/content/search/scopus?"
                         + urllib.parse.urlencode(params), headers)
        res = data.get("search-results", {})
        items = [e for e in res.get("entry", []) if "error" not in e]
        if start == 0:
            print(f"    total available: {res.get('opensearch:totalResults')}")
        if not items:
            break
        for a in items[: limit - len(records)]:
            if a.get("subtypeDescription") not in SCOPUS_SUBTYPES:
                continue
            r = new_record("ScienceDirect (via Scopus)")
            r["type"] = ris_type(a.get("prism:aggregationType"))
            r["title"] = a.get("dc:title", "")
            if a.get("dc:creator"):
                r["authors"] = [a["dc:creator"]]  # only first author in STANDARD
            r["affiliations"] = unique(
                ", ".join(p for p in (x.get("affilname"), x.get("affiliation-city"),
                                      x.get("affiliation-country")) if p)
                for x in a.get("affiliation", []) or [])
            r["year"] = (a.get("prism:coverDate") or "")[:4]
            r["journal"] = a.get("prism:publicationName", "")
            r["doi"] = a.get("prism:doi", "")
            doi = r["doi"]
            r["url"] = f"https://doi.org/{doi}" if doi else ""
            r["cited_by"] = a.get("citedby-count", "")
            records.append(r)
        start += len(items)
        time.sleep(SLEEP_SECONDS)
    return records


SOURCES = {"ieee": fetch_ieee, "springer": fetch_springer, "scopus": fetch_scopus}

# Record "source" label -> per-database RIS file suffix (matches Zotero folders)
SOURCE_FILE_SUFFIX = {"IEEE Xplore": "ieee",
                      "ScienceDirect (via Scopus)": "sciencedirect",
                      "SpringerLink": "springerlink"}


# --------------------------------------------------------------------------
# Deduplication and OpenAlex enrichment
# --------------------------------------------------------------------------
def norm_doi(doi):
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (doi or "").strip().lower())


def norm_title(title):
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())


def deduplicate(records):
    seen, out = set(), []
    for r in records:
        keys = {k for k in (norm_doi(r["doi"]), norm_title(r["title"])) if k}
        if keys & seen:
            continue
        seen |= keys
        out.append(r)
    return out


def _abstract_from_index(inv):
    if not inv:
        return ""
    words = sorted((pos, w) for w, positions in inv.items() for pos in positions)
    return " ".join(w for _, w in words)


# OpenAlex names that bibliometrix does not recognise as countries
COUNTRY_ALIASES = {"US": "USA", "GB": "United Kingdom", "KR": "South Korea",
                   "RU": "Russia", "IR": "Iran", "VN": "Vietnam", "TW": "Taiwan"}


def openalex_country_names(base):
    """ISO-2 code -> country name, from the OpenAlex countries entity."""
    try:
        data = http_json("https://api.openalex.org/countries?"
                         + urllib.parse.urlencode({**base, "per-page": 200}))
    except (SourceUnavailable, RuntimeError) as e:
        print(f"    OpenAlex countries lookup failed ({e}); affiliations without country")
        return {}
    names = {c["id"].rsplit("/", 1)[-1].upper(): c["display_name"]
             for c in data.get("results", [])}
    names.update(COUNTRY_ALIASES)
    return names


def enrich_openalex(records, env):
    """Fill missing authors/affiliations/abstract/keywords from OpenAlex by DOI."""
    by_doi = {norm_doi(r["doi"]): r for r in records
              if r["doi"] and "," not in r["doi"] and "|" not in r["doi"]}
    dois = list(by_doi)
    base = {"per-page": 50}
    if env.get("OPENALEX_API_KEY"):
        base["api_key"] = env["OPENALEX_API_KEY"]
    if env.get("OPENALEX_MAILTO"):
        base["mailto"] = env["OPENALEX_MAILTO"]
    countries = openalex_country_names(base)
    for i in range(0, len(dois), 50):
        chunk = dois[i:i + 50]
        params = {**base, "filter": "doi:" + "|".join(chunk)}
        try:
            data = http_json("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
        except (SourceUnavailable, RuntimeError) as e:
            print(f"    OpenAlex batch {i // 50 + 1} failed: {e}")
            continue
        for w in data.get("results", []):
            r = by_doi.get(norm_doi(w.get("doi")))
            if not r:
                continue
            auths = w.get("authorships", [])
            names = [to_last_first(a.get("author", {}).get("display_name", "")) for a in auths]
            if len(names) > len(r["authors"]):
                r["authors"] = names
            if not r["affiliations"]:
                # "Institution, Country" so bibliometrix can extract countries
                r["affiliations"] = unique(
                    ", ".join(p for p in (inst.get("display_name"),
                                          countries.get(inst.get("country_code") or "")) if p)
                    for a in auths for inst in a.get("institutions", []))
            if not r["abstract"]:
                r["abstract"] = _abstract_from_index(w.get("abstract_inverted_index"))
            # OpenAlex keywords are machine-assigned, not author keywords
            if not r["keywords"] and not r["index_terms"]:
                r["index_terms"] = unique(k.get("display_name", "") for k in w.get("keywords", []))
            if not r["cited_by"]:
                r["cited_by"] = str(w.get("cited_by_count", ""))
            r["enriched_openalex"] = True
        print(f"    OpenAlex: {min(i + 50, len(dois))}/{len(dois)} DOIs")
        time.sleep(SLEEP_SECONDS / 2)


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def write_ris(records, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            lines = [("TY", r["type"]), ("TI", r["title"])]
            lines += [("AU", a) for a in r["authors"] if a]
            lines += [("PY", r["year"]), ("T2", r["journal"]), ("DO", r["doi"]),
                      ("AB", r["abstract"])]
            lines += [("KW", k) for k in r["keywords"]]
            lines += [("AD", a) for a in r["affiliations"]]
            lines += [("UR", r["url"]), ("DB", r["source"])]
            if r["cited_by"]:
                lines.append(("N1", f"Cited by: {r['cited_by']}"))
            for tag, val in lines:
                val = " ".join(str(val).split())
                if val:
                    f.write(f"{tag}  - {val}\n")
            f.write("ER  - \n\n")


SCOPUS_CSV_COLUMNS = ["Authors", "Author full names", "Title", "Year", "Source title",
                      "DOI", "Link", "Abstract", "Author Keywords", "Index Keywords",
                      "Affiliations", "Authors with affiliations", "References",
                      "Document Type", "Cited by", "Source", "EID"]


def write_csv(records, path):
    """CSV in Scopus export layout, readable by bibliometrix:
    convert2df(file, dbsource = "scopus", format = "csv")."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(SCOPUS_CSV_COLUMNS)
        for i, r in enumerate(records, 1):
            authors = "; ".join(a for a in r["authors"] if a)
            affiliations = "; ".join(r["affiliations"])
            w.writerow([authors, authors, r["title"], r["year"], r["journal"],
                        r["doi"], r["url"], " ".join(r["abstract"].split()),
                        "; ".join(r["keywords"]), "; ".join(r["index_terms"]),
                        affiliations, affiliations, "",
                        "Conference Paper" if r["type"] == "CPAPER" else "Article",
                        r["cited_by"] or "0", r["source"], f"rec-{i}"])


def coverage(records):
    n = len(records) or 1
    for field in ("authors", "abstract", "keywords", "doi", "affiliations"):
        have = sum(1 for r in records if r[field])
        print(f"    {field:<13} {have:>4}/{len(records)} ({100 * have // n}%)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sources", default="ieee,springer,scopus",
                    help="comma list of: ieee, springer, scopus")
    ap.add_argument("--max-per-source", type=int, default=0,
                    help="cap per source (0 = no limit, fetch all results)")
    ap.add_argument("--no-enrich", action="store_true", help="skip OpenAlex")
    ap.add_argument("--combined", action="store_true",
                    help="also write one combined RIS and CSV")
    ap.add_argument("--out", default=f"bibliometria_{date.today():%Y%m%d}",
                    help="output file prefix (files are written to data/raw/)")
    args = ap.parse_args()

    env = load_env()
    RAW.mkdir(parents=True, exist_ok=True)
    records, skipped = [], []
    for name in [s.strip() for s in args.sources.split(",") if s.strip()]:
        if name not in SOURCES:
            sys.exit(f"unknown source: {name}")
        limit = args.max_per_source or sys.maxsize
        print(f"\n[{name}] fetching {args.max_per_source or 'all'} records...")
        try:
            got = SOURCES[name](env, limit)
            print(f"    fetched: {len(got)}")
            records += got
        except SourceUnavailable as e:
            print(f"    SKIPPED: {e}")
            skipped.append(name)

    before = len(records)
    records = deduplicate(records)
    print(f"\nDeduplicated: {before} -> {len(records)}")
    if records and not args.no_enrich:
        print("\n[openalex] enriching missing fields...")
        enrich_openalex(records, env)

    # Keep only records with an abstract (from the source or OpenAlex)
    before = len(records)
    records = [r for r in records if r["abstract"].strip()]
    print(f"\nWith abstract: {before} -> {len(records)}")

    if args.combined:
        write_ris(records, RAW / f"{args.out}.ris")
        write_csv(records, RAW / f"{args.out}.csv")
    # Per database: RIS (Zotero collection) + Scopus-format CSV (bibliometrix)
    per_source = []
    for src, suffix in SOURCE_FILE_SUFFIX.items():
        subset = [r for r in records if r["source"] == src]
        if subset:
            stem = RAW / f"{args.out}_{suffix}"
            write_ris(subset, stem.with_suffix(".ris"))
            write_csv(subset, stem.with_suffix(".csv"))
            per_source += [f"{stem.name}.ris", f"{stem.name}.csv"]
    print("\nField coverage:")
    coverage(records)
    for src in sorted({r["source"] for r in records}):
        print(f"    {src}: {sum(r['source'] == src for r in records)}")
    if args.combined:
        print(f"\nWrote {args.out}.ris and {args.out}.csv")
    print(f"Per-database files: {', '.join(per_source) or 'none'}")
    if skipped:
        print(f"Skipped sources: {', '.join(skipped)} (check keys/access and re-run)")


if __name__ == "__main__":
    main()
