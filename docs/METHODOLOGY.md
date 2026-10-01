# Methodology — Bibliometric Analysis

Topic: student well-being and mental health analytics, 2021–2026.
Data snapshot: 2026-09-28 (`data/raw/bibliometria_20260928_*`, not versioned).

## 1. Data sources and search

Metadata was retrieved through the official APIs of each database by
`scripts/01_fetch_metadata.py`. The same search equation was expressed in each API's
syntax:

```
(student* OR "higher education" OR universit* OR college*)
AND ("well-being" OR wellbeing OR "mental health"
     OR "psychological well-being" OR "emotional well-being")
AND (analytics OR "learning analytics" OR "data analytics"
     OR "predictive analytics" OR "data mining" OR "machine learning"
     OR "big data")
Publication years: 2021–2026
```

| Database | API used | Fields searched |
|---|---|---|
| IEEE Xplore | IEEE Xplore Metadata API | Document Title, Abstract, Index Terms |
| ScienceDirect | Scopus Search API, restricted to `PUBLISHER(elsevier)` | TITLE-ABS-KEY |
| SpringerLink | Springer Nature Meta API v2 | `keyword:` field |

Notes:

- IEEE searches all metadata by default, including author affiliations
  (`universit*` would match any university author), so the search was scoped
  to title, abstract and index terms.
- The ScienceDirect Search API requires an institutional token that was not
  available, so Elsevier-published records were retrieved through Scopus.
- Springer's title search is a paid feature and its free-text search matches
  full text, so the `keyword:` field was used. The keyword field does not
  expand wildcards, so explicit forms were used (student, students,
  "university students", "college students", "higher education").

## 2. Inclusion criteria

- Document types: journal articles, conference papers and early access
  articles.
- Records must have an abstract (from the source or from OpenAlex).
- Duplicates removed by normalized DOI and normalized title.

Corpus after filtering: 1165 deduplicated records → 1072 with abstract.

| Database | Records | Journal articles | Conference papers |
|---|---|---|---|
| IEEE Xplore | 933 | 48 | 885 |
| ScienceDirect | 86 | 79 | 7 |
| SpringerLink | 53 | 24 | 29 |

The analysis is performed **per database**, not on a merged corpus.

## 3. Enrichment with OpenAlex

Fields missing in the source record (authors, affiliations with country,
abstract, citation count, keywords) were filled from OpenAlex by DOI. Values
provided by the source are never overwritten, except that the author list is
replaced when OpenAlex lists more authors (Scopus returns only the first
author in its standard view).

## 4. Keyword fields

Two keyword fields are kept separate, following the Scopus convention:

- **Author Keywords (DE):** keywords chosen by the authors.
- **Index Keywords (ID):** controlled or machine-assigned terms.

| Database | DE source | ID source | Field used for keyword analysis |
|---|---|---|---|
| IEEE Xplore | IEEE `author_terms` (899/933 after cleaning) | IEEE `ieee_terms` controlled vocabulary (928/933) | DE |
| ScienceDirect | none (0/86) | OpenAlex keywords (86/86) | **ID** |
| SpringerLink | Springer `keyword` (53/53) | none | DE |

**ScienceDirect limitation.** The Scopus API with the available access level
does not return author keywords, so the ScienceDirect keyword analysis uses
OpenAlex keywords. These are assigned automatically by OpenAlex's
classification model, not by the authors, and tend to be broad disciplinary
terms (e.g. *computer science*, *psychology*, *medicine*). ScienceDirect
keyword results therefore describe the disciplinary profile of the records
rather than their specific research topics. They are not directly
comparable with the author-keyword results of IEEE Xplore and SpringerLink.

IEEE's controlled vocabulary was separated from author keywords because it
adds generic technical terms unrelated to the topic (e.g. *accuracy*,
*printing*, *timing*).

## 5. Keyword normalization

