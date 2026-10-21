# AI Brain — validation handoff

Status: **research/shadow module implemented; broker validation pending**.

The AI Brain consumes time-stamped completed-trade examples, trains only on outcomes already known before the validation window, and evaluates a chronological holdout. It filters potential multi-market signals through existing health, news, entry and quality checks. It cannot place trades or grant live risk.

Run the complete regression suite via GitHub Actions. To validate a **private** local dataset without broker access:

```bash
PYTHONPATH=src python scripts/ai/validate_brain.py \
  --input /private/path/completed-trade-outcomes.jsonl \
  --features technical,macro \
  --output build/ai/validation.json
```

Each JSONL line must contain `sample_id`, `observed_ns`, `label_known_ns`, a fixed-order numeric `features` array, and `profitable_after_costs` (0/1). Both timestamps use epoch nanoseconds. The label must reflect **realized net profit after spread/commission/slippage**, and must not have been known at feature-observation time. The example feature names above are placeholders: replace them with the actual logged feature schema.

The generated JSON report is offline, **research-only**, and explicitly marks data provenance as unverified. GitHub synthetic fixtures only check implementation correctness; they are not profitability evidence. Never commit private trading datasets, broker identifiers, or model/research report files containing sensitive account information.

Remaining gates: validate data provenance; market-feature ingestion from the KAT1/MT5 validated feed; real-tick multi-symbol backtests; repeated walk-forward evidence; unbiased stability testing; terminal/broker/demo reconciliation; then explicit strategy/risk policy approvals. No automated real-money trading.
