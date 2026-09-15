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


# ---------------------------------------------------------------------------
# Falsificacao e extrapolacao
# ---------------------------------------------------------------------------


def embaralhar_dentro_de_grupos(y, grupos, seed: int = 42) -> np.ndarray:
    """Permuta o alvo dentro de cada grupo (municipio). Mantem a taxa de cada
    grupo e destroi a relacao entre o alvo e as variaveis de cada linha; um
    modelo que ainda acerta esta lendo a estrutura dos grupos, nao o dado."""
    y = np.asarray(y)
    grupos = np.asarray(grupos)
    rng = np.random.default_rng(seed)
    saida = y.copy()
    for g in np.unique(grupos):
        idx = np.flatnonzero(grupos == g)
        saida[idx] = y[rng.permutation(idx)]
    return saida


def predicao_por_uf_excluida(
    pipeline: Pipeline,
    x: pd.DataFrame,
    y,
    uf: pd.Series,
    sample_weight: np.ndarray | None = None,
    regressao: bool = False,
) -> np.ndarray:
    """Leave-one-UF-out: para cada UF, ajusta o pipeline nas demais e prediz a
    excluida. A categoria da UF excluida nao existe no one-hot do treino, entao
    o modelo a ve como desconhecida (todas as dummies zeradas). Devolve a
    predicao de cada linha feita por um modelo que nunca viu a sua UF."""
    y = np.asarray(y)
    uf = np.asarray(uf)
    saida = np.full(len(y), np.nan)
    for sigla in np.unique(uf):
        tr, va = np.flatnonzero(uf != sigla), np.flatnonzero(uf == sigla)
        modelo = clone(pipeline)
        fit_params = {}
        if sample_weight is not None:
            fit_params["modelo__sample_weight"] = sample_weight[tr]
        modelo.fit(x.iloc[tr], y[tr], **fit_params)
        if regressao:
            saida[va] = modelo.predict(x.iloc[va])
        else:
            saida[va] = modelo.predict_proba(x.iloc[va])[:, 1]
    return saida


def diferenca_bootstrap_pareada(
    y,
    score_a,
    score_b,
    grupos,
    metrica,
    n_reamostras: int = 200,
    sample_weight=None,
    seed: int = 42,
    nivel: float = 0.95,
) -> dict[str, float]:
    """IC da diferenca metrica(a) - metrica(b) por bootstrap de grupos, com a
    mesma reamostra aplicada aos dois scores (pareado). Se o intervalo nao
    contem zero, a diferenca e maior do que o ruido amostral."""
    y = np.asarray(y)
    a = np.asarray(score_a)
    b = np.asarray(score_b)
    grupos = np.asarray(grupos)
    w = None if sample_weight is None else np.asarray(sample_weight)
    codigos, inverso = np.unique(grupos, return_inverse=True)
    por_grupo = [np.flatnonzero(inverso == g) for g in range(len(codigos))]
    rng = np.random.default_rng(seed)

    def m(idx, s):
        kw = {} if w is None else {"sample_weight": w[idx]}
        return metrica(y[idx], s[idx], **kw)

    todos = np.arange(len(y))
    difs = []
    for _ in range(n_reamostras):
        idx = np.concatenate([por_grupo[g] for g in rng.integers(0, len(codigos), len(codigos))])
        difs.append(m(idx, a) - m(idx, b))
    difs = np.asarray(difs)
    alfa = (1 - nivel) / 2
    return {
        "metrica_a": float(m(todos, a)),
        "metrica_b": float(m(todos, b)),
        "diferenca": float(m(todos, a) - m(todos, b)),
        "ic_inferior": float(np.quantile(difs, alfa)),
        "ic_superior": float(np.quantile(difs, 1 - alfa)),
        "n_reamostras": int(n_reamostras),
    }
