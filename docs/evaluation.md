# Evaluation methodology

VibeFinance records evaluation metrics with every completed analysis session.
The metric values and all three agent latencies are persisted with the validated
result.

## Metrics

### 30-session momentum accuracy

For every historical point with 30 preceding and 30 following trading sessions,
the system classifies both trailing momentum and the subsequent return as
positive (at least +5%), negative (at most -5%), or neutral. Accuracy is the
share of equal classifications. Only completed forward windows are included, so
future data never affects the current signal. Overlapping windows are disclosed
and mean this is a transparent diagnostic rather than a claim of future returns.

### Portfolio concentration

Holdings are valued using recorded quantity multiplied by average cost. Position
and sector exposure are divided by total portfolio cost basis. The displayed
concentration score is the greater of the selected company's position exposure
and its sector exposure. Both are compared with the selected profile's stored
limits.

### Performance and evidence

- Each agent records elapsed milliseconds using a monotonic clock.
- End-to-end latency covers graph execution through metrics collection.
- Evidence count reports the cited observations used by the specialists.
- Conflict count reports material directional disagreement between agents.
- Filing retrieval records cosine similarity and preserves the referenced chunk.

## Demonstration procedure

1. Sync an official SEC filing and wait for indexing to complete.
2. Open **Evaluation**, select one company and two different investor profiles,
   then run the comparison. The dashboard launches both persisted analysis jobs
   together and verifies whether their returned market evidence matches.
3. Compare recommendation, confidence, portfolio fit, concentration, evidence,
   conflicts, and latency side by side. The proof banner only confirms controlled
   personalization when market evidence matches and a portfolio-aware outcome changes.
4. Demonstrate a missing filing or unavailable provider. The affected agent is
   marked degraded, its warning is visible, and the workflow completes with
   bounded confidence.

## Limitations

Yahoo Finance is a convenient public market-data adapter rather than an exchange
feed. The current backtest covers the available six-month price window and does
not include fees, slippage, survivorship adjustments, or non-overlapping folds.
Portfolio values use cost basis rather than live mark-to-market values. SEC
filings cover US issuers; Indian issuers require equivalent NSE, BSE, or SEBI
adapters. These limitations are shown as product scope, not hidden as model
certainty.
