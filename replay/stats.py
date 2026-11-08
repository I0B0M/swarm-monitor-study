"""Small-sample statistics for proportions, standard library only (the repo has no package manifest).

Every function is exact or a published closed form. tests/test_replay_stats.py checks the values below,
which were cross-checked on 2026-11-07 against independent implementations: statsmodels 0.15.0
(confint_proportions_2indep, method "newcomb"; proportion_confint, method "beta") and scipy 1.18.1
(fisher_exact). Methods:
- Clopper-Pearson exact interval (Clopper and Pearson 1934); rule of three for 0/n as a cross-check.
- Wilson score interval (Wilson 1927).
- Newcombe hybrid score interval for a difference of two independent proportions (Newcombe 1998, method 10).
- Fisher exact test for a 2x2 table, two-sided by summing tables no more likely than the observed one.
- Exact power of the two-sided Fisher test by enumeration.
- Jeffreys interval (Beta(k + 1/2, n - k + 1/2) quantiles) via the regularised incomplete beta function.
- Cluster bootstrap: resample whole clusters (layouts), never single games.
- TOST-style equivalence check on a difference: the 90% Newcombe interval inside plus or minus a margin.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Iterable, Sequence

Z975 = 1.959963984540054
Z95 = 1.6448536269514722


# ---------- binomial helpers ----------

def _log_binom_pmf(k: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
            + k * math.log(p) + (n - k) * math.log1p(-p))


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return min(1.0, sum(math.exp(_log_binom_pmf(i, n, p)) for i in range(0, k + 1)))


def _bisect(f: Callable[[float], float], lo: float, hi: float, tol: float = 1e-12, it: int = 200) -> float:
    flo = f(lo)
    for _ in range(it):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided (1 - alpha) interval for a binomial proportion."""
    if n <= 0:
        raise ValueError("n must be positive")
    lower = 0.0 if k == 0 else _bisect(lambda p: (1 - binom_cdf(k - 1, n, p)) - alpha / 2, 0.0, 1.0)
    upper = 1.0 if k == n else _bisect(lambda p: binom_cdf(k, n, p) - alpha / 2, 0.0, 1.0)
    return lower, upper


def rule_of_three(n: int) -> float:
    """Approximate 95% upper bound for 0 events in n trials."""
    return 3.0 / n


def wilson(k: int, n: int, z: float = Z975) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("n must be positive")
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)


def newcombe_diff(k1: int, n1: int, k2: int, n2: int, z: float = Z975) -> tuple[float, float, float]:
    """Difference p1 - p2 and its Newcombe (1998) method-10 interval."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    lower = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    upper = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, lower, upper


def tost_equivalent(k1: int, n1: int, k2: int, n2: int, margin: float) -> tuple[bool, tuple[float, float, float]]:
    """Equivalence at alpha 0.05 (TOST): the 90% Newcombe interval lies inside (-margin, +margin)."""
    d, lo, hi = newcombe_diff(k1, n1, k2, n2, z=Z95)
    return (lo > -margin and hi < margin), (d, lo, hi)


# ---------- Fisher exact ----------

def _hyper_logp(a: int, r1: int, c1: int, n: int) -> float:
    return (math.lgamma(r1 + 1) - math.lgamma(a + 1) - math.lgamma(r1 - a + 1)
            + math.lgamma(n - r1 + 1) - math.lgamma(c1 - a + 1) - math.lgamma(n - r1 - c1 + a + 1)
            - (math.lgamma(n + 1) - math.lgamma(c1 + 1) - math.lgamma(n - c1 + 1)))


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided p for the table [[a, b], [c, d]] (rows: groups; columns: event, no event)."""
    r1, n = a + b, a + b + c + d
    c1 = a + c
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    obs = _hyper_logp(a, r1, c1, n)
    total = 0.0
    for x in range(lo, hi + 1):
        lp = _hyper_logp(x, r1, c1, n)
        if lp <= obs + 1e-7:
            total += math.exp(lp)
    return min(1.0, total)


def fisher_power(p1: float, p2: float, n1: int, n2: int, alpha: float = 0.05) -> float:
    """Exact power of the two-sided Fisher test by enumerating every outcome."""
    power = 0.0
    pm1 = [math.exp(_log_binom_pmf(x, n1, p1)) for x in range(n1 + 1)]
    pm2 = [math.exp(_log_binom_pmf(y, n2, p2)) for y in range(n2 + 1)]
    for x in range(n1 + 1):
        if pm1[x] < 1e-15:
            continue
        for y in range(n2 + 1):
            if pm2[y] < 1e-15:
                continue
            if fisher_exact(x, n1 - x, y, n2 - y) <= alpha:
                power += pm1[x] * pm2[y]
    return power


# ---------- Beta functions (Jeffreys) ----------

def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Numerical Recipes, Lentz's method)."""
    tiny, eps = 1e-300, 3e-16
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = tiny if abs(d) < tiny else d
    d = 1.0 / d
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1.0 - x) / b


def beta_ppf(q: float, a: float, b: float) -> float:
    return _bisect(lambda x: betainc(a, b, x) - q, 0.0, 1.0)


def jeffreys(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    a, b = k + 0.5, n - k + 0.5
    lower = 0.0 if k == 0 else beta_ppf(alpha / 2, a, b)
    upper = 1.0 if k == n else beta_ppf(1 - alpha / 2, a, b)
    return lower, upper


def prob_beta_diff_greater(k1: int, n1: int, k2: int, n2: int, delta: float, draws: int = 200_000,
                           seed: int = 20261107) -> float:
    """P(p1 - p2 > delta) under independent Jeffreys posteriors, by Monte Carlo with a fixed seed."""
    rng = random.Random(seed)
    hits = 0
    for _ in range(draws):
        x = rng.betavariate(k1 + 0.5, n1 - k1 + 0.5)
        y = rng.betavariate(k2 + 0.5, n2 - k2 + 0.5)
        hits += (x - y) > delta
    return hits / draws


# ---------- cluster bootstrap ----------

def cluster_bootstrap(rows: Sequence[dict], cluster: Callable[[dict], object], stat: Callable[[list], float],
                      reps: int = 10_000, seed: int = 20261107, alpha: float = 0.05) -> tuple[float, float, float]:
    """Percentile interval for stat(rows), resampling whole clusters with replacement."""
    groups: dict = {}
    for r in rows:
        groups.setdefault(cluster(r), []).append(r)
    keys = sorted(groups, key=str)
    rng = random.Random(seed)
    point = stat(list(rows))
    vals = []
    for _ in range(reps):
        sample: list = []
        for _k in keys:
            sample.extend(groups[keys[rng.randrange(len(keys))]])
        vals.append(stat(sample))
    vals.sort()
    lo = vals[int(math.floor((alpha / 2) * reps))]
    hi = vals[min(reps - 1, int(math.ceil((1 - alpha / 2) * reps)) - 1)]
    return point, lo, hi


def rate(rows: Iterable[dict], key: str) -> float:
    rows = list(rows)
    return sum(1 for r in rows if r[key]) / len(rows) if rows else float("nan")
