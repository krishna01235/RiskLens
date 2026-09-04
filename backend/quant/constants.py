"""Constants used across the quant engine."""

# Minimum observations required to fit a GARCH(1,1) model stably.
MIN_GARCH_OBSERVATIONS = 20

# Minimum exceedances required to fit a Generalized Pareto Distribution stably.
MIN_EVT_EXCEEDANCES = 20

# Percentage to reduce the largest risk contributor by when generating decision candidates.
REDUCE_POSITION_PCT = 0.20

# Percentage of portfolio to shift to cash when generating the "increase cash" candidate.
INCREASE_CASH_PCT = 0.10

# Risk aversion parameter lambda used for ranking candidates (expected_return - lambda * CVaR).
DECISION_LAMBDA = 0.5

# Minimum margin by which the top risk contributor must exceed the second-highest to be considered dominant.
REDUCE_POSITION_MARGIN = 0.05

# Timeout in seconds for Monte Carlo simulation of a single decision candidate.
CANDIDATE_MC_TIMEOUT = 2.0
