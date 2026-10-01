# Codebook — Systematic review extraction (abstract level)

One row per abstract. Every field uses the closed vocabulary below. Values
separated by `;` when more than one applies.

| Field | Values |
|---|---|
| id | S### (SpringerLink), D### (ScienceDirect), I### (IEEE): 1-based row number in `data/raw/bibliometria_20260928_<db>_clean.csv`; use the DOI to match records across downloads |
| screening | INCLUDE · DOUBTFUL · EXCLUDE · RETRACTED |
| screening_reason | Short English phrase, only when not INCLUDE |
| study_type | predictive_model · factor_analysis · system_framework · review · descriptive · other |
| population | university · secondary_school · vocational · mixed_unspecified · not_students |
| outcome | depression · anxiety · stress · suicide · general_mh_risk · wellbeing · emotions · addiction · other |
| data_source | survey · public_dataset · large_scale_survey · institutional_records · social_media_text · sensors_physiological · smartphone_digital · multimodal · not_reported |
| method | classic_ml · ensemble_boosting · deep_learning · reinforcement_learning · nlp_sentiment · association_clustering · statistical · not_reported |
| xai | yes (SHAP, LIME, permutation importance, attention maps) · no |
| best_result | Best model and metric as reported in the abstract; empty if none |
| country | Country of the sample if stated in the abstract; empty otherwise |
| quality_note | clear · vague (method/data/result missing or incoherent) |
| summary_en | 1–2 sentences in English: objective, data, method, main result |

Screening criterion (INCLUDE): the study applies data analytics, data mining,
machine learning or AI to the mental health or well-being of students (any
education level). Only what the abstract states is coded; nothing is inferred.

## Coding conventions (applied across all coders)

- Population: if the abstract never mentions students → EXCLUDE. If students are the
  motivation but the data come from another group (general social media users, public
  datasets not described as students) or the sample mixes students and non-students →
  DOUBTFUL.
- Outcome: if mental health or well-being is only a predictor and the outcome is academic
  performance, dropout, engagement or sleep → DOUBTFUL.
- Studies without any data analysis (essays, platform descriptions, strategy proposals) → EXCLUDE.
- Loneliness → emotions. Resilience and self-esteem → wellbeing. Nomophobia and
  internet/phone/game addiction → addiction.
- MLP, ANN and extreme learning machines → deep_learning. Random forest and bagged trees →
  ensemble_boosting.
- Facial images, video and speech → sensors_physiological (no separate category).
- Country only when the abstract names the country; not inferred from cities or institutions.
- Per-record corrections made after coding are listed in `scripts/harmonize.py` and logged in
  `data/screening/harmonization_log.txt`.
