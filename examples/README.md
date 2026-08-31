# Examples

Runnable, offline, no LLM required.

- **[company_model/](company_model/run.py)** — build an operating + working-capital
  model, run what-if scenarios, and see what FinIR recomputes vs. reuses, plus a
  100k-scenario vectorized batch.  `python examples/company_model/run.py`
- **[agent_financial_reasoning/](agent_financial_reasoning/run.py)** — an AI agent
  flow: natural-language → structured intent (via a mock compiler) → FinIR mutation →
  incremental execution.  `python examples/agent_financial_reasoning/run.py`

There is also a plain `.finir` model at `company_model/model.finir` you can run with
the CLI:

```bash
finir run examples/company_model/model.finir \
  --set revenue=500000000 --set cogs=300000000 --set opex=120000000 \
  --set receivable_days=30 --set payable_days=45 --set inventory=50000000
```
