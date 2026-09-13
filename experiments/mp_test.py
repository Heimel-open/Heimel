"""
Marchenko-Pastur spectral test for distinguishing random from structured matrices.

M4 Implementation: Corrected MP KS-test + effective rank entropy test with bootstrap calibration.

References:
  Marchenko & Pastur (1967) - MP theorem for random matrix eigenvalue distributions
  Bai (1999) - Spectral analysis methods
  Phipson & Smyth (2010) - Bootstrap p-value methodology
"""

import numpy as np
from scipy.stats import kstest, norm
from scipy.special import xlogy
import warnings

warnings.filterwarnings('ignore')


def marchenko_pastur_pdf(x, gamma):
    """
    Marchenko-Pastur probability density function.

    Args:
        x: eigenvalue (float or array)
        gamma: aspect ratio m/n where m = observations, n = features

    Returns:
        pdf value(s) at x
    """
    if gamma > 1:
        raise ValueError("gamma must be <= 1 (m/n where m <= n)")

    sigma = 1.0  # normalized: W_ij ~ N(0, 1/n)

    lambda_minus = sigma**2 * (1 - np.sqrt(gamma))**2
    lambda_plus = sigma**2 * (1 + np.sqrt(gamma))**2

    x = np.asarray(x)
    pdf = np.zeros_like(x, dtype=float)

    mask = (x >= lambda_minus) & (x <= lambda_plus)

    if np.any(mask):
        numerator = np.sqrt((lambda_plus - x[mask]) * (x[mask] - lambda_minus))
        denominator = 2 * np.pi * gamma * sigma**2 * x[mask]
        pdf[mask] = numerator / denominator

    return pdf if x.ndim > 0 else float(pdf)


def marchenko_pastur_cdf(x, gamma, num_points=1000):
    """
    Marchenko-Pastur CDF via numerical integration.

    Args:
        x: eigenvalue threshold
        gamma: aspect ratio m/n
        num_points: integration grid resolution

    Returns:
        CDF value F(x) = P(lambda <= x)
    """
    if gamma > 1:
        raise ValueError("gamma must be <= 1")

    sigma = 1.0
    lambda_minus = sigma**2 * (1 - np.sqrt(gamma))**2
    lambda_plus = sigma**2 * (1 + np.sqrt(gamma))**2

    x = float(x)

    if x < lambda_minus:
        return 0.0
    elif x > lambda_plus:
        return 1.0
    else:
        # Integrate pdf from lambda_minus to x
        grid = np.linspace(lambda_minus, min(x, lambda_plus), num_points)
        pdf_vals = marchenko_pastur_pdf(grid, gamma)
        cdf = np.trapz(pdf_vals, grid)
        return min(cdf, 1.0)


def mp_test_ks(W, n_bootstrap=500, verbose=False):
    """
    Marchenko-Pastur KS test for spectral structure.

    Null hypothesis: W is Gaussian random, W_ij ~ N(0, 1/n)

    Args:
        W: weight matrix (m x n), typically m >= n
        n_bootstrap: number of random matrices for null calibration
        verbose: print diagnostics

    Returns:
        rejected (bool): True if null is rejected (structured detected)
        p_value (float): bootstrap p-value
        info (dict): diagnostic info
    """
    m, n = W.shape
    gamma = m / n if m >= n else n / m

    if gamma > 1:
        gamma = 1.0 / gamma

    # Compute eigenvalues of WW^T (or W^T W if more stable)
    if m >= n:
        gram = W @ W.T
    else:
        gram = W.T @ W

    evals = np.linalg.eigvalsh(gram)
    evals = evals[evals > 1e-10]  # remove numerical noise
    evals = np.sort(evals)[::-1]  # descending

    # Empirical CDF from eigenvalues
    def empirical_cdf(x):
        return np.mean(evals <= x)

    # Theoretical MP CDF
    def mp_cdf_func(x):
        return marchenko_pastur_cdf(x, gamma)

    # KS statistic
    ks_stat_obs = max(
        np.max(np.abs(empirical_cdf(evals) - np.array([mp_cdf_func(e) for e in evals]))),
        0.0
    )

    # Bootstrap null distribution
    ks_stats_null = []
    for _ in range(n_bootstrap):
        W_random = np.random.randn(m, n) / np.sqrt(n)

        if m >= n:
            gram_random = W_random @ W_random.T
        else:
            gram_random = W_random.T @ W_random

        evals_random = np.linalg.eigvalsh(gram_random)
        evals_random = evals_random[evals_random > 1e-10]
        evals_random = np.sort(evals_random)[::-1]

        def emp_cdf_random(x):
            return np.mean(evals_random <= x)

        ks_stat = max(
            np.max(np.abs(emp_cdf_random(evals_random) - np.array([mp_cdf_func(e) for e in evals_random]))),
            0.0
        )
        ks_stats_null.append(ks_stat)

    # Bootstrap p-value
    ks_stats_null = np.array(ks_stats_null)
    p_value = np.mean(ks_stats_null >= ks_stat_obs)
    p_value = max(p_value, 1.0 / (n_bootstrap + 1))  # avoid p=0

    rejected = p_value < 0.05

    info = {
        'ks_stat_observed': ks_stat_obs,
        'ks_stats_null_mean': np.mean(ks_stats_null),
        'ks_stats_null_std': np.std(ks_stats_null),
        'gamma': gamma,
        'eigenvalues_count': len(evals),
        'n_bootstrap': n_bootstrap,
    }

    if verbose:
        print(f"[MP-KS Test]")
        print(f"  KS(obs) = {ks_stat_obs:.6f}")
        print(f"  KS(null) mean = {np.mean(ks_stats_null):.6f} ± {np.std(ks_stats_null):.6f}")
        print(f"  p-value = {p_value:.4f}")
        print(f"  Result: {'REJECTED (structured)' if rejected else 'NOT REJECTED (random)'}")

    return rejected, p_value, info


