"""Gate de vazamento sobre as bases analiticas versionadas.

Nenhuma variavel isolada pode ordenar o alvo quase perfeitamente (AUC acima de
0,90) e a ausencia de nenhuma variavel pode prediz-lo (AUC acima de 0,60): as
duas situacoes sao a assinatura de uma coluna derivada do proprio alvo ou de um
atalho de coleta. O teste roda sobre as ABTs de data/processed e falha se uma
coluna nova cair em um desses casos.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from src.data.abt import carregar_abt_aluno
from src.evaluation.metricas import auc_da_ausencia
from src.preprocessing.features import colunas, grupos_aluno, grupos_municipio, preparar_xy

PROCESSED = Path("data/processed")
LIMITE_VARIAVEL = 0.90
LIMITE_AUSENCIA = 0.60


def _auc_isolado(x: pd.DataFrame, y: np.ndarray) -> pd.Series:
    out = {}
    for c in x.columns:
        if not pd.api.types.is_numeric_dtype(x[c]):
            continue
        v = x[c].to_numpy(dtype=float)
        ok = ~np.isnan(v)
        if ok.sum() < 100 or len(np.unique(y[ok])) < 2 or np.nanstd(v) == 0:
            continue
        auc = roc_auc_score(y[ok], v[ok])
        out[c] = max(auc, 1 - auc)
    return pd.Series(out).sort_values(ascending=False)


@pytest.mark.skipif(not (PROCESSED / "abt_municipio.parquet").exists(), reason="ABT nao gerada")
def test_nenhuma_variavel_municipal_isola_o_alvo():
    abt = pd.read_parquet(PROCESSED / "abt_municipio.parquet")
    abt = abt[abt["atingiu_meta_t"].notna()]
    grupos = grupos_municipio()
    assert "indicador_t" not in colunas(grupos)
    x, y = preparar_xy(abt, grupos, "atingiu_meta_t")
    aucs = _auc_isolado(x, y.to_numpy())
    suspeitas = aucs[aucs > LIMITE_VARIAVEL]
    assert suspeitas.empty, f"variaveis que isolam o alvo: {suspeitas.to_dict()}"
    ausencia = auc_da_ausencia(x, y)
    if not ausencia.empty:
        assert ausencia["auc_ausencia"].max() < LIMITE_AUSENCIA, ausencia.head(3).to_dict()


@pytest.mark.skipif(not (PROCESSED / "abt_aluno.parquet").exists(), reason="ABT nao gerada")
def test_nenhuma_variavel_do_aluno_isola_o_alvo():
    alunos = carregar_abt_aluno()
    amostra = alunos.sample(n=min(200_000, len(alunos)), random_state=42)
    grupos = grupos_aluno()
    assert "proficiencia" not in colunas(grupos)
    x, y = preparar_xy(amostra, grupos, "alfabetizado")
    aucs = _auc_isolado(x, y.to_numpy())
    suspeitas = aucs[aucs > LIMITE_VARIAVEL]
    assert suspeitas.empty, f"variaveis que isolam o alvo: {suspeitas.to_dict()}"
    ausencia = auc_da_ausencia(x, y)
    if not ausencia.empty:
        assert ausencia["auc_ausencia"].max() < LIMITE_AUSENCIA, ausencia.head(3).to_dict()
