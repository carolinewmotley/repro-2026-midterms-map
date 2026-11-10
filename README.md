# Abortion Access After the 2026 Elections

A state-by-state tracker of where abortion law stands in every state, what the November 3, 2026 elections changed, and what is moving now.

**[View the live tracker](https://carolinewmotley.github.io/repro-2026-midterms-map/)**

## What it shows

- **The law today.** Each state is shaded by its current abortion law, from total bans to no gestational limit.
- **What the 2026 elections changed.** Governor and U.S. Senate results for every state with a race, plus the four abortion ballot measures in Missouri, Nevada, Virginia, and Idaho.
- **What is moving now.** A news feed for every state, refreshed each morning.

Select any state on the map or in the table to see all three together.

## How it stays current

A GitHub Action (`.github/workflows/update-news.yml`) runs once a day. It calls the free [GDELT](https://www.gdeltproject.org/) news API through `scripts/update_news.py` and saves the latest headlines to `data/news.json`, which the page reads when it loads. No API key is needed. The feed can also be refreshed by hand from the Actions tab with **Run workflow**.

Law status and election results are reviewed by hand and dated on the page.

## Sources

- Abortion law: Guttmacher Institute, State Bans on Abortion Throughout Pregnancy (as of September 17, 2026)
- Ballot measures: Ballotpedia News and AP calls
- Governor results: MultiState
- Senate results: US Polling Data, Newsweek, and state news outlets for races still being counted
- News feed: GDELT Project

## Built with

Plain HTML, CSS, and JavaScript, with [Plotly.js](https://plotly.com/javascript/) for the map. The page is a single file with no build step.

---

Built by [Caroline Motley](https://github.com/carolinewmotley) as a personal project. This tracker summarizes public reporting and is not legal advice. Corrections are welcome through [issues](https://github.com/carolinewmotley/repro-2026-midterms-map/issues).
