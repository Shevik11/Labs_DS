"""ЛР 2: застосування машинного навчання до енергетичних даних.
Варіант: енергетика / програмне забезпечення / візуалізація.
"""
from __future__ import annotations
import json
from pathlib import Path
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_score, recall_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "hourly_clean.csv"
RESULTS = ROOT / "results"
PLOTS = RESULTS / "plots"
SEED = 42
POWER = "Global_active_power"
NUMERIC = [POWER, "Global_reactive_power", "Voltage", "Global_intensity",
           "Sub_metering_1", "Sub_metering_2", "Sub_metering_3"]

def run_lab():
    RESULTS.mkdir(exist_ok=True)
    PLOTS.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid")
    raw = pd.read_csv(DATA, parse_dates=["timestamp"]).set_index("timestamp").sort_index().asfreq("h")
    required = NUMERIC + ["energy_kwh"]
    if not set(required).issubset(raw.columns):
        raise ValueError(f"У CSV бракує колонок: {set(required) - set(raw.columns)}")
    features = raw[NUMERIC].copy()
    for lag in (1, 2, 24, 168):
        features[f"power_lag_{lag}h"] = raw[POWER].shift(lag)
    features["power_mean_24h"] = raw[POWER].rolling(24, min_periods=24).mean()
    future = features.index + pd.Timedelta(hours=1)
    features["hour_sin"] = np.sin(2 * np.pi * future.hour / 24)
    features["hour_cos"] = np.cos(2 * np.pi * future.hour / 24)
    features["weekday_sin"] = np.sin(2 * np.pi * future.dayofweek / 7)
    features["weekday_cos"] = np.cos(2 * np.pi * future.dayofweek / 7)
    data = features.assign(target=raw["energy_kwh"].shift(-1)).dropna()
    cut = int(len(data) * .7)
    test = data.iloc[cut:]
    train = data.iloc[:cut]
    X_train, y_train = train.drop(columns="target"), train["target"]
    X_test, y_test = test.drop(columns="target"), test["target"]
    threshold = float(y_train.quantile(.75))
    y_train_class = (y_train > threshold).astype(int)
    y_test_class = (y_test > threshold).astype(int)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=SEED))
    model.fit(X_train, y_train_class)
    predicted = model.predict(X_test)
    baseline = DummyClassifier(strategy="most_frequent").fit(X_train, y_train_class)
    baseline_pred = baseline.predict(X_test)
    report = classification_report(y_test_class, predicted, labels=[0, 1],
        target_names=["Звичайне", "Високе"], output_dict=True, zero_division=0)
    metrics = {
        "variant": {"industry": "Енергетика", "domain": "Програмне забезпечення", "task": "Візуалізація"},
        "dataset": {"source": "UCI Individual Household Electric Power Consumption",
                    "url": "https://archive.ics.uci.edu/dataset/235/individualhouseholdelectricpowerconsumption",
                    "clean_hourly_rows": int(raw["energy_kwh"].notna().sum()),
                    "hourly_grid_rows": int(len(raw)), "prepared_rows": int(len(data)),
                    "scope": "одне домогосподарство у Франції, 2006-2010"},
        "classification": {
            "target_threshold_kwh": threshold,
            "accuracy": float(accuracy_score(y_test_class, predicted)),
            "majority_baseline_accuracy": float(accuracy_score(y_test_class, baseline_pred)),
            "precision_high": float(precision_score(y_test_class, predicted, zero_division=0)),
            "recall_high": float(recall_score(y_test_class, predicted, zero_division=0)),
            "f1_high": float(f1_score(y_test_class, predicted, zero_division=0)),
            "report": report,
            "confusion_matrix_labels": ["Звичайне", "Високе"],
            "confusion_matrix": confusion_matrix(y_test_class, predicted, labels=[0, 1]).tolist()
        },
        "split": {"train_rows": int(len(train)), "test_rows": int(len(test)),
                  "train_start": str(train.index.min()), "train_end": str(train.index.max()),
                  "test_start": str(test.index.min()), "test_end": str(test.index.max()),
                  "type": "часовий поділ 70/30; тест містить пізніші спостереження"}
    }
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    pred = pd.DataFrame({
        "target_timestamp": X_test.index + pd.Timedelta(hours=1),
        "actual_energy_kwh": y_test.to_numpy(),
        "actual_class": y_test_class.to_numpy(),
        "predicted_class": predicted,
        "probability_high": model.predict_proba(X_test)[:, 1]
    })
    pred.to_csv(RESULTS / "test_predictions.csv", index=False)
    joblib.dump({"model": model, "threshold_kwh": threshold, "features": list(X_train.columns)},
                RESULTS / "model.joblib")
    pd.DataFrame({"class": ["Звичайне", "Високе"],
                  "кількість_навчання": y_train_class.value_counts().reindex([0,1]).to_numpy(),
                  "кількість_тест": y_test_class.value_counts().reindex([0,1]).to_numpy()}).to_csv(
                      RESULTS / "class_distribution.csv", index=False)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(confusion_matrix(y_test_class, predicted, labels=[0,1]), annot=True, fmt="d",
        cmap="Blues", xticklabels=["Звичайне", "Високе"], yticklabels=["Звичайне", "Високе"], ax=ax)
    ax.set(xlabel="Передбачений клас", ylabel="Фактичний клас", title="Матриця помилок")
    fig.tight_layout(); fig.savefig(PLOTS / "confusion_matrix.png", dpi=170); plt.close(fig)
    dist = pd.read_csv(RESULTS / "class_distribution.csv").set_index("class")
    ax = dist.plot(kind="bar", figsize=(7,4), color=["#4c78a8", "#f58518"])
    ax.set(title="Розподіл класів у навчальній і тестовій вибірках", xlabel="Клас", ylabel="Кількість годин")
    ax.tick_params(axis="x", rotation=0); ax.legend(["Навчання", "Тест"])
    plt.tight_layout(); plt.savefig(PLOTS / "class_distribution.png", dpi=170); plt.close()
    score = pd.Series({"Модель": metrics["classification"]["accuracy"],
                       "Базовий прогноз": metrics["classification"]["majority_baseline_accuracy"]})
    ax = score.plot(kind="bar", figsize=(6,4), color=["#54a24b", "#bab0ac"], ylim=(0,1))
    ax.set(title="Точність на тестовій вибірці", ylabel="Accuracy", xlabel="")
    ax.tick_params(axis="x", rotation=0)
    for i, val in enumerate(score): ax.text(i, val + .02, f"{val:.3f}", ha="center")
    plt.tight_layout(); plt.savefig(PLOTS / "accuracy.png", dpi=170); plt.close()
    cls = metrics["classification"]
    print(f"Accuracy={cls['accuracy']:.4f}; majority_baseline={cls['majority_baseline_accuracy']:.4f}; high_recall={cls['recall_high']:.4f}")
    print(f"Results saved to {RESULTS}")
    return metrics

if __name__ == "__main__":
    run_lab()

