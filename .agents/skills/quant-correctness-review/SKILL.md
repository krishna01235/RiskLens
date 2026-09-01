---
name: quant-correctness-review
description: Use when implementing or reviewing any function in quant/ — 
  covariance, VaR/CVaR, GARCH, Monte Carlo, EVT, HMM, Kupiec backtest.
---
Before considering any quant/ function done:
- Write or locate a test against a known analytical or textbook reference
  value, not just an assertion that the function runs without error.
- State the mathematical formula being implemented in a comment above the
  function, matching docs/implementation.md's notation.
- Check edge cases explicitly: insufficient data, single-asset portfolios,
  numerical instability (e.g. non-positive-definite matrices).
- Never silently fall back to a wrong-but-plausible number — an
  insufficient-data case must surface as an explicit state, not a
  fabricated result.