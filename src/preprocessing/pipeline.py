"""Preprocessamento integrado ao modelo.

Um unico ColumnTransformer com quatro ramos, todos ajustados apenas no treino
(o Pipeline do scikit-learn garante isso dentro da validacao cruzada):

    historico    mediana + indicador de ausencia + escalonamento
    log          mediana + log1p + escalonamento (porte e renda, muito assimetricas)
    numericas    mediana + escalonamento
    categoricas  one-hot, ignorando categorias nao vistas no treino

O escalonamento nao faz diferenca para arvores, mas e necessario para a regressao
logistica; manter um preprocessador unico simplifica a comparacao entre modelos e
a leitura do SHAP, que recebe os mesmos nomes de coluna em todos os casos.
"""

from __future__ import annotations

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler


def _log1p_seguro(x):
    # valores negativos nao existem nessas variaveis, mas a protecao evita NaN
    return np.log1p(np.clip(x, 0, None))


def build_preprocessor(grupos: dict[str, list[str]], escalonar: bool = True) -> ColumnTransformer:
    """Monta o ColumnTransformer a partir dos grupos de colunas.

    `grupos` tem as chaves historico, log, numericas e categoricas (qualquer uma
    pode ser uma lista vazia).
    """

    def escala():
        return StandardScaler() if escalonar else "passthrough"

    ramos = []
    if grupos.get("historico"):
        ramos.append(
            (
                "historico",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                        ("scaler", escala()),
                    ]
                ),
                grupos["historico"],
            )
        )
    if grupos.get("log"):
        ramos.append(
            (
                "log",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        (
                            "log1p",
                            FunctionTransformer(_log1p_seguro, feature_names_out="one-to-one"),
                        ),
                        ("scaler", escala()),
                    ]
                ),
                grupos["log"],
            )
        )
    if grupos.get("numericas"):
        ramos.append(
            (
                "num",
                Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", escala())]),
                grupos["numericas"],
            )
        )
    if grupos.get("categoricas"):
        ramos.append(
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=np.float32),
                grupos["categoricas"],
            )
        )
    return ColumnTransformer(ramos, remainder="drop", verbose_feature_names_out=False)


def build_pipeline(grupos: dict[str, list[str]], modelo, escalonar: bool = True) -> Pipeline:
    """Preprocessador + modelo em um unico objeto, o que vai para producao."""
    return Pipeline([("prep", build_preprocessor(grupos, escalonar)), ("modelo", modelo)])


def nomes_das_features(pipeline: Pipeline) -> list[str]:
    """Nomes das colunas depois do preprocessamento (indicadores de ausencia e
    one-hot incluidos), para importancias e SHAP."""
    nomes = list(pipeline.named_steps["prep"].get_feature_names_out())
    # o SimpleImputer nomeia os indicadores como missingindicator_<coluna>
    return [n.replace("missingindicator_", "ausente_") for n in nomes]
