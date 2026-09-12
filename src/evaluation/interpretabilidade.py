"""Interpretabilidade: importancia de variaveis e SHAP sobre o pipeline completo.

O SHAP e calculado no espaco transformado (depois do preprocessamento), com os
nomes de coluna do ColumnTransformer traduzidos para rotulos de negocio. Para
arvores usa-se o TreeExplainer (exato e rapido); para a regressao logistica, o
LinearExplainer.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline

from src.preprocessing.pipeline import nomes_das_features
from src.visualization.rotulos import rotulo


def rotulo_transformado(nome: str) -> str:
    """Rotulo de negocio para uma coluna pos-preprocessamento."""
    if nome.startswith("ausente_"):
        return f"Sem informação: {rotulo(nome[len('ausente_') :])}"
    for prefixo in ("sigla_uf_", "rede_"):
        if nome.startswith(prefixo):
            base = prefixo[:-1]
            return f"{rotulo(base)}: {nome[len(prefixo) :]}"
    return rotulo(nome)


def matriz_transformada(pipeline: Pipeline, x: pd.DataFrame) -> pd.DataFrame:
    prep = pipeline.named_steps["prep"]
    valores = prep.transform(x)
    return pd.DataFrame(valores, columns=nomes_das_features(pipeline), index=x.index)


def explicar(pipeline: Pipeline, x: pd.DataFrame, max_amostras: int = 5000, seed: int = 42):
    """Valores SHAP (classe positiva) para uma amostra de x.

    Devolve (explicacao shap, DataFrame transformado usado), ja com rotulos de
    negocio nos nomes das colunas.
    """
    if len(x) > max_amostras:
        x = x.sample(max_amostras, random_state=seed)
    xt = matriz_transformada(pipeline, x)
    modelo = pipeline.named_steps["modelo"]
    nome_modelo = type(modelo).__name__
    if nome_modelo == "LogisticRegression":
        explainer = shap.LinearExplainer(modelo, xt)
        valores = explainer(xt)
    else:
        explainer = shap.TreeExplainer(modelo)
        valores = explainer(xt)
        # para classificadores binarios de arvore, alguns backends devolvem as duas classes
        if valores.values.ndim == 3:
            valores = valores[:, :, 1]
    valores.feature_names = [rotulo_transformado(c) for c in xt.columns]
    xt.columns = valores.feature_names
    return valores, xt


def importancia_shap(valores) -> pd.DataFrame:
    """Importancia global: media do valor absoluto do SHAP por variavel."""
    media = np.abs(valores.values).mean(axis=0)
    return (
        pd.DataFrame({"variavel": valores.feature_names, "importancia_shap": media})
        .sort_values("importancia_shap", ascending=False)
        .reset_index(drop=True)
    )


def importancia_por_grupo(importancias: pd.DataFrame, grupos: dict[str, list[str]]) -> pd.DataFrame:
    """Soma a importancia por bloco de variaveis (historico, censo, ideb, ...)."""
    mapa = {}
    for grupo, nomes in grupos.items():
        for n in nomes:
            mapa[rotulo(n)] = grupo

    def bloco(v):
        if v.startswith("UF:") or v.startswith("Rede de ensino:"):
            return "territorio (UF) e rede"
        if v.startswith("Sem informação: "):
            return mapa.get(v[len("Sem informação: ") :], "outros")
        return mapa.get(v, "outros")

    tab = importancias.assign(bloco=importancias["variavel"].map(bloco))
    out = tab.groupby("bloco")["importancia_shap"].sum().sort_values(ascending=False)
    return (100 * out / out.sum()).round(1).to_frame("% da importância")


def importancia_permutacao(
    pipeline: Pipeline,
    x: pd.DataFrame,
    y,
    n_repeats: int = 5,
    seed: int = 42,
    scoring: str = "roc_auc",
) -> pd.DataFrame:
    """Importancia por permutacao sobre as colunas originais (antes do preprocessamento)."""
    r = permutation_importance(
        pipeline, x, y, n_repeats=n_repeats, random_state=seed, scoring=scoring, n_jobs=-1
    )
    return (
        pd.DataFrame(
            {
                "variavel": [rotulo(c) for c in x.columns],
                "queda_auc": r.importances_mean,
                "desvio": r.importances_std,
            }
        )
        .sort_values("queda_auc", ascending=False)
        .reset_index(drop=True)
    )
