# Obtaining the API keys

`scripts/01_fetch_metadata.py` needs free, non-commercial keys for three APIs.
Copy `.env.example` to `.env` at the repository root and fill in your keys.
`.env` is listed in `.gitignore` and must never be committed.

| Variable | Service | Required |
|---|---|---|
| `IEEE_API_KEY` | IEEE Xplore Metadata API | yes |
| `SPRINGER_META_API_KEY` | Springer Nature Meta API v2 | yes |
| `ELSEVIER_API_KEY` | Elsevier Scopus Search API | yes |
| `ELSEVIER_INSTTOKEN` | Elsevier institutional token (richer Scopus views) | no |
| `OPENALEX_API_KEY`, `OPENALEX_MAILTO` | OpenAlex (polite pool) | no |

## IEEE Xplore

1. Register at <https://developer.ieee.org> and confirm your e-mail.
2. Under **My Account**, register an application to request a key (academic, non-commercial use).
3. The key can stay pending for a few hours until IEEE activates it.

Metadata do not require an institutional subscription. The free plan limits records per call
and calls per day; the script pauses between calls and retries on HTTP 429.

## Springer Nature

1. Register at <https://dev.springernature.com> and confirm your e-mail.
2. In <https://datasolutions.springernature.com/account/api-management/>, create or copy a
   **Meta API** key. The default key may belong to the Open Access API, which the Meta API
   rejects with `401 API key is invalid`.
3. Use the domain `api.springernature.com` (`api.springer.com` is deprecated).

The free plan returns at most 25 results per page; free-text and title searches are not
usable on that plan, which is why the script searches the `keyword:` field.

## Elsevier (ScienceDirect via Scopus)

1. At <https://dev.elsevier.com>, choose **I want an API Key** → **Create API Key** (an Elsevier
   account is needed).
2. Fill in a label and a website URL, and accept the **API Service Agreement**. It allows
   non-commercial use and forbids bulk redistribution of the retrieved content.

Without an institutional token the ScienceDirect Search API is not available, so the script
uses the Scopus Search API restricted to `PUBLISHER(elsevier)`.

## Good practice

- Keep keys in `.env` or environment variables, never in source code or output files.
- Respect the rate limits; all three services answer `429 Too Many Requests` when exceeded.
