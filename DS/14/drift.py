import numpy as np
from scipy.stats import ks_2samp


def finite_sample(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError('Expected at least two finite numeric values')
    return x


def psi(expected, actual, bins=10):
    expected, actual = finite_sample(expected), finite_sample(actual)
    if bins < 2:
        raise ValueError('At least two bins required')
    # Freeze edges on reference only; open tails count out-of-range observations.
    inner = np.unique(np.quantile(expected, np.arange(1, bins) / bins))
    if np.ptp(expected) == 0:
        center = expected[0]
        tolerance = np.sqrt(np.finfo(float).eps) * max(1, abs(center))
        edges = np.array([-np.inf, center-tolerance, center+tolerance, np.inf])
    else:
        edges = np.r_[-np.inf, inner, np.inf]
    e = np.histogram(expected, edges)[0].astype(float)
    a = np.histogram(actual, edges)[0].astype(float)
    # Jeffreys pseudocount prevents log(0); both vectors remain normalized.
    e = (e + .5) / (e.sum() + .5 * len(e))
    a = (a + .5) / (a.sum() + .5 * len(a))
    return float(np.sum((a - e) * np.log(a / e)))


def compare(reference, current):
    result = {}
    for feature, expected in reference.items():
        actual = current[feature]
        ks = ks_2samp(finite_sample(expected), finite_sample(actual))
        result[feature] = dict(psi=psi(expected, actual),
                               ks=float(ks.statistic), pvalue=float(ks.pvalue),
                               n_reference=len(expected), n_current=len(actual))
    return result


def severity(features):
    # Bonferroni family threshold for three features, plus PSI effect-size gate.
    changed = [v for v in features.values() if v['pvalue'] < .01 / 3]
    if sum(v['psi'] >= .25 for v in changed) >= 2:
        return 'critical'
    if sum(v['psi'] >= .1 for v in changed) >= 2:
        return 'warning'
    return None


class AlertManager:
    def __init__(self, cooldown=900):
        self.cooldown = cooldown
        self.last = {}

    def check(self, features, now, defect=False, llm_failed=False):
        # LLM availability and contract defects must not wait for two features.
        kind = ('llm_failure' if llm_failed else
                'data_defect' if defect else 'data_drift')
        level = 'critical' if (defect or llm_failed) else severity(features)
        if level is None:
            return None
        previous = self.last.get(kind)
        escalation = previous and previous['level'] == 'warning' and level == 'critical'
        if previous and now - previous['at'] < self.cooldown and not escalation:
            return dict(kind=kind, level=level, suppressed=True, at=now)
        self.last[kind] = dict(at=now, level=level)
        return dict(kind=kind, level=level, suppressed=False, at=now)