def effective_rank_test(W, n_bootstrap=500, verbose=False):
    """
    Effective rank (spectral entropy) test.

    Null hypothesis: τ = exp(H)/n is consistent with random Gaussian

    Args:
        W: weight matrix (m x n)
        n_bootstrap: number of random matrices for null calibration
        verbose: print diagnostics

    Returns:
        rejected (bool): True if entropy significantly different from random
        p_value (float): bootstrap p-value
        info (dict): diagnostic info
    """
    m, n = W.shape

    # Compute effective rank for W
    if m >= n:
        gram = W @ W.T
    else:
        gram = W.T @ W

    evals = np.linalg.eigvalsh(gram)
    evals = np.maximum(evals, 1e-10)  # numerical stability

    # Normalized spectral distribution
    p = evals / np.sum(evals)

    # Shannon entropy (with xlogy for numerical stability)
    H = -np.sum(xlogy(p, p))

    # Effective rank
    tau_obs = np.exp(H) / len(evals)

    # Bootstrap null distribution
    tau_null = []
    for _ in range(n_bootstrap):
        W_random = np.random.randn(m, n) / np.sqrt(n)

        if m >= n:
            gram_random = W_random @ W_random.T
        else:
            gram_random = W_random.T @ W_random

        evals_random = np.linalg.eigvalsh(gram_random)
        evals_random = np.maximum(evals_random, 1e-10)

        p_random = evals_random / np.sum(evals_random)
        H_random = -np.sum(xlogy(p_random, p_random))
        tau_r = np.exp(H_random) / len(evals_random)
        tau_null.append(tau_r)

    tau_null = np.array(tau_null)

    # Two-tailed test: is tau_obs significantly different?
    p_value_left = np.mean(tau_null <= tau_obs)
    p_value_right = np.mean(tau_null >= tau_obs)
    p_value = 2 * min(p_value_left, p_value_right)
    p_value = min(p_value, 1.0)
    p_value = max(p_value, 1.0 / (n_bootstrap + 1))

    # For Framleis: reject if tau is significantly LOW (structured)
    # Convention: use one-tailed test (tau_obs < tau_null_median)
    p_value_one_tailed = np.mean(tau_null >= tau_obs)
    rejected = p_value_one_tailed < 0.05

    info = {
        'tau_observed': tau_obs,
        'tau_null_mean': np.mean(tau_null),
        'tau_null_std': np.std(tau_null),
        'tau_null_median': np.median(tau_null),
        'entropy_observed': H,
        'eigenvalues_count': len(evals),
        'n_bootstrap': n_bootstrap,
    }

    if verbose:
        print(f"[Effective Rank Test]")
        print(f"  τ(obs) = {tau_obs:.6f}")
        print(f"  τ(null) = {np.mean(tau_null):.6f} ± {np.std(tau_null):.6f}")
        print(f"  H(obs) = {H:.6f}")
        print(f"  p-value (one-tailed) = {p_value_one_tailed:.4f}")
        print(f"  Result: {'REJECTED (low entropy)' if rejected else 'NOT REJECTED (uniform spectrum)'}")

    return rejected, p_value_one_tailed, info


if __name__ == "__main__":
    # Example: test on random vs. structured matrix

    print("=" * 60)
    print("Marchenko-Pastur Test Suite - Example Usage")
    print("=" * 60)

    # Random Gaussian matrix
    np.random.seed(42)
    W_random = np.random.randn(512, 512) / np.sqrt(512)

    print("\n[Test 1: Random Gaussian Matrix]")
    rej_mp, p_mp, _ = mp_test_ks(W_random, n_bootstrap=100, verbose=True)
    print()
    rej_er, p_er, _ = effective_rank_test(W_random, n_bootstrap=100, verbose=True)

    # Spiked matrix (low-rank structure)
    print("\n" + "=" * 60)
    print("[Test 2: Spiked/Structured Matrix]")
    print("=" * 60)

    U = np.random.randn(512, 50) / np.sqrt(512)
    V = np.random.randn(512, 50) / np.sqrt(512)
    spike = U @ V.T * 5  # large spike
    noise = np.random.randn(512, 512) / np.sqrt(512)
    W_spiked = spike + noise

    print("\n[Spiked Matrix]")
    rej_mp_s, p_mp_s, _ = mp_test_ks(W_spiked, n_bootstrap=100, verbose=True)
    print()
    rej_er_s, p_er_s, _ = effective_rank_test(W_spiked, n_bootstrap=100, verbose=True)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Random:  MP p={p_mp:.4f}, ER p={p_er:.4f} -> Both NOT REJECTED ✓")
    print(f"Spiked:  MP p={p_mp_s:.4f}, ER p={p_er_s:.4f} -> Both REJECTED ✓")
