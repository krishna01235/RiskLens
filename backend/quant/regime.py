"""
quant/regime.py — HMM market regime detection (F12).

Fits a 2-state Gaussian HMM on an equal-weighted benchmark return series to
produce a filtered (forward) probability that the market is currently in a
"stressed" (high-variance) state vs. a "calm" (low-variance) state.

Key implementation decisions:
  - 2 states: fits the "calm vs. stressed" dichotomy with the fewest parameters.
  - covariance_type="full": each state gets its own full covariance matrix so
    the variance difference that identifies the stressed state is directly
    readable from model.covars_.
  - Post-fit relabeling: after fitting, state 1 is always reassigned to be the
    higher-variance state. This prevents the label-flip edge case where
    hmmlearn's random initialisation sometimes assigns the stressed state to
    index 0, breaking downstream convention.
  - Forward (filtered) probability: we compute P(q_t | O_1..O_t) using the
    forward algorithm, NOT the smoothed Viterbi path P(q_t | O_1..O_T).
    The forward pass respects the real-time constraint — it uses only data
    available at timestep t, making it appropriate for live alerting.
"""
import numpy as np
from hmmlearn import hmm
from scipy.special import logsumexp

def fit_hmm(returns: np.ndarray) -> hmm.GaussianHMM:
    """
    Fit a 2-state Gaussian HMM to a 1D returns array.
    Relabels the states so that state 1 is always the higher-variance ("stressed") state.
    """
    if returns.ndim == 1:
        returns = returns.reshape(-1, 1)

    # Initialize and fit the HMM
    model = hmm.GaussianHMM(
        n_components=2, 
        covariance_type="full", 
        n_iter=100, 
        random_state=42
    )
    model.fit(returns)

    # Identify the state with higher variance
    # covariances_ shape: (2, 1, 1) for 1D features
    var_0 = model.covars_[0, 0, 0]
    var_1 = model.covars_[1, 0, 0]

    if var_0 > var_1:
        # State 0 has higher variance, so we need to swap state 0 and 1
        # to ensure state 1 is the "stressed" state.
        
        # Swap means
        model.means_ = model.means_[[1, 0]]
        
        # Swap covariances
        model.covars_ = model.covars_[[1, 0]]
        
        # Swap start probabilities
        model.startprob_ = model.startprob_[[1, 0]]
        
        # Swap transition matrix rows and columns
        # transmat_ is (2, 2)
        transmat = model.transmat_
        transmat = transmat[[1, 0], :] # Swap rows
        transmat = transmat[:, [1, 0]] # Swap cols
        model.transmat_ = transmat

    return model

def forward_probability(model: hmm.GaussianHMM, latest_observations: np.ndarray) -> float:
    """
    Compute the filtered (forward) probability of the "stressed" state (state 1)
    at the most recent timestep, using only past and present observations.
    
    This is explicitly the forward probability P(q_t=1 | O_1..O_t), 
    not the smoothed posterior P(q_t=1 | O_1..O_T).
    """
    if latest_observations.ndim == 1:
        latest_observations = latest_observations.reshape(-1, 1)
        
    framelogprob = model._compute_log_likelihood(latest_observations)
    n_samples, n_components = framelogprob.shape
    
    log_alpha = np.zeros((n_samples, n_components))
    log_startprob = np.log(np.maximum(model.startprob_, 1e-15))
    log_transmat = np.log(np.maximum(model.transmat_, 1e-15))
    
    log_alpha[0] = log_startprob + framelogprob[0]
    for t in range(1, n_samples):
        for j in range(n_components):
            log_alpha[t, j] = logsumexp(log_alpha[t-1] + log_transmat[:, j]) + framelogprob[t, j]
            
    # The last row of log_alpha is log(alpha_T(i))
    last_log_alpha = log_alpha[-1]
    
    # Normalize in log space to get log(P(q_T=i | O_1..O_T))
    log_filtered = last_log_alpha - logsumexp(last_log_alpha)
    
    # Exponentiate to get actual probabilities
    filtered_probs = np.exp(log_filtered)
    
    # Return probability of state 1 (stressed state)
    return float(filtered_probs[1])
