# Bibliometric figures of the included studies, per database (bibliometrix).
#
# Usage (from the repository root):
#   Rscript scripts/05_figures.R <db> <keyword_field> [network_layout] [lang]
#     db              ieee | sciencedirect | springerlink
#     keyword_field   DE (author keywords) | ID (index keywords; OpenAlex concepts for ScienceDirect)
#     network_layout  igraph layout for the co-occurrence network (default: fruchterman)
#     lang            en (default) | es; translates axis labels and legends, keywords stay in English
#
# Input:  data/included/<db>_included.csv
# Output: results/figures/<db>/<lang>/  PDF (vector, for LaTeX) and PNG figures, plus
#         summary.txt with the numbers behind every figure.

suppressPackageStartupMessages({
  library(bibliometrix)
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
if (!length(args) %in% 2:4) stop("usage: Rscript scripts/05_figures.R <db> <DE|ID> [layout] [en|es]")
if (!file.exists("scripts/paths.py")) stop("run this script from the repository root")
db <- args[1]
field <- args[2]
layout <- if (length(args) >= 3) args[3] else "fruchterman"
lang <- if (length(args) == 4) args[4] else "en"
L <- if (lang == "es") list(full = "Año completo", partial = "Año parcial", year = "Año de publicación",
  docs = "Documentos", scp = "Un solo país (SCP)", mcp = "Varios países (MCP)",
  centr = "Grado de relevancia\n(Centralidad)", dens = "Grado de desarrollo\n(Densidad)",
  term = "Término", tyear = "Año", tfreq = "Frecuencia del término") else
  list(full = "Full year", partial = "Partial year", year = "Publication year", docs = "Documents",
  scp = "Single country (SCP)", mcp = "Multiple countries (MCP)",
  centr = "Relevance degree\n(Centrality)", dens = "Development degree\n(Density)",
  term = "Term", tyear = "Year", tfreq = "Term frequency")
# Records were retrieved on 2026-09-28, so 2026 is a partial year whatever the current date.
SNAPSHOT_YEAR <- 2026L
in_csv <- file.path("data", "included", sprintf("%s_included.csv", db))
out_dir <- file.path("results", "figures", db, lang)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

M <- suppressWarnings(suppressMessages(
  convert2df(in_csv, dbsource = "scopus", format = "csv")))
M <- metaTagExtraction(M, "AU_CO")

# Print-friendly palette (light surface)
BLUE <- "#2a78d6"; BLUE_LIGHT <- "#9ec5f4"; ORANGE <- "#eb6834"
INK <- "#0b0b0b"; INK_2 <- "#52514e"; GRID <- "#e1e0d9"

theme_fig <- theme_minimal(base_size = 11) +
  theme(text = element_text(colour = INK_2),
        axis.text = element_text(colour = INK_2),
        axis.title = element_text(colour = INK_2),
        panel.grid.major = element_line(colour = GRID, linewidth = 0.3),
        panel.grid.minor = element_blank(),
        legend.position = "top", legend.title = element_blank(),
        plot.background = element_rect(fill = "white", colour = NA))

save_fig <- function(plot, name, width = 7, height = 4.5) {
  base <- file.path(out_dir, sub("\\.png$", "", name))
  ggsave(paste0(base, ".pdf"), plot, width = width, height = height, device = cairo_pdf, bg = "white")
  ggsave(paste0(base, ".png"), plot, width = width, height = height, dpi = 200, bg = "white")
}

summary_lines <- c(sprintf("Database: %s | documents: %d | keyword field: %s", db, nrow(M), field))
note <- function(...) summary_lines <<- c(summary_lines, sprintf(...))

split_terms <- function(x) {
  terms <- trimws(unlist(strsplit(x[!is.na(x) & x != ""], ";")))
  terms[terms != ""]
}

# 1. Annual scientific production ------------------------------------------
years <- as.data.frame(table(PY = M$PY), stringsAsFactors = FALSE)
years$PY <- as.integer(years$PY)
years$status <- ifelse(years$PY == SNAPSHOT_YEAR, L$partial, L$full)
p <- ggplot(years, aes(factor(PY), Freq, fill = status)) +
  geom_col(width = 0.7) +
  geom_text(aes(label = Freq), vjust = -0.4, colour = INK, size = 3.5) +
  scale_fill_manual(values = setNames(c(BLUE, BLUE_LIGHT), c(L$full, L$partial))) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
  labs(x = L$year, y = L$docs) + theme_fig
save_fig(p, "01_annual_production.png")
note("Annual production: %s", paste(years$PY, years$Freq, sep = "=", collapse = ", "))

# 2. Most relevant sources --------------------------------------------------
src <- head(sort(table(M$SO), decreasing = TRUE), 10)
src <- data.frame(source = names(src), n = as.integer(src))
# convert2df upper-cases source titles; restore the original spelling
raw <- read.csv(in_csv, check.names = FALSE, encoding = "UTF-8")
original <- tapply(raw[["Source title"]], toupper(trimws(raw[["Source title"]])), `[`, 1)
src$label <- stringr::str_wrap(ifelse(is.na(original[src$source]), src$source, original[src$source]), 60)
p <- ggplot(src, aes(reorder(label, n), n)) +
  geom_col(fill = BLUE, width = 0.7) +
  geom_text(aes(label = n), hjust = -0.3, colour = INK, size = 3.3) +
  coord_flip() + scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
  labs(x = NULL, y = L$docs) + theme_fig +
  theme(axis.text.y = element_text(size = 8))
save_fig(p, "02_sources.png", height = 5)
note("Distinct sources: %d | top 10 sources hold %d documents",
     length(unique(M$SO)), sum(src$n))
note("Top sources: %s", paste(src$source, src$n, sep = " = ", collapse = " | "))

# 3. Countries (all authors, full counting), single vs multiple country ----
COUNTRY_NAMES <- c(USA = "United States", "UNITED KINGDOM" = "United Kingdom",
                   KOREA = "South Korea", "HONG KONG" = "Hong Kong", "SRI LANKA" = "Sri Lanka",
                   "SAUDI ARABIA" = "Saudi Arabia", "UNITED ARAB EMIRATES" = "United Arab Emirates")
country_label <- function(x) {
  ifelse(x %in% names(COUNTRY_NAMES), COUNTRY_NAMES[x], tools::toTitleCase(tolower(x)))
}
doc_countries <- lapply(strsplit(ifelse(is.na(M$AU_CO), "", M$AU_CO), ";"),
                        function(x) unique(trimws(x[trimws(x) != ""])))
with_country <- sum(lengths(doc_countries) > 0)
co <- do.call(rbind, lapply(doc_countries[lengths(doc_countries) > 0], function(cs)
  data.frame(country = cs, type = if (length(cs) == 1) L$scp else L$mcp)))
top_co <- names(head(sort(table(co$country), decreasing = TRUE), 10))
co_top <- as.data.frame(table(co[co$country %in% top_co, ]), stringsAsFactors = FALSE)
co_top$country <- factor(country_label(co_top$country), levels = rev(country_label(top_co)))
co_top$type <- factor(co_top$type, levels = c(L$mcp, L$scp))
p <- ggplot(co_top, aes(country, Freq, fill = type)) +
  geom_col(width = 0.7, colour = "white", linewidth = 0.4) +
  coord_flip() + scale_y_continuous(expand = expansion(mult = c(0, 0.05))) +
  scale_fill_manual(values = setNames(c(BLUE, ORANGE), c(L$scp, L$mcp)),
                    breaks = c(L$scp, L$mcp)) +
  labs(x = NULL, y = L$docs) + theme_fig
save_fig(p, "03_countries.png")
totals <- aggregate(Freq ~ country, co_top, sum)
totals <- totals[order(-totals$Freq), ]
mcp <- aggregate(Freq ~ country, co_top[co_top$type == L$mcp, ], sum)
note("Documents with country: %d/%d | multi-country documents: %d",
     with_country, nrow(M), sum(lengths(doc_countries) > 1))
note("Top countries (docs, MCP): %s", paste(sprintf("%s=%d (MCP %d)", totals$country, totals$Freq,
     mcp$Freq[match(totals$country, mcp$country)]), collapse = ", "))

# 4. Most frequent keywords -------------------------------------------------
kw <- head(sort(table(split_terms(M[[field]])), decreasing = TRUE), 15)
kw <- data.frame(term = tolower(names(kw)), n = as.integer(kw))
p <- ggplot(kw, aes(reorder(term, n), n)) +
  geom_col(fill = BLUE, width = 0.7) +
  geom_text(aes(label = n), hjust = -0.3, colour = INK, size = 3.3) +
  coord_flip() + scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
  labs(x = NULL, y = L$docs) + theme_fig
save_fig(p, "04_keywords.png", height = 5)
note("Documents with keywords: %d/%d | distinct keywords: %d",
     sum(!is.na(M[[field]]) & M[[field]] != ""), nrow(M), length(unique(split_terms(M[[field]]))))
note("Top keywords: %s", paste(kw$term, kw$n, sep = "=", collapse = ", "))

# 5. Keyword co-occurrence network (bibliometrix networkPlot) ---------------
network <- if (field == "DE") "author_keywords" else "keywords"
net_matrix <- biblioNetwork(M, analysis = "co-occurrences", network = network, sep = ";")
draw_network <- function() {
  # Side margins keep long labels inside the image
  par(mar = c(1, 4, 1, 4), xpd = NA)
  set.seed(42)
  networkPlot(net_matrix, n = 40, Title = "", type = layout, size = TRUE,
              size.cex = TRUE, remove.multiple = FALSE, remove.isolates = TRUE,
              labelsize = 0.95, label.cex = FALSE, cluster = "louvain",
              edgesize = 3, edges.min = 2, verbose = TRUE)
}
cairo_pdf(file.path(out_dir, "05_cooccurrence_network.pdf"), width = 14, height = 11)
net <- draw_network()
dev.off()
png(file.path(out_dir, "05_cooccurrence_network.png"), width = 2100, height = 1650, res = 150)
invisible(draw_network())
dev.off()
clusters <- net$cluster_res
for (cl in sort(unique(clusters$cluster))) {
  terms <- clusters[clusters$cluster == cl, ]
  terms <- terms[order(-terms$btw_centrality), ]
  note("Network cluster %s: %s", cl, paste(tolower(terms$vertex), collapse = ", "))
}

# 6. Thematic map (bibliometrix thematicMap) --------------------------------
set.seed(42)
tm <- thematicMap(M, field = field, n = 250, minfreq = 5, stemming = FALSE,
                  size = 0.5, n.labels = 3, repel = TRUE)
tm_plot <- tm$map + labs(x = L$centr, y = L$dens)
if (lang == "es") {
  quadrants_es <- c("Emerging or\nDeclining Themes" = "Temas emergentes\no en declive",
                    "Niche Themes" = "Temas nicho", "Basic Themes" = "Temas básicos",
                    "Motor Themes" = "Temas motores")
  for (i in seq_along(tm_plot$layers)) {
    lab <- tm_plot$layers[[i]]$aes_params$label
    if (!is.null(lab)) {
      key <- trimws(lab)
      tm_plot$layers[[i]]$aes_params$label <- ifelse(key %in% names(quadrants_es), quadrants_es[key], lab)
    }
  }
}
# Draw the quadrant names underneath the cluster labels so the labels stay readable
is_quadrant <- vapply(tm_plot$layers, function(l) inherits(l$geom, "GeomText") && !is.null(l$aes_params$label), logical(1))
tm_plot$layers <- c(tm_plot$layers[is_quadrant], tm_plot$layers[!is_quadrant])
save_fig(tm_plot, "06_thematic_map.png", width = 8, height = 6.5)
tm_clusters <- tm$clusters
for (i in seq_len(nrow(tm_clusters))) {
  note("Theme '%s': centrality=%.3f density=%.2f freq=%d",
       tolower(tm_clusters$name[i]), tm_clusters$rcentrality[i],
       tm_clusters$rdensity[i], as.integer(tm_clusters$freq[i]))
}

# 7. Trend topics (bibliometrix fieldByYear) --------------------------------
trend <- fieldByYear(M, field = field, timespan = c(2021, 2026), min.freq = 5,
                     n.items = 3, graph = FALSE)
save_fig(trend$graph + labs(title = NULL, x = L$term, y = L$tyear) +
           guides(size = guide_legend(title = L$tfreq)),
         "07_trend_topics.png", width = 7, height = 6)
td <- trend$df
note("Trend topics (median year): %s",
     paste(sprintf("%s=%s", tolower(td$item), td$year_med), collapse = ", "))

writeLines(summary_lines, file.path(out_dir, "summary.txt"))
cat(summary_lines, sep = "\n")
