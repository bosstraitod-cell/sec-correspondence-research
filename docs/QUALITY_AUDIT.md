# Checking the text before measuring it

The thesis cannot treat a machine-extracted zero as proof that an SEC letter has no
new numbered staff comment. A parser can miss a number, mix company and SEC text,
or stop a comment too early. Those are data-quality problems, not market results.

The current working ledger has **33,974 candidate numbered comments**. That is a
reproducible development count, **not a verified final count**. Source checks and
corrections are still in progress. The 11,607 matched `UPLOAD` records are the
metadata census; they are not 11,607 validated substantive letters.

## The independent closing-letter check

The project selected a **1% letter-level quality ceiling** for one specific
stratum: automatically classified ordinary closing letters that were not used
in development. This is a project choice, not a rate estimated from the data or
prescribed by an SEC paper. One letter is defective for this check if its
original SEC staff source contains at least one **new numbered comment** that
the candidate extraction missed.

After excluding 100 development closings, the untouched frame has 3,849 letters.
Let `M = ceil(0.01 × N)` be the number of defective letters at the chosen
ceiling. With `N = 3,849`, `M = 39`. For a simple random sample of `n` letters
without replacement, the chance of finding zero defects if at least `M` letters
are defective is:

```text
P(zero defects | N, M, n) = choose(N - M, n) / choose(N, n)
```

The smallest `n` that makes this probability at most 5% is **284**:
`P(zero | n=283) = 0.0500981895`, while
`P(zero | n=284) = 0.0495502844`. The exact finite-population formula follows
the [NIST Dataplot hypergeometric probability function, Eq. 8-243](https://www.itl.nist.gov/div898/software/dataplot/refman2/ch8/hyppdf.pdf).
[Samohyl (2018)](https://doi.org/10.1007/s40092-017-0231-9) discusses
finite-population acceptance sampling, but its displayed Appendix Eq. (5)
appears to have a typesetting error, so the calculation does not copy that
equation. Neither source sets the project's 1% ceiling.

The real 284-letter sample has been frozen with a recorded seed and remains
private. Original-source review is required before this check can clear text
for production use. Any missed numbered comment or unreadable/unresolved
original stops this gate for correction and escalation; the case cannot be
replaced to produce a nominal pass. Even a valid zero-defect result would not
prove that the population contains no mistakes or clear the rest of the corpus.

Run `python3 quality_audit_demo.py` to reproduce the sample-size arithmetic and
a deterministic draw from **synthetic IDs**. The example includes no actual SEC
source, real draw order, original seed, licensed data, or reviewer judgment.

Other checks remain separate: nonclosing and critical zero candidates,
positive-letter text boundaries and authorship, OCR quality, original offsets,
and final filing/comment/week reconciliation. No production SEC text measure,
SEC–volatility result, or forecasting claim is established by this audit plan.
