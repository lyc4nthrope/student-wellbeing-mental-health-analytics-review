# Reproducible pipeline. Run `make all` from the repository root.
# Step 01 (fetch) needs API keys in .env and is not part of `all`: the published
# results use the snapshot of 2026-09-28, and a new download returns different records.

PYTHON ?= python3
RSCRIPT ?= Rscript
FIGURES = ieee:DE springerlink:DE sciencedirect:ID

.PHONY: all published article-onecolumn fetch clean-keywords extraction included figures stats bib article clean

all: clean-keywords extraction included figures stats bib article

# From the published data only (no raw exports needed): figures, statistics, bibliography, PDFs
published: figures stats bib article

fetch:            ## 01: download metadata from the APIs into data/raw/ (needs .env)
	$(PYTHON) scripts/01_fetch_metadata.py

clean-keywords:   ## 02: apply the keyword thesaurus
	$(PYTHON) scripts/02_clean_keywords.py

extraction:       ## 03: merge, harmonize and validate the abstract coding
	$(PYTHON) scripts/03_build_extraction.py

included:         ## 04: metadata of the included studies (without abstracts)
	$(PYTHON) scripts/04_select_included.py

figures:          ## 05: bibliometric figures, English and Spanish labels
	@for spec in $(FIGURES); do \
	  db=$${spec%%:*}; field=$${spec##*:}; \
	  for lang in en es; do \
	    echo "figures: $$db ($$lang)"; \
	    $(RSCRIPT) scripts/05_figures.R $$db $$field fruchterman $$lang > /dev/null || exit 1; \
	  done; \
	done

stats:            ## 06: numbers reported in the systematic review
	$(PYTHON) scripts/06_review_stats.py > results/review_stats.txt
	@echo "wrote results/review_stats.txt"

bib:              ## 07: bibliography of the cited included studies
	$(PYTHON) scripts/07_make_corpus_bib.py

article:          ## build the IEEE two-column PDFs (English and Spanish)
	cd article && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex > /dev/null
	cd article && latexmk -pdf -interaction=nonstopmode -halt-on-error main_es.tex > /dev/null
	@echo "wrote article/main.pdf and article/main_es.pdf"

article-onecolumn: ## build the one-column backup PDFs
	cd article && latexmk -pdf -interaction=nonstopmode -halt-on-error main_onecolumn.tex > /dev/null
	cd article && latexmk -pdf -interaction=nonstopmode -halt-on-error main_es_onecolumn.tex > /dev/null
	@echo "wrote article/main_onecolumn.pdf and article/main_es_onecolumn.pdf"

clean:            ## remove LaTeX build files
	cd article && latexmk -c main.tex main_es.tex main_onecolumn.tex main_es_onecolumn.tex
