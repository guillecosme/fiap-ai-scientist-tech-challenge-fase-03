"""Validacao: cruzada por grupos, backtest temporal e curvas de aprendizado."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import learning_curve
from sklearn.pipeline import Pipeline

from src.evaluation.metricas import avaliar_classificacao, avaliar_regressao
from src.preprocessing.splits import cv_por_municipio, cv_por_municipio_regressao


def validar_por_grupos(
    pipeline: Pipeline,
    x: pd.DataFrame,
    y: pd.Series,
    grupos: pd.Series,
    n_splits: int = 5,
    sample_weight: np.ndarray | None = None,
    limiar: float = 0.5,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Metricas por fold (treino e validacao) e as probabilidades fora da amostra.

    As probabilidades fora da amostra (out-of-fold) permitem analisar erros e
    escolher o limiar sem tocar no conjunto de teste.
    """
    y = np.asarray(y)
    oof = np.full(len(y), np.nan)
    linhas = []
    for k, (tr, va) in enumerate(cv_por_municipio(n_splits).split(x, y, grupos)):
        modelo = clone(pipeline)
        fit_params = {}
        if sample_weight is not None:
            fit_params["modelo__sample_weight"] = sample_weight[tr]
        modelo.fit(x.iloc[tr], y[tr], **fit_params)
        p_tr = modelo.predict_proba(x.iloc[tr])[:, 1]
        p_va = modelo.predict_proba(x.iloc[va])[:, 1]
        oof[va] = p_va
        w_tr = None if sample_weight is None else sample_weight[tr]
        w_va = None if sample_weight is None else sample_weight[va]
        m_tr = avaliar_classificacao(y[tr], p_tr, limiar, w_tr)
        m_va = avaliar_classificacao(y[va], p_va, limiar, w_va)
        linhas.append({"fold": k, "conjunto": "treino", **m_tr})
        linhas.append({"fold": k, "conjunto": "validacao", **m_va})
    return pd.DataFrame(linhas), oof


def resumir_folds(
    tabela: pd.DataFrame, metricas=("auc_roc", "auc_pr", "f1", "recall_negativos")
) -> pd.DataFrame:
    """Media e desvio por conjunto (treino x validacao), para ler o gap de overfitting."""
    g = tabela.groupby("conjunto")[list(metricas)]
    out = pd.concat({"media": g.mean(), "desvio": g.std()}, axis=1)
    return out.round(4)


def backtest_temporal(
    pipeline: Pipeline,
    x_treino: pd.DataFrame,
    y_treino: pd.Series,
    x_teste: pd.DataFrame,
    y_teste: pd.Series,
    sample_weight_treino: np.ndarray | None = None,
    sample_weight_teste: np.ndarray | None = None,
    limiar: float = 0.5,
) -> tuple[dict, np.ndarray]:
    """Treina em um ano e avalia no seguinte (walk-forward de um passo)."""
    modelo = clone(pipeline)
    fit_params = {}
    if sample_weight_treino is not None:
        fit_params["modelo__sample_weight"] = sample_weight_treino
    modelo.fit(x_treino, y_treino, **fit_params)
    proba = modelo.predict_proba(x_teste)[:, 1]
    return avaliar_classificacao(np.asarray(y_teste), proba, limiar, sample_weight_teste), proba


def curva_de_aprendizado(
    pipeline: Pipeline,
    x: pd.DataFrame,
    y: pd.Series,
    grupos: pd.Series,
    fracoes=(0.1, 0.25, 0.5, 0.75, 1.0),
    n_splits: int = 5,
    scoring: str = "roc_auc",
    n_jobs: int = -1,
) -> pd.DataFrame:
    """Curva de aprendizado com validacao por grupos, para diagnosticar viés e variância."""
    tamanhos, treino, validacao = learning_curve(
        pipeline,
        x,
        y,
        groups=grupos,
        cv=cv_por_municipio(n_splits),
        train_sizes=list(fracoes),
        scoring=scoring,
        n_jobs=n_jobs,
        shuffle=False,
    )
    return pd.DataFrame(
        {
            "tamanho": tamanhos,
            "treino_media": treino.mean(axis=1),
            "treino_desvio": treino.std(axis=1),
            "validacao_media": validacao.mean(axis=1),
            "validacao_desvio": validacao.std(axis=1),
        }
    )


def validar_regressao_por_grupos(
    pipeline: Pipeline,
    x: pd.DataFrame,
    y: pd.Series,
    grupos: pd.Series,
    n_splits: int = 5,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Versao para alvo continuo; devolve as metricas por fold e a predicao fora da amostra."""
    y = np.asarray(y, dtype=float)
    oof = np.full(len(y), np.nan)
    linhas = []
    for k, (tr, va) in enumerate(cv_por_municipio_regressao(n_splits).split(x, y, grupos)):
        modelo = clone(pipeline)
        modelo.fit(x.iloc[tr], y[tr])
        p_tr, p_va = modelo.predict(x.iloc[tr]), modelo.predict(x.iloc[va])
        oof[va] = p_va
        linhas.append({"fold": k, "conjunto": "treino", **avaliar_regressao(y[tr], p_tr)})
        linhas.append({"fold": k, "conjunto": "validacao", **avaliar_regressao(y[va], p_va)})
    return pd.DataFrame(linhas), oof
