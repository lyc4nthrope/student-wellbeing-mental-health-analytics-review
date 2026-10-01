"""Recompute every number reported in Section 3 (systematic review) of the article.

Reads data/screening/extraction_all.csv (INCLUDE records only). Multi-valued fields
count a study once per value, so shares can exceed 100%. The last block counts
words in the original abstracts, so it needs the API exports in data/raw/ and is
skipped when they are not available.

Usage: python3 scripts/06_review_stats.py
"""
import collections
import csv
import re
import sys

from paths import DATABASES, SCREENING, clean_csv, record_id

with open(SCREENING / "extraction_all.csv", encoding="utf-8", newline="") as _f:
    rows = [r for r in csv.DictReader(_f) if r["screening"] == "INCLUDE"]
N = len(rows)


def vals(r, k):
    return set(r[k].split(";"))


def share(n, d=N):
    return f"{n} ({100 * n / d:.0f}%)"


print(f"Included studies: {N}\n")
print("Table 1 - overview")
for k in ["study_type", "population", "outcome", "data_source", "method", "xai", "quality_note"]:
    c = collections.Counter(v for r in rows for v in vals(r, k))
    ranked = sorted(c.items(), key=lambda item: (-item[1], item[0]))  # ties in alphabetical order
    print(f"  {k}: " + "; ".join(f"{v} {share(n)}" for v, n in ranked))

THEMES = {
    "Depression/anxiety/stress prediction": lambda r: vals(r, "outcome") & {"depression", "anxiety", "stress"}
    and vals(r, "study_type") & {"predictive_model", "factor_analysis"},
    "Suicide risk": lambda r: "suicide" in vals(r, "outcome"),
    "Early warning systems and platforms": lambda r: "system_framework" in vals(r, "study_type"),
    "Sensor-based and multimodal sensing": lambda r: vals(r, "data_source") & {"sensors_physiological", "smartphone_digital", "multimodal"},
    "Language, text and emotion": lambda r: "nlp_sentiment" in vals(r, "method") or "emotions" in vals(r, "outcome")
    or "social_media_text" in vals(r, "data_source"),
    "Positive well-being": lambda r: "wellbeing" in vals(r, "outcome"),
    "Addiction": lambda r: "addiction" in vals(r, "outcome"),
    "Reviews": lambda r: "review" in vals(r, "study_type"),
}
print("\nThematic categories")
hit = collections.Counter()
for name, f in THEMES.items():
    g = [r for r in rows if f(r)]
    hit.update(r["id"] for r in g)
    print(f"  {name}: {share(len(g))}, vague {sum(r['quality_note'] == 'vague' for r in g)}, "
          f"XAI {sum(r['xai'] == 'yes' for r in g)}")
print(f"  In no category: {sum(1 for r in rows if hit[r['id']] == 0)}")

print("\nTable 2 - outcome x method")
METHODS = ["classic_ml", "ensemble_boosting", "deep_learning", "nlp_sentiment", "association_clustering", "statistical"]
for o in ["stress", "general_mh_risk", "depression", "anxiety", "emotions", "wellbeing", "addiction", "suicide"]:
    g = [r for r in rows if o in vals(r, "outcome")]
    print(f"  {o}: n={len(g)} " + " ".join(f"{m}={sum(m in vals(r, 'method') for r in g)}" for m in METHODS))

print("\nTable 3 - shares per year")
for y in sorted({r["year"] for r in rows}):
    g = [r for r in rows if r["year"] == y]
    pct = lambda cond: f"{100 * sum(map(cond, g)) / len(g):.0f}%"
    print(f"  {y} n={len(g)} XAI {pct(lambda r: r['xai'] == 'yes')} DL {pct(lambda r: 'deep_learning' in vals(r, 'method'))} "
          f"sensing {pct(lambda r: bool(vals(r, 'data_source') & {'sensors_physiological', 'smartphone_digital', 'multimodal'}))} "
          f"NLP {pct(lambda r: 'nlp_sentiment' in vals(r, 'method'))} wellbeing {pct(lambda r: 'wellbeing' in vals(r, 'outcome'))}")

print("\nQuality signals")
for db in ["IEEE Xplore", "ScienceDirect", "SpringerLink"]:
    g = [r for r in rows if r["database"] == db]
    print(f"  {db}: vague {share(sum(r['quality_note'] == 'vague' for r in g), len(g))}, "
          f"XAI {share(sum(r['xai'] == 'yes' for r in g), len(g))}")
reported = [r for r in rows if r["best_result"]]
high = [r["id"] for r in reported
        if any(float(m) >= 98 for m in re.findall(r"(\d{2,3}(?:\.\d+)?)\s?%", r["best_result"]))]
print(f"  Report a performance value: {len(reported)}; value >= 98%: {len(high)}")
ext = [r["id"] for r in rows if re.search(r"external|independent (cohort|sample|dataset)|cross-dataset|transportab",
                                          r["summary_en"] + r["best_result"], re.I)]
print(f"  Mention external validation: {ext}")
countries = collections.Counter(c for r in rows for c in r["country"].split(";") if c)
print(f"  Countries stated: {sorted(countries.items(), key=lambda item: (-item[1], item[0]))[:3]}")

# Signals counted on the original abstracts (not on the coded summaries)
if not all(clean_csv(db).exists() for db in DATABASES):
    print("\nSkipped the abstract-based counts: data/raw/ exports not found (see README).")
    sys.exit(0)  # expected when working from the published data, not an error
abstracts = {}
for db in DATABASES:
    with open(clean_csv(db), encoding="utf-8", newline="") as _f:
        for i, r in enumerate(csv.DictReader(_f), 1):
            abstracts[record_id(db, i)] = r["Title"] + " " + r["Abstract"]
inc = {r["id"] for r in rows}
SIGNALS = {"fairness/bias": r"fairness|algorithmic bias|demographic parity|equalized odds|equitable",
           "calibration": r"calibrat", "reporting guideline (TRIPOD, STARD, CONSORT)": r"TRIPOD|STARD|CONSORT",
           "privacy/confidentiality": r"privacy|confidential|anonymi"}
print("\nSignals in the original abstracts of included studies")
for name, pat in SIGNALS.items():
    hits = [k for k in inc if re.search(pat, abstracts[k], re.I)]
    print(f"  {name}: {share(len(hits))}")
theme1 = [r["id"] for r in rows if THEMES["Depression/anxiety/stress prediction"](r)]
print(f"\nDepression/anxiety/stress category (n={len(theme1)}): variables named in abstracts")
for name, pat in {"academic pressure/workload/performance": r"academic (pressure|stress|workload|performance)|workload|cgpa|gpa",
                  "social support/family": r"social support|family|parent", "sleep": r"sleep", "finances": r"financ",
                  "validated instrument": r"PHQ|GAD-?7|PSS|DASS|BDI|CES-D|HADS|GHQ|K10|Kessler|SCL-90|Beck"}.items():
    n = sum(bool(re.search(pat, abstracts[k], re.I if name != "validated instrument" else 0)) for k in theme1)
    print(f"  {name}: {share(n, len(theme1))}")
