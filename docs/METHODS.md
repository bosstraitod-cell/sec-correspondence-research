# Methods and source boundaries

## Scope

This is a public demonstration of implemented data-handling ideas. The authoritative
private thesis controls were version 1.56 when this release was prepared on
2026-11-03. The demonstration creates no production signals, human labels, fitted
models or SEC–market association tests.

## Two date roles

`DateFiled` controls study inclusion and historical issuer membership. Membership
uses `start <= DateFiled < end`, with an open end allowed. The outer
`<SEC-DOCUMENT>` date is the approved date-level market-information measure for the
private-to-public wrappers in the audited population. It is not an exact intraday
release timestamp. The containing Friday defines the information week; the next
Friday defines the subsequent outcome week. Weekend dates roll forward.

The original audit module also recognizes candidate PUBLIC-REL-DATE and PDS fields.
All 11,607 audited population rows selected the outer archive date. The demo
explicitly implements the approved outer-date rule rather than treating its generic
candidate hierarchy as a new thesis decision. An SEC-HEADER date does not replace
the outer SEC-DOCUMENT date.

Official background: [SEC filing review process](https://www.sec.gov/about/divisions-offices/division-corporation-finance/filing-review-process-corp-fin).
The specific field choice, weekly horizon and membership convention are thesis
design decisions, not a claim that SEC guidance prescribes a volatility model.

## Daily-close weekly volatility

For expected trading sessions with an observed predecessor close:

```text
r[d] = log(close[d] / previous_close)
RV_raw = sqrt(sum(r[d] ** 2))
RV_five_day = sqrt(5 / n_sessions) * RV_raw
```

The public demo accepts an explicit session list and fails on missing or unexpected
dates. It does not infer exchange holidays. Exact duplicate observations collapse;
conflicting duplicate prices fail. A zero RV has an undefined logarithm, represented
by JSON null in this demonstration, with no epsilon added. This illustration does
not settle a production model's treatment of zero RV.

Squared log-return aggregation follows the established realized-volatility
literature; the daily-close frequency and five-session scaling are adaptations.
See Andersen, Bollerslev, Diebold and Labys (2003), *Modeling and Forecasting
Realized Volatility*, [Econometrica](https://doi.org/10.1111/1468-0262.00418).
The supplied four-session example is synthetic and is not a historical exchange
calendar claim. Five-day normalization assumes approximate variance additivity;
it can over-correct shortened weeks and does not recover true integrated variance.

## Publication boundary

The historical census spans filing dates 2006–2025. The approved primary empirical
calendar is narrower: information weeks 2007-01-12 through 2025-12-19 and outcome
weeks 2007-01-19 through 2025-12-26. Post-2025 archive releases remain in the census
and are excluded only from the in-window market panel. A final production panel
and empirical hypothesis tests remain pending.

No observation-level historical constituent list or vendor price series is included.
Reproducing the full thesis requires separately authorized inputs and the full
controlled research workflow. The public demonstration is independently runnable.
