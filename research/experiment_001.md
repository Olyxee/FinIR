# Experiment 001 — Does multimodal business evidence identify material events earlier?

> **Status: reference experiment on synthetic data.** All inputs and labels are
> synthetic and clearly marked as such in `benchmarks/cases/`. The numbers below
> demonstrate the *mechanism* and *measurement methodology*; they are **not**
> evidence of real-world efficacy on real company data. See *Limitations*.

## Hypothesis

Adding text and document evidence to structured financial data lets EIF identify
financially **material** economic events **earlier** (higher Economic Signal Lead
Time, ESLT) and **at least as accurately** (detection F1) as using structured
financial data alone.

## Setup

- **Framework**: EIF 0.1.0, deterministic default provider (no external models).
- **Data**: the eight canonical synthetic benchmark cases in `benchmarks/cases/`
  (supplier price increase, customer contraction, project delay/overrun,
  inventory accumulation, contract obligation, capacity issue, conflicting
  evidence, benign non-material). Each case bundles multimodal evidence plus gold
  labels, a realized outcome, and — where applicable — the date a conventional
  structured indicator would have surfaced the same event.
- **Two conditions**, identical framework, identical configuration:
  - **Baseline** — structured/tabular evidence only (`.csv`, `.xlsx`, `.json`).
  - **EIF** — the full multimodal evidence set (adds emails, notes, transcripts,
    contracts, operations notes).
- **Metrics**: detection precision/recall/F1 over *material* events; impact error
  vs the realized outcome (MAE/MAPE); ESLT (days EIF precedes structured
  detection). Detection scores only material predictions, so non-material events
  (e.g. the benign case) are never counted as false alarms.

Reproduce with:

```bash
python research/reproduce_experiment_001.py
```

## Results

Latest deterministic run (`research/results_001.json`):

| Metric                         | Baseline (structured-only) | EIF (multimodal) |
|--------------------------------|----------------------------|------------------|
| Detection precision            | 1.00                       | 1.00             |
| Detection recall               | 0.14                       | 1.00             |
| Detection F1                   | 0.25                       | 1.00             |
| Impact MAE vs realized (ZAR)   | n/a (nothing detected)     | 83,000           |
| Impact MAPE vs realized        | n/a                        | 0.04 (4%)        |
| Interval coverage (vs label)   | n/a                        | 1.00             |
| ESLT mean (days)               | 43.0 (n=1)                 | 70.2 (n=6)       |
| ESLT median (days)             | 43.0                       | 57.0             |

### Interpretation

- **Detection.** The structured-only baseline detected 1 of 7 material events —
  the inventory accumulation case, which is visible in a numeric time series. It
  missed the supplier price increase, customer contraction, project delay,
  contract obligation, capacity issue, and the conflicting-evidence price change,
  because each of those signals lived in *text* (an email, a call, a note, a
  contract) before it reached any structured system. EIF detected all seven.
- **Precision.** Both conditions had precision 1.00: neither produced a material
  false positive, and the benign non-material case correctly raised no alarm.
- **Impact accuracy.** Against the *realized* outcomes, EIF's deterministic
  estimates were off by R83k on average (MAPE ~4%). This is the honest accuracy
  figure. (Impact-vs-label MAE is 0 by construction — the gold labels are defined
  as the intended deterministic estimate, so that metric measures *reproducibility*
  of the calculation, not predictive accuracy, and is reported separately.)
- **ESLT.** For the six cases with a traditional-detection date, EIF's detection
  (dated to when the evidence became available) preceded conventional structured
  detection by ~70 days on average. The baseline's single ESLT data point (43
  days) exists only because it happened to detect the one structured-visible case.

## Limitations (read this)

1. **Synthetic data.** These cases were authored to be realistic but are not real.
   Real evidence is noisier, more ambiguous, and adversarial. Do not read these
   numbers as real-world performance.
2. **Small n.** Eight cases (six with ESLT). Confidence intervals are wide; the
   reported ESLT 95% CI spans roughly 38–102 days.
3. **Deterministic extractor.** The default extractor uses transparent rules
   tuned to common phrasings. On real text its recall would be lower and would
   depend heavily on the extractor/model used. The framework is designed to let
   you swap in stronger extractors — that is the point — but this experiment does
   not measure them.
4. **Baseline is deliberately simple.** "Structured-only" means the same EIF
   pipeline restricted to tabular evidence, not a sophisticated forecasting
   baseline. A stronger statistical baseline could detect some events the naive
   one misses. The comparison isolates the *value of the extra modalities*, not a
   claim of superiority over all structured methods.
5. **ESLT depends on assumed traditional-detection dates.** Those dates are part
   of the synthetic labels. On real data they must be measured, not assumed.
6. **No claim of causal generalization.** This experiment shows that *when* an
   economically meaningful signal appears first in text, EIF can surface it before
   it reaches structured systems. It does not establish how often that happens in
   any particular company.

## Conclusion

On this synthetic suite, EIF supports the hypothesis: multimodal evidence
increased material-event recall from 0.14 to 1.00 with no loss of precision, and
detected events a median of ~57 days before the modeled conventional indicator.
These results demonstrate the mechanism and the measurement methodology. They are
a starting point for evaluation on real, labeled data — not a finished efficacy
claim. Contributions of real (appropriately anonymized) benchmark cases are
welcome.
