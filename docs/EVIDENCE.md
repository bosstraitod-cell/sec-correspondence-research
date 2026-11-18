# Evidence for the public portfolio

The initial package was locally checked on **2026-11-03**; the quality-audit
addition was checked on **2026-11-18**. These are release checks of the public
code and claims, not certification of the entire thesis.

## What was rechecked

- All 11,607 local SEC archives were rehashed against the saved timing ledger:
  zero SHA-256 mismatches.
- Public-date to Friday-week mappings and recorded filing-to-archive intervals
  were recomputed for all 11,607 rows: zero mismatches.
- All filing keys were unique. Recomputed aggregates matched the README:
  11,585 later archive dates; 11,545 changed Friday weeks; median interval 60 days.
- The selected original timing module and original tests are byte-identical to
  their private-repository sources.
- At initial release, the private repository's 39 tests and the public package's
  18 tests passed separately. These counts overlap because five original timing
  tests are included in both suites; they must not be added as independent tests.
- On 2026-11-18, the public package's **23 tests passed**. Five new tests cover
  the exact finite-population probability, minimal 284-case calculation,
  reproducible synthetic draw, duplicate rejection, and explicit synthetic label.
  Running `quality_audit_demo.py` independently returned `N=3,849`, `M=39`,
  `n=284`, `P0=0.049550284409080284`, and a unique 284-ID synthetic draw.

Machine-readable aggregates and source hashes are in
[`evidence_summary.json`](evidence_summary.json). The full corpus is private, so
these aggregate statistics cannot be independently regenerated from the synthetic
public fixture. The offline demonstration itself is fully reproducible.

## Boundaries and known issues

The public-release date measure has day-level precision. It does not establish
when investors first learned the content or whether the release contains new news.
The archived SEC header and outer-document dates can disagree. The outer date is
retained by the controlled design; the synthetic example deliberately shows that
distinction. Long filing-to-archive intervals require careful interpretation.

Saved historical live SEC comparisons were not rerun as part of this publication
check. No market relationship was inspected for this release. No NLP validity,
statistical significance, forecasting performance, or regime result is established.
Remaining text-extraction production checks and model/validation decisions remain
outstanding in the thesis.

The new [quality-audit note](QUALITY_AUDIT.md) reports only the approved
closing-letter sampling rule and the frozen-draw status as of 2026-11-18.
Its 1% ceiling is project-chosen; its arithmetic is independently checked
against the [NIST hypergeometric formula](https://www.itl.nist.gov/div898/software/dataplot/refman2/ch8/hyppdf.pdf).
The public synthetic draw does **not** expose or reproduce the real selected
accessions, original seed, source files, or reviewer judgments. At this check,
the independent original-source gate had **0/284 completed judgments**.

## Public package review

The new package excludes the private repository's Git history and its tracked
vendor workbook, market outputs, proposals, private control logs, and paper PDFs.
A text-pattern scan checks for local home-directory paths, common secret formats
and private keys; this is supplemented by reviewing the explicit file inventory.
No open-source reuse license has been selected. No publication approval is implied
by this local verification.

## What is original and what is adapted

`scripts/audit_sec_information_timing.py` and its five tests are original research
artifacts copied without edits. `research_demo.py` and its thirteen tests were
prepared for this public release: they reuse the original parser/calendar functions
and implement small, independently checked demonstrations of the approved membership
and RV rules. They do not replace the larger production workflow. Synthetic data
were created specifically for the demonstration.

`quality_audit_demo.py` is a public adaptation of the private finite-population
planner and seed-recorded sampler. It demonstrates the arithmetic and algorithm
on synthetic identifiers only. Its five tests do not constitute source review
or a passed SEC-text quality gate.
