"""Metricas de classificacao com suporte a peso amostral.

A classe positiva e "1". No modelo de aluno, 1 = alfabetizado; a classe de
interesse para politica publica e a 0 (nao alfabetizado), por isso as metricas
sao reportadas tambem para ela (recall_negativos, precisao_negativos).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    r2_score,
    roc_auc_score,
    roc_curve,
)


def avaliar_classificacao(
    y: np.ndarray,
    proba: np.ndarray,
    limiar: float = 0.5,
    sample_weight: np.ndarray | None = None,
) -> dict[str, float]:
    y = np.asarray(y).astype(int)
    pred = (np.asarray(proba) >= limiar).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1], sample_weight=sample_weight).ravel()
    total = tn + fp + fn + tp
    precisao = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precisao * recall / (precisao + recall) if (precisao + recall) > 0 else 0.0
    precisao_neg = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    recall_neg = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    return {
        "auc_roc": float(roc_auc_score(y, proba, sample_weight=sample_weight)),
        "auc_pr": float(average_precision_score(y, proba, sample_weight=sample_weight)),
        "acuracia": float((tp + tn) / total),
        "precisao": float(precisao),
        "recall": float(recall),
        "f1": float(f1),
        "precisao_negativos": float(precisao_neg),
        "recall_negativos": float(recall_neg),
        "limiar": float(limiar),
        "taxa_base": float((tp + fn) / total),
    }


def matriz_confusao(
    y: np.ndarray, proba: np.ndarray, limiar: float = 0.5, rotulos=("0", "1")
) -> pd.DataFrame:
    pred = (np.asarray(proba) >= limiar).astype(int)
    m = confusion_matrix(np.asarray(y).astype(int), pred, labels=[0, 1])
    return pd.DataFrame(
        m,
        index=[f"real {rotulos[0]}", f"real {rotulos[1]}"],
        columns=[f"previsto {rotulos[0]}", f"previsto {rotulos[1]}"],
    )


def curva_roc(y, proba, sample_weight=None) -> pd.DataFrame:
    fpr, tpr, thr = roc_curve(y, proba, sample_weight=sample_weight)
    return pd.DataFrame({"fpr": fpr, "tpr": tpr, "limiar": thr})


def curva_pr(y, proba, sample_weight=None) -> pd.DataFrame:
    p, r, thr = precision_recall_curve(y, proba, sample_weight=sample_weight)
    return pd.DataFrame({"precisao": p[:-1], "recall": r[:-1], "limiar": thr})


def varrer_limiares(
    y, proba, limiares=None, sample_weight=None, passo: float = 0.02
) -> pd.DataFrame:
    """Metricas para cada limiar; serve para escolher o ponto de operacao."""
    if limiares is None:
        limiares = np.round(np.arange(0.1, 0.91, passo), 2)
    linhas = [avaliar_classificacao(y, proba, t, sample_weight) for t in limiares]
    return pd.DataFrame(linhas)


def limiar_por_recall_negativos(y, proba, recall_minimo: float, sample_weight=None) -> float:
    """Menor limiar que garante o recall minimo da classe 0 (nao alfabetizado /
    nao atingiu a meta): quanto maior o limiar, mais casos viram classe 0."""
    tabela = varrer_limiares(y, proba, sample_weight=sample_weight, passo=0.01)
    ok = tabela[tabela["recall_negativos"] >= recall_minimo]
    if ok.empty:
        return float(tabela["limiar"].max())
    return float(ok["limiar"].min())


# ---------------------------------------------------------------------------
# Regressao do nivel do indicador e risco derivado
# ---------------------------------------------------------------------------


def avaliar_regressao(y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    return {
        "mae": float(mean_absolute_error(y, pred)),
        "rmse": float(np.sqrt(mean_squared_error(y, pred))),
        "r2": float(r2_score(y, pred)),
        "vies": float((pred - y).mean()),
        "spearman": float(stats.spearmanr(y, pred).statistic),
    }


def risco_de_nao_atingir(
    pred_nivel: np.ndarray, meta: np.ndarray, residuos: np.ndarray
) -> np.ndarray:
    """Probabilidade de o nivel real ficar abaixo da meta, dado o nivel previsto.

    Usa a distribuicao empirica dos residuos (real - previsto) da validacao:
    P(real < meta) = P(residuo < meta - previsto). Municipios sem meta recebem NaN.
    """
    residuos = np.sort(np.asarray(residuos, dtype=float))
    folga = np.asarray(meta, dtype=float) - np.asarray(pred_nivel, dtype=float)
    risco = np.searchsorted(residuos, folga, side="right") / len(residuos)
    return np.where(np.isnan(folga), np.nan, risco)