Keyword variants were unified with a thesaurus (`data/thesaurus/keyword_thesaurus.csv`,
197 variants → 125 canonical terms), applied by `scripts/02_clean_keywords.py`. The raw
files are kept unchanged. The cleaned files (`*_clean.csv`) differ only in
the two keyword columns. The same thesaurus is exported for VOSviewer
(`data/thesaurus/vosviewer_thesaurus_keywords.txt`).

Merged: spelling, plural, hyphenation and punctuation variants, abbreviations
and typos of the same concept (e.g. *SVM*, *support vector machine* →
*support vector machines*; *KNN*, *k-nearest neighbour* →
*k-nearest neighbors*).

Removed: the sample keywords of the IEEE conference template (*component*,
*formatting*, *style*, *styling*, *insert*), which 5 IEEE records kept
unchanged. They formed a spurious theme in the thematic map. Four of these
records had no other author keywords, so IEEE records with author keywords
drop from 903 to 899.

Corrected: the OpenAlex concept *depression (economics)* is a disambiguation
error; all 9 ScienceDirect records tagged with it deal with clinical
depression, so it is mapped to *depression*.

Deliberately **not** merged, because the terms differ in meaning:

- *anxiety* vs *anxiety disorders* (symptom vs clinical condition)
- *student mental health* vs *mental health* (loses the population)
- *machine learning* vs *machine learning algorithms*
- *academic* / *academics*, *logistic* / *logistics*,
  *medicine* / *medicines*, *dropout* / *dropouts*, *internet* / *internet+*

## 6. Limitations

- **No cited references.** The APIs do not provide reference lists, so
  co-citation, bibliographic coupling, historiograph and local-citation
  analyses are not possible.
- **Unbalanced databases.** IEEE Xplore holds 87% of the corpus, mostly
  conference papers.
- **Different search fields.** SpringerLink was searched by keywords only,
  which is narrower than the title/abstract search used in the other
  databases.
- **Lost ScienceDirect records.** Elsevier does not share abstracts with
  OpenAlex, so records without an abstract in Scopus were excluded by the
  abstract criterion.
- **Upstream updates.** Citation counts and some OpenAlex fields change over
  time; all results refer to the 2026-09-28 snapshot.

## 7. Abstract screening and extraction (systematic review)

Every abstract of the 1072 records was screened and coded with the closed
codebook in `docs/CODEBOOK.md` (screening decision, study type,
population, outcome, data source, method, XAI, best result, country, quality
note and an English summary). Coding was assisted by a large language model
(IEEE Xplore in eight parallel batches) and checked with random samples,
targeted checks of suspicious exclusions and documented harmonisation rules
(`scripts/harmonize.py`, `data/screening/harmonization_log.txt`).

| Database | Included | Doubtful | Excluded | Retracted |
|---|---|---|---|---|
| IEEE Xplore | 426 | 207 | 298 | 2 |
| ScienceDirect | 33 | 17 | 36 | 0 |
| SpringerLink | 43 | 6 | 2 | 2 |
| Total | 502 | 230 | 336 | 4 |

Scope: a study is included only if the outcome it analyses or predicts is the
mental health or well-being of students. A scope review moved 15 records from
INCLUDE to DOUBTFUL (well-being only as a predictor, classroom comfort, digital
device use, course feedback, classroom emotions for teaching, data security);
they are listed in `scripts/harmonize.py` (`SCOPE_EXCLUSIONS`).

Doubtful records are excluded from the synthesis and reported in the PRISMA
diagram as excluded after review. IEEE Xplore results arrive in relevance order
(the API call sets no sort), so the tail of the list is largely off-topic; in
ScienceDirect, `TITLE-ABS-KEY` matches universities and "wellbeing"
organisations in affiliation and funding text.

The article figures are produced from the included records only:
`scripts/04_select_included.py` → `data/included/<db>_included.csv` (without
abstracts) → `scripts/05_figures.R` → `results/figures/<db>/<en|es>/`.
