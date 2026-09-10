"""Divisoes de treino, validacao e teste sem vazamento.

Duas regras:
- o teste e temporal: o modelo aprende com um ano e e avaliado no ano seguinte,
  que so e aberto uma vez, no fim;
- a validacao cruzada dentro do ano de treino separa municipios inteiros
  (StratifiedGroupKFold), para que o mesmo municipio nunca esteja dos dois lados.
"""

from __future__ import annotations

import pandas as pd
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold

SEED = 42


def split_temporal(
    df: pd.DataFrame, ano_treino: int, ano_teste: int, coluna_ano: str = "ano"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    treino = df[df[coluna_ano] == ano_treino].copy()
    teste = df[df[coluna_ano] == ano_teste].copy()
    return treino, teste


def cv_por_municipio(n_splits: int = 5) -> StratifiedGroupKFold:
    return StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)


def cv_por_municipio_regressao(n_splits: int = 5) -> GroupKFold:
    """Versao para alvo continuo (nao ha o que estratificar)."""
    return GroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)


def amostra_estratificada(df: pd.DataFrame, n: int, alvo: str, seed: int = SEED) -> pd.DataFrame:
    """Amostra que preserva a proporcao do alvo; usada para a busca de
    hiperparametros do modelo de aluno, que tem milhoes de linhas."""
    if n >= len(df):
        return df
    frac = n / len(df)
    amostra = (
        df.groupby(alvo, group_keys=False)
        .apply(lambda g: g.sample(frac=frac, random_state=seed), include_groups=False)
        .pipe(lambda idx: df.loc[idx.index])
    )
    # embaralha: o groupby deixa as classes em blocos, o que atrapalha a curva de aprendizado
    return amostra.sample(frac=1, random_state=seed)
