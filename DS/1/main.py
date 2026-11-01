"""ЛР 1: енергетика / програмне забезпечення / візуалізація.

Запуск: python main.py. Дані UCI завантажуються автоматично.
Прогноз формується після завершення поточної години на наступну годину.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request
import zipfile

os.environ.setdefault("OMP_NUM_THREADS", "2")
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report,
    confusion_matrix, f1_score, mean_absolute_error, mean_squared_error,
    precision_score, r2_score, recall_score, silhouette_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
URL = "https://archive.ics.uci.edu/static/public/235/individual+household+electric+power+consumption.zip"
SOURCE = "https://archive.ics.uci.edu/dataset/235/individualhouseholdelectricpowerconsumption"
SEED = 42
POWER = "Global_active_power"
NUMERIC = [POWER, "Global_reactive_power", "Voltage", "Global_intensity",
           "Sub_metering_1", "Sub_metering_2", "Sub_metering_3"]


def save_plot(folder, name):
    plt.tight_layout()
    plt.savefig(folder / name, dpi=160, bbox_inches="tight")
    plt.close()


def obtain_data(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".download")
    print("Завантаження даних UCI...")
    try:
        with urllib.request.urlopen(URL, timeout=120) as response, temp.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        with zipfile.ZipFile(temp) as archive:
            if archive.testzip() is not None:
                raise ValueError("Пошкоджений архів UCI")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    return path


def prepare(path, out):
    """KDD: вибір, очищення, агрегація; неповні години не заповнюємо"""
    with zipfile.ZipFile(path) as archive:
        with archive.open("household_power_consumption.txt") as stream:
            raw = pd.read_csv(stream, sep=";", na_values=["?", ""],
                              dtype={c: "float64" for c in NUMERIC})
    audit = {"raw_rows": len(raw)}
    raw["timestamp"] = pd.to_datetime(raw["Date"] + " " + raw["Time"],
                                       format="%d/%m/%Y %H:%M:%S", errors="coerce")
    audit["rows_with_missing_values"] = int(raw[NUMERIC + ["timestamp"]].isna().any(axis=1).sum())
    clean = raw.dropna(subset=NUMERIC + ["timestamp"]).copy()
    before = len(clean)
    clean = clean.drop_duplicates(subset=["timestamp"] + NUMERIC)
    audit["exact_duplicate_measurements_removed"] = before - len(clean)
    if clean["timestamp"].duplicated().any():
        raise ValueError("Знайдено суперечливі вимірювання з однаковим часом")
    clean = clean.set_index("timestamp")[NUMERIC].sort_index()
    invalid = (clean < 0).any(axis=1) | (clean["Voltage"] <= 0)
    audit["invalid_rows_removed"] = int(invalid.sum())
    clean = clean.loc[~invalid]
    audit["clean_minute_rows"] = len(clean)
    counts = clean[POWER].resample("h").count()
    hourly = clean.resample("h").mean()
    # Кожне значення - середня потужність за хвилину (кВт).
    hourly["energy_kwh"] = clean[POWER].resample("h").sum(min_count=60) / 60
    hourly.loc[counts != 60, :] = np.nan
    audit["complete_hours"] = int((counts == 60).sum())
    audit["incomplete_hours_excluded"] = int((counts != 60).sum())
    hourly.dropna().to_csv(out / "hourly_clean.csv", index_label="timestamp")
    return hourly, audit


def supervised(hourly, out, plots):
    features = hourly[NUMERIC].copy()
    for lag in (1, 2, 24, 168):
        features[f"power_lag_{lag}h"] = hourly[POWER].shift(lag)
    features["power_mean_24h"] = hourly[POWER].rolling(24, min_periods=24).mean()
    future = features.index + pd.Timedelta(hours=1)
    features["hour_sin"] = np.sin(2 * np.pi * future.hour / 24)
    features["hour_cos"] = np.cos(2 * np.pi * future.hour / 24)
    features["weekday_sin"] = np.sin(2 * np.pi * future.dayofweek / 7)
    features["weekday_cos"] = np.cos(2 * np.pi * future.dayofweek / 7)
    data = features.assign(target=hourly["energy_kwh"].shift(-1)).dropna()
    split = int(len(data) * .7)
    if split < 100 or len(data) - split < 50:
        raise ValueError("Замало повних спостережень для навчання та тестування")
    test = data.iloc[split:]
    # Виключаємо ціль навчання, яка потрапила б у період тестування
    train = data.iloc[:split]
    train = train.loc[train.index + pd.Timedelta(hours=1) < test.index.min()]
    X_train, y_train = train.drop(columns="target"), train["target"]
    X_test, y_test = test.drop(columns="target"), test["target"]
    threshold = float(y_train.quantile(.75))
    c_train, c_test = (y_train > threshold).astype(int), (y_test > threshold).astype(int)
    classifier = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=SEED))
    classifier.fit(X_train, c_train)
    c_pred = classifier.predict(X_test)
    dummy = DummyClassifier(strategy="most_frequent").fit(X_train, c_train)
    regressor = make_pipeline(StandardScaler(), RandomForestRegressor(
        n_estimators=160, min_samples_leaf=4, max_features=.8, random_state=SEED, n_jobs=1))
    regressor.fit(X_train, y_train)
    y_pred = regressor.predict(X_test)
    # Середня потужність поточної повної години * 1 год = енергія наступної
    # за наївним припущенням незмінного навантаження.
    baseline = X_test[POWER].to_numpy()
    metrics = {
        "classification": {"accuracy": accuracy_score(c_test, c_pred),
            # "precision": precision_score(c_test, c_pred, zero_division=0), # справжні позитивні прогнози
            # "recall": recall_score(c_test, c_pred, zero_division=0), # здатність виявляти позитивний клас
            # "f1": f1_score(c_test, c_pred, zero_division=0), # 2 * (добуток/суму precision та recall)
            "majority_baseline_accuracy": accuracy_score(c_test, dummy.predict(X_test)),
            "report": classification_report(c_test, c_pred, labels=[0, 1],
                target_names=["normal", "high"], output_dict=True, zero_division=0)},
        "regression": {"mae_kwh": mean_absolute_error(y_test, y_pred), # середнє арифметичне абсолютних різниць
            "mse_kwh_squared": mean_squared_error(y_test, y_pred), # середнє арифметичне квадратів різниць
            "r2": r2_score(y_test, y_pred), # частка дисперсії (на скільки % краще за просте середнє)
            "persistence_mae_kwh": mean_absolute_error(y_test, baseline),
            "persistence_mse_kwh_squared": mean_squared_error(y_test, baseline),
            "persistence_r2": r2_score(y_test, baseline)},
        "split": {"train_rows": len(train), "test_rows": len(test),
            "train_start": str(train.index.min()), "train_end": str(train.index.max()),
            "test_start": str(test.index.min()), "test_end": str(test.index.max()),
            "high_threshold_kwh": threshold,
            "rule": "next-hour energy > training target 75th percentile"}}
    for name, X, y, classes in [("train", X_train, y_train, c_train), ("test", X_test, y_test, c_test)]:
        scaled = pd.DataFrame(classifier[0].transform(X), index=X.index, columns=X.columns)
        scaled.assign(target_energy_kwh=y, target_high=classes).to_csv(out / f"{name}_normalized.csv")
    predictions = pd.DataFrame({"target_timestamp": X_test.index + pd.Timedelta(hours=1),
        "actual_kwh": y_test.to_numpy(), "predicted_kwh": y_pred,
        "persistence_kwh": baseline, "actual_high": c_test.to_numpy(),
        "predicted_high": c_pred, "probability_high": classifier.predict_proba(X_test)[:, 1]})
    predictions.to_csv(out / "test_predictions.csv", index=False)
    joblib.dump({"classifier": classifier, "regressor": regressor,
        "high_threshold_kwh": threshold, "feature_columns": list(X_train.columns)}, out / "models.joblib")
    plt.figure(figsize=(6, 5))
    sns.heatmap(confusion_matrix(c_test, c_pred, labels=[0, 1]), annot=True, fmt="d", cmap="Blues",
                xticklabels=["Звичайне", "Високе"], yticklabels=["Звичайне", "Високе"])
    plt.xlabel("Прогноз"); plt.ylabel("Фактичний клас")
    plt.title("Класифікація навантаження наступної години")
    save_plot(plots, "03_confusion_matrix.png")
    window = predictions.loc[predictions.target_timestamp < predictions.target_timestamp.min() + pd.Timedelta(days=7)]
    # Розриви даних показуємо розривами ліній, без уявної інтерполяції.
    window = window.set_index("target_timestamp").asfreq("h").reset_index()
    plt.figure(figsize=(12, 5))
    for col, label in [("actual_kwh", "Факт"), ("predicted_kwh", "Random Forest")]:
        plt.plot(window.target_timestamp, window[col], label=label, linewidth=1.3)
    plt.ylabel("Енергія, кВт·год"); plt.xlabel("Час"); plt.legend()
    plt.title("Однокрокові прогнози на першому тижні тестового періоду")
    save_plot(plots, "04_forecast.png")
    plt.figure(figsize=(6, 6))
    plt.scatter(y_test, y_pred, s=7, alpha=.18)
    lim = max(float(y_test.max()), float(y_pred.max()))
    plt.plot([0, lim], [0, lim], "r--")
    plt.xlabel("Факт, кВт·год"); plt.ylabel("Прогноз, кВт·год")
    plt.title("Регресія: фактичні та прогнозовані значення")
    save_plot(plots, "05_regression_scatter.png")
    return metrics


def cluster_days(hourly, out, plots):
    profiles = hourly[["energy_kwh"]].copy()
    profiles["date"] = profiles.index.normalize()
    profiles["hour"] = profiles.index.hour
    daily = profiles.pivot(index="date", columns="hour", values="energy_kwh").dropna()
    if len(daily) < 10:
        raise ValueError("Недостатньо повних діб для кластеризації")
    scaler = StandardScaler()
    X = scaler.fit_transform(daily)
    scores, models = [], {}
    for k in range(2, 9):
        model = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(X)
        score = silhouette_score(X, model.labels_, sample_size=min(1200, len(X)), random_state=SEED)
# inertia - сума квадратів відстаней від діб до центрів їхніх кластерів
# silhouette - оцінка розділеності кластерів
        scores.append({"k": k, "inertia": float(model.inertia_), "silhouette": float(score)})
        models[k] = model
    table = pd.DataFrame(scores)
    best_k = int(table.loc[table.silhouette.idxmax(), "k"])
    model = models[best_k]
    table.to_csv(out / "cluster_selection.csv", index=False)
    daily.assign(cluster=model.labels_).to_csv(out / "daily_clusters.csv")
    pd.DataFrame(X, index=daily.index, columns=daily.columns).assign(cluster=model.labels_).to_csv(out / "daily_normalized.csv")
    joblib.dump({"scaler": scaler, "model": model, "hour_columns": list(daily.columns)}, out / "clusters.joblib")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(table.k, table.inertia, "o-")
    axes[0].set(xlabel="Кількість кластерів", ylabel="Інерція", title="Метод ліктя")
    axes[1].plot(table.k, table.silhouette, "o-")
    axes[1].axvline(best_k, color="red", linestyle="--", label=f"Обрано k={best_k}")
    axes[1].set(xlabel="Кількість кластерів", ylabel="Silhouette", title="Перевірка розділеності")
    axes[1].legend()
    save_plot(plots, "06_cluster_selection.png")
    plt.figure(figsize=(10, 5))
    for label in range(best_k):
        selected = daily.loc[model.labels_ == label]
        plt.plot(daily.columns, selected.mean(), marker="o", label=f"Кластер {label}: {len(selected)} діб")
    plt.xticks(range(0, 24, 2)); plt.xlabel("Година доби"); plt.ylabel("Енергія за годину, кВт·год")
    plt.title("Середні добові профілі споживання"); plt.legend()
    save_plot(plots, "07_daily_clusters.png")
    return {"complete_days": len(daily), "selected_k": best_k,
        "selection_rule": "maximum sampled silhouette for k=2..8; elbow shown for visual review",
        "silhouette": float(table.silhouette.max()),
        "cluster_sizes": {str(i): int((model.labels_ == i).sum()) for i in range(best_k)},
        "scope": "exploratory clustering of all complete days, not a held-out predictive score"}


def overview(hourly, plots):
    daily_count = hourly.energy_kwh.resample("D").count()
    daily_energy = hourly.energy_kwh.resample("D").sum(min_count=24)
    daily_energy[daily_count != 24] = np.nan
    plt.figure(figsize=(12, 4))
    plt.plot(daily_energy.index, daily_energy, linewidth=.6)
    plt.ylabel("Енергія, кВт·год/добу"); plt.xlabel("Дата")
    plt.title("Добове електроспоживання: лише повні доби")
    save_plot(plots, "01_daily_consumption.png")
    frame = hourly[["energy_kwh"]].copy()
    frame["weekday"] = frame.index.dayofweek
    frame["hour"] = frame.index.hour
    heat = frame.pivot_table(index="weekday", columns="hour", values="energy_kwh", aggfunc="mean")
    plt.figure(figsize=(12, 4))
    sns.heatmap(heat, cmap="YlOrRd", yticklabels=["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
                cbar_kws={"label": "Середня енергія за годину, кВт·год"})
    plt.xlabel("Година"); plt.ylabel("День тижня"); plt.title("Тижневий профіль навантаження")
    save_plot(plots, "02_weekly_heatmap.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "household_power_consumption.zip")
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    out = args.output.resolve()
    plots = out / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", font="DejaVu Sans")
    path = obtain_data(args.data.resolve())
    print("Очищення та підготовка даних...", flush=True)
    hourly, audit = prepare(path, out)
    overview(hourly, plots)
    print("Навчання класифікації та регресії...", flush=True)
    metrics = supervised(hourly, out, plots)
    print("Кластеризація добових профілів...", flush=True)
    metrics["clustering"] = cluster_days(hourly, out, plots)
    metrics["data_quality"] = audit
    metrics["source"] = {"url": SOURCE, "download_url": URL,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "license": "CC BY 4.0"}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items() if k in ("regression", "clustering")}, indent=2, ensure_ascii=False))
    print(f"Готово. Результати: {out}")


if __name__ == "__main__":
    main()
