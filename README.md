# Student Well-Being and Mental Health Analytics: Systematic Review and Bibliometric Analysis

Data, code and coded records for a systematic review and comparative bibliometric
analysis of student well-being and mental health analytics in IEEE Xplore,
ScienceDirect and SpringerLink (2021–2026).

**Author:** Cristhian Eduardo Osorio Restrepo, Universidad del Quindío, Colombia ·
ORCID [0009-0004-6899-4555](https://orcid.org/0009-0004-6899-4555) ·
cristhiane.osorior@uqvirtual.edu.co

The article is in [`article/`](article), in IEEE two-column format (`IEEEtran`):
`main.tex` (English) and `main_es.tex` (Spanish). A one-column version with the same
content is kept as a backup: `main_onecolumn.tex` and `main_es_onecolumn.tex`.

## What the study does

*Student well-being and mental health analytics* is the application of data analytics,
data mining, machine learning or artificial intelligence to data about students in order
to assess, predict or monitor their mental health or well-being.

1. Metadata of 1072 records with abstracts were retrieved from the APIs of IEEE Xplore,
   ScienceDirect (through Scopus) and SpringerLink on 2026-09-28.
2. Every abstract was screened and coded with a closed codebook. A study is included only
   if the outcome it analyses or predicts is the students' mental health or well-being.
3. The 502 included studies were analysed with bibliometrix, separately for each database.

| Screening decision | IEEE Xplore | ScienceDirect | SpringerLink | Total |
|---|---|---|---|---|
| Included | 426 | 33 | 43 | 502 |
| Excluded after review (doubtful) | 207 | 17 | 6 | 230 |
| Excluded (unrelated to the topic) | 298 | 36 | 2 | 336 |
| Retracted | 2 | 0 | 2 | 4 |

## Repository structure

```
scripts/        pipeline, numbered in execution order
  paths.py        file layout shared by all scripts
  harmonize.py    documented corrections applied after coding
data/
  raw/            API exports (not versioned, see "Data not included")
  thesaurus/      keyword thesaurus (CSV and VOSviewer format)
  screening/      coding of every abstract and the merged, validated extraction tables
  included/       metadata of the 502 included studies, without abstracts
results/
  figures/<db>/<en|es>/   figures (PDF and PNG) and summary.txt with the numbers behind them
  review_stats.txt        every number reported in the systematic review
docs/           methodology, codebook and how to obtain API keys
article/        LaTeX sources of the article: IEEE two-column (main*.tex), one-column
                backup (main*_onecolumn.tex), bibliography and the IEEEtran class files
```

## Pipeline

| Step | Script | Input → output |
|---|---|---|
| 01 | `scripts/01_fetch_metadata.py` | APIs → `data/raw/*.csv`, `*.ris` (needs API keys) |
| 02 | `scripts/02_clean_keywords.py` | raw exports + thesaurus → `data/raw/*_clean.csv` |
| 03 | `scripts/03_build_extraction.py` | coding + metadata → `data/screening/extraction_*.csv`, `harmonization_log.txt` |
| 04 | `scripts/04_select_included.py` | extraction + metadata → `data/included/*_included.csv` |
| 05 | `scripts/05_figures.R` | included studies → `results/figures/` |
| 06 | `scripts/06_review_stats.py` | extraction → `results/review_stats.txt` |
| 07 | `scripts/07_make_corpus_bib.py` | included studies + article → `article/corpus.bib` |

Step 03 stops with an error if any record is missing, any field is missing or any value is
outside the codebook vocabulary.

## How to reproduce

Requirements (versions used): Python 3.13 (standard library only), R 4.5 with
`bibliometrix` 5.5.0, `ggplot2` and `stringr`, and a LaTeX distribution with `latexmk`
for the article.

```bash
# 1. Obtain your own API keys (docs/API_KEYS.md) and put them in .env
cp .env.example .env

# 2. Download the metadata (writes data/raw/bibliometria_<today>_*.csv)
make fetch

# 3. Run the rest of the pipeline and build the article
make all
```

Without API keys, `make published` regenerates the figures, the review statistics, the
bibliography and both PDFs from the data published in this repository (steps 05–07).

`make all` runs steps 02–07 and compiles both IEEE PDFs; `make article-onecolumn` compiles
the one-column backup. It expects the exports of the
2026-09-28 snapshot in `data/raw/` with the names `bibliometria_20260928_<db>.csv`
(see `scripts/paths.py`).

**Important:** a new download returns a different set of records, because the databases
change over time. Record identifiers (`I001`, `D011`, `S005`, …) are row numbers of the
2026-09-28 exports, so the coding in `data/screening/coding/` only matches that snapshot.
To compare a new download with this study, match records by DOI using
`data/screening/extraction_all.csv`. To analyse a new download on its own, change `SNAPSHOT` in
`scripts/paths.py`; the abstracts then have to be screened and coded again.

## Data

### `data/screening/extraction_all.csv`

One row per screened record (1072 rows). Columns: `id`, `database`, `year`, `doc_type`,
`title`, `doi`, and the coded fields `screening`, `screening_reason`, `study_type`,
`population`, `outcome`, `data_source`, `method`, `xai`, `best_result`, `country`,
`quality_note` and `summary_en` (a one- or two-sentence summary written for this study).
Fields can hold several values separated by `;`. The vocabulary and the coding conventions
are defined in [`docs/CODEBOOK.md`](docs/CODEBOOK.md).

### `data/screening/coding/`

The original coding, one JSON file per batch, before harmonization. Abstract screening and
coding were carried out with the assistance of a large language model under the closed
codebook, followed by checks on random samples, targeted checks of doubtful decisions and the
harmonization rules in `scripts/harmonize.py`. Every change those rules make is listed in
`data/screening/harmonization_log.txt`.

### `data/included/`

Metadata of the included studies in the Scopus CSV layout read by bibliometrix: authors,
title, year, source, DOI, keywords, affiliations and citation count. The `EID` column holds
the record id. The `Abstract` column is empty on purpose.

### Data not included

The raw API exports (`data/raw/`) are not published, because they contain the abstracts of
the articles, which are copyrighted by their publishers, and the API terms of service do not
allow redistributing the retrieved content. They can be downloaded again with step 01 and
your own keys. For the same reason, `scripts/06_review_stats.py` skips its last block (counts
of words in the original abstracts) when `data/raw/` is empty.

## Results

The figures used in the article are, for IEEE Xplore, all seven in `results/figures/ieee/`;
for ScienceDirect, production, sources, countries and keywords; and for SpringerLink,
production, countries, keywords and the co-occurrence network. The other figures are
generated for completeness but are not interpreted, because the volume of data does not
support them (see Section 4 of the article).

## License

The code is released under the GNU General Public License v3.0 (see [`LICENSE`](LICENSE)).
