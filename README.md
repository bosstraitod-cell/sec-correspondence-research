# SEC comment letters and S&P 500 volatility

I'm Traitod, an M.Sc. Finance student at Chiang Mai University. My thesis asks
whether negative language in publicly released SEC correspondence is associated
with S&P 500 volatility in the following week.

Before testing that question, I needed to work out which companies belonged in
the sample and when each document became public. This repository shares that part
of the work: a timing-audit script from the thesis, a small example you can run,
and tests for the main date and data-quality rules.

The full study is still in progress. I haven't yet estimated the relationship
between the SEC language measure and market volatility.

## Run the example

You need Python 3.11 or later. There are no packages to install, and the example
works offline.

```bash
git clone https://github.com/bosstraitod-cell/sec-correspondence-research.git
cd sec-correspondence-research
python3 research_demo.py
python3 -m unittest discover -s tests -v
```

On Windows, use `python` if `python3` is unavailable.
Running `research_demo.py` creates `demo_output/demo.json` and
`demo_output/timing.csv`. All company records and prices in this example are made up.

| Step | Example |
|---|---|
| Company is in the index | 1 January 2023 until 1 February 2024, excluding the end date |
| Correspondence is filed privately | 8 January 2024 |
| Correspondence appears in the public archive | 14 March 2024 |
| Information week ends | 15 March 2024 |
| Following volatility week ends | 22 March 2024 |

Under my study design, the company qualifies because it was a constituent when the
correspondence was filed. The public archive date determines when the text enters
the weekly information measure. These dates answer different questions, so the
code keeps both. Weekend releases move to the following Friday.

The example also calculates weekly volatility from daily closing prices. It shows
both the raw value and an approximate adjustment for a four-session week.

## What I've completed so far

The larger research workflow reconstructs historical S&P 500 membership, matches
companies using SEC issuer identifiers, and collects correspondence filed during
2006–2025. The timing audit gives the following counts:

| Check | Result |
|---|---:|
| Matched UPLOAD correspondence records | 11,607 |
| Duplicate filing keys | 0 |
| Public archive date later than private filing date | 11,585 |
| Friday-week assignment changes when using the archive date | 11,545 |
| Median time from filing to the archive date | 60 calendar days |

UPLOAD records include several document types, so the total should not be read as
11,607 substantive SEC staff letters. The 60-day interval starts at filing;
it is not a measure of how long the SEC waits after completing a review.
The [evidence notes](docs/EVIDENCE.md) explain how these counts were checked and what
they can tell us.

## Where to start in the code

- [research_demo.py](research_demo.py) is the easiest starting point. It runs the
  example using the original date parser and adds small membership and volatility
  calculations.
- [scripts/audit_sec_information_timing.py](scripts/audit_sec_information_timing.py)
  is the original timing-audit script, copied unchanged from the thesis project.
  Running its full audit requires the private manifests and downloaded archives.
- [tests/test_research_demo.py](tests/test_research_demo.py) checks membership
  boundaries, weekends, year changes, missing sessions, conflicting prices, and
  volatility calculations against known answers.
- [tests/test_sec_information_timing.py](tests/test_sec_information_timing.py)
  contains the original parser tests.

GitHub Actions is configured to run the public tests on Python 3.11, 3.12 and 3.13.

## What's still in progress

The data collection and timing work are complete. Text extraction still has
production checks to finish, and the weekly market series has been constructed
for development checks but has not been frozen as the final research input.

For the language measure, I've designed a framework using an SEC-specific lexicon
and contextual NLP/LLM classification. Human-reference coding and model validation
are still ahead. The statistical plan includes mutual information and hidden
Markov models with time-varying transition probabilities; those empirical analyses
have not been run.

I'm testing an association. This project does not yet demonstrate prediction,
causality, or trading performance.

## Data and method notes

The correspondence comes from SEC EDGAR. The thesis also uses LSEG/Refinitiv
membership and market-price data, which aren't distributed here. The public
repository includes synthetic inputs and aggregate audit counts so that anyone
can run the example without a subscription.

The [method notes](docs/METHODS.md) cover the date rules, volatility formula and
sources. The weekly volatility measure uses daily closes. The five-day adjustment
is approximate, so the research retains the raw measure for comparison.

## About the work

This is part of my independent study at Chiang Mai University. I developed the
research question and methodology and used AI assistance for coding, documentation
and testing. The runnable example was prepared to share the work publicly; it is
smaller than the private thesis workflow.

Contact: **bosstraitod@gmail.com** · [Code reuse terms](RIGHTS.md)
