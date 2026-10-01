"""Post-coding harmonization of the abstract coding.

Every correction made after the abstracts were coded is declared here, so the
audit trail is explicit. scripts/03_build_extraction.py applies these rules to
each record and logs every change in data/screening/harmonization_log.txt.
"""

# Per-record corrections: record id -> {field: new value}
OVERRIDES = {
    # Country inferred from a city or institution name; the codebook requires an explicitly stated country.
    **{rid: {"country": ""} for rid in ["I237", "I246", "I262", "I268", "I276", "I285", "I293", "I333"]},
    # Loneliness is coded as emotions (as in D028).
    "I328": {"outcome": "emotions"},
    "I595": {"outcome": "emotions"},
    # Resilience is coded as wellbeing (as in D021).
    "I629": {"outcome": "wellbeing"},
}

# Scope review (2026-09-30). The topic is student well-being and mental health analytics:
# a study is in scope only if the outcome it analyses or predicts is the students' well-being
# or mental health. These records were coded INCLUDE and are moved to DOUBTFUL.
SCOPE_EXCLUSIONS = {
    "S032": "Out of scope: data storage security, no analysis of well-being or mental health",
    "S036": "Out of scope: well-being is a predictor; the outcome is reading literacy",
    "D018": "Out of scope: supervisor-student relationship typology; well-being only as an implication",
    "D034": "Out of scope: outcome is perceived indoor environmental comfort",
    "D079": "Out of scope: pubertal timing and social adaptability, not well-being or mental health",
    "I149": "Out of scope: opinions about mental health services, not students' mental health",
    "I296": "Out of scope: digital well-being as device-use management",
    "I608": "Out of scope: engagement in remote learning; emotions as engagement signals",
    "I645": "Out of scope: digital well-being as smartphone usage anomalies",
    "I662": "Out of scope: sentiment of course feedback",
    "I672": "Out of scope: digital well-being, digital hoarding and information security awareness",
    "I673": "Out of scope: academic emotions to adapt instruction",
    "I711": "Out of scope: classroom emotion detection for teaching",
    "I728": "Out of scope: emotional development of pre-primary children, no data",
    "I803": "Out of scope: parent-child relationship quality index",
}
for _rid, _reason in SCOPE_EXCLUSIONS.items():
    OVERRIDES.setdefault(_rid, {}).update({"screening": "DOUBTFUL", "screening_reason": _reason})


def apply_rules(rid, codes):
    """Apply the generic rule and the per-record corrections to one record (in place).

    Returns a description of every change, for the harmonization log.
    """
    changes = []
    # Rule R1: an included study whose population also contains non-students is a mixed population.
    if codes["screening"] == "INCLUDE" and "not_students" in codes["population"].split(";"):
        codes["screening"] = "DOUBTFUL"
        codes["screening_reason"] = "Mixed population: students and non-students"
        changes.append("R1 INCLUDE->DOUBTFUL (mixed population)")
    for field, value in OVERRIDES.get(rid, {}).items():
        if codes.get(field) != value:
            changes.append(f"{field}: {codes.get(field)!r} -> {value!r}")
            codes[field] = value
    return changes
