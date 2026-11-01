from pathlib import Path
import hashlib
import json
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import scipy

from drift import compare, severity, AlertManager

R = Path(__file__).resolve().parent
FEATURES = {
    'activePowerKw': ('Lab8Observation', 'timestamp', 'Active power, kW', 0, 20),
    'voltageV': ('Lab8Observation', 'timestamp', 'Voltage, V', 180, 270),
    'forecastKwh': ('Lab8Forecast', 'targetTime', 'Forecast energy, kWh', 0, 20),
}


def contract_errors(batch):
    errors = []
    for feature, (_, _, _, lo, hi) in FEATURES.items():
        values = np.asarray(batch.get(feature, []), dtype=float)
        if len(values) < 1000 or not np.isfinite(values).all():
            errors.append(feature + ': missing/nonfinite/insufficient values')
        elif np.any((values < lo) | (values > hi)):
            errors.append(feature + ': outside agreed physical/unit range')
    return errors


def json_write(name, value):
    (R / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')


def main():
    (R / 'results').mkdir(exist_ok=True)
    (R / 'figures').mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    path = R / 'data/nodes.json'
    nodes = json.loads(path.read_text('utf-8'))
    reference, pool, info = {}, {}, {}
    for feature, (label, timestamp, title, lo, hi) in FEATURES.items():
        rows = sorted((n['properties'] for n in nodes if label in n['labels']),
                      key=lambda p: p[timestamp])
        # Independent splits from a historical pool; not a live time-series claim.
        rows = rows[:6000]
        assert len(rows) == 6000
        order = rng.permutation(len(rows))
        ref_ids, cur_ids = order[:3000], order[3000:]
        values = np.array([p[feature] for p in rows])
        reference[feature], pool[feature] = values[ref_ids], values[cur_ids]
        info[feature] = dict(label=label, unit=title.split(', ')[-1],
                             n_reference=3000, n_pool=3000,
                             historical_start=rows[0][timestamp],
                             historical_end=rows[-1][timestamp],
                             mean=float(reference[feature].mean()),
                             std=float(reference[feature].std(ddof=1)),
                             reference_ids=[rows[int(i)][timestamp] for i in ref_ids],
                             current_ids=[rows[int(i)][timestamp] for i in cur_ids])
    json_write('data/reference.json', {k: v.tolist() for k, v in reference.items()})
    json_write('data/current_pool.json', {k: v.tolist() for k, v in pool.items()})
    json_write('data/reference_manifest.json', dict(
        seed=42, source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        design='first 6000 historical rows per population; seeded disjoint random split 3000/3000',
        scope='graph input features and stored forecast scores; not RAG request score drift',
        features=info))
    cases = {
        'calm': pool,
        'mean_plus_1sigma': {k: v + reference[k].std(ddof=1) for k, v in pool.items()},
        'units_times_100': {k: v * 100 for k, v in pool.items()},
    }
    results = {}
    for name, values in cases.items():
        metrics = compare(reference, values)
        errors = contract_errors(values)
        alert = AlertManager().check(metrics, 0, defect=bool(errors))
        results[name] = dict(metrics=metrics, contract_errors=errors, alert=alert)
        fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), layout='constrained')
        for ax, (feature, (_, _, title, _, _)) in zip(axes, FEATURES.items()):
            combined = np.r_[reference[feature], values[feature]]
            bins = np.linspace(combined.min(), combined.max(), 45)
            ax.hist(reference[feature], bins=bins, density=True, histtype='step',
                    linewidth=1.8, label='Reference, n=3000')
            ax.hist(values[feature], bins=bins, density=True, histtype='step',
                    linewidth=1.8, label='Current, n=3000')
            ax.set(xlabel=title, ylabel='Density', title=f"PSI={metrics[feature]['psi']:.3f}")
            ax.legend(fontsize=8)
        fig.savefig(R / f'figures/{name}.png', dpi=180)
        plt.close(fig)
    json_write('results/drift.json', results)

    # Weeks are deliberately modeled windows, not calendar observations.
    weekly = []
    for week, shift in enumerate([0, 0, .1, .2, .35, .5, .75, 1, 1, 0], 1):
        batch = {k: rng.choice(v, 1000) + shift * reference[k].std(ddof=1)
                 for k, v in pool.items()}
        metrics = compare(reference, batch)
        weekly.append(dict(simulated_week=week, sigma_shift=shift, metrics=metrics,
                           level=severity(metrics)))
    json_write('results/weeks.json', weekly)
    fig, ax = plt.subplots(figsize=(9, 4), layout='constrained')
    for feature in FEATURES:
        ax.plot([w['simulated_week'] for w in weekly],
                [w['metrics'][feature]['psi'] for w in weekly], marker='o', label=feature)
    ax.axhline(.1, color='gray', linestyle='--', label='Warning 0.10')
    ax.axhline(.25, color='black', linestyle=':', label='Critical 0.25')
    ax.set(xlabel='Simulated week', ylabel='PSI', title='Modeled drift over 10 windows')
    ax.legend()
    fig.savefig(R / 'figures/psi_weeks.png', dpi=180)
    plt.close(fig)

    quiet = []
    for i in range(100):
        batch = {k: rng.choice(v, 1000) for k, v in pool.items()}
        metrics = compare(reference, batch)
        quiet.append(dict(window=i, level=severity(metrics), metrics=metrics))
    count = sum(w['level'] is not None for w in quiet)
    json_write('results/false_alarms.json', dict(
        n_windows=100, n_per_feature=1000, alerts=count, rate=count / 100,
        design='bootstrap of held-out historical pool; windows overlap, not independent live weeks',
        windows=quiet))

    manager = AlertManager(cooldown=900)
    drift_metrics = results['mean_plus_1sigma']['metrics']
    alerts = [manager.check(drift_metrics, 0), manager.check(drift_metrics, 60),
              manager.check(drift_metrics, 901),
              manager.check(results['units_times_100']['metrics'], 902, defect=True),
              manager.check({}, 903, llm_failed=True)]
    # An availability failure is injected in a separate API test, not inferred from PSI.
    json_write('results/alerts.json', dict(cooldown_seconds=900, events=alerts,
                                         llm_scenario='modeled failure; see fault_injection.json'))
    json_write('results/monitor_environment.json', dict(
        python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        matplotlib=matplotlib.__version__, seed=42))
    print(json.dumps(dict(drift_levels={k: v['alert'] for k, v in results.items()},
                          quiet_alerts=count), ensure_ascii=False))


if __name__ == '__main__':
    main()
