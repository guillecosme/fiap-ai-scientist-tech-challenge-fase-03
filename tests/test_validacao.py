import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline

from src.evaluation.metricas import auc_da_ausencia
from src.evaluation.validacao import (
    diferenca_bootstrap_pareada,
    embaralhar_dentro_de_grupos,
    predicao_por_uf_excluida,
)


def test_embaralhar_preserva_taxa_por_grupo_e_destroi_o_sinal():
    rng = np.random.default_rng(0)
    grupos = rng.integers(0, 30, 6000)
    x = rng.normal(size=6000)
    y = (x + rng.normal(size=6000) > 0).astype(int)
    y_emb = embaralhar_dentro_de_grupos(y, grupos, seed=0)
    for g in np.unique(grupos):
        assert y[grupos == g].sum() == y_emb[grupos == g].sum()
    assert roc_auc_score(y, x) > 0.7
    assert abs(roc_auc_score(y_emb, x) - 0.5) < 0.03


def test_predicao_por_uf_excluida_nunca_ve_a_propria_uf():
    uf = pd.Series(["A"] * 10 + ["B"] * 10 + ["C"] * 10)
    y = np.array([1.0] * 10 + [2.0] * 10 + [3.0] * 10)
    x = pd.DataFrame({"z": np.zeros(30)})
    pipe = Pipeline([("modelo", DummyRegressor(strategy="mean"))])
    pred = predicao_por_uf_excluida(pipe, x, y, uf, regressao=True)
    # a media das outras duas UFs, nunca a media da propria
    assert np.allclose(pred[:10], 2.5)
    assert np.allclose(pred[10:20], 2.0)
    assert np.allclose(pred[20:], 1.5)


def test_predicao_por_uf_excluida_classificacao_cobre_todas_as_linhas():
    rng = np.random.default_rng(1)
    uf = pd.Series(rng.choice(["A", "B", "C", "D"], 400))
    x = pd.DataFrame({"v": rng.normal(size=400)})
    y = (x["v"] + rng.normal(size=400) > 0).astype(int).to_numpy()
    pipe = Pipeline([("modelo", LogisticRegression())])
    pred = predicao_por_uf_excluida(pipe, x, y, uf)
    assert not np.isnan(pred).any()
    assert roc_auc_score(y, pred) > 0.6


def test_diferenca_pareada_contem_a_diferenca_e_detecta_ganho():
    rng = np.random.default_rng(2)
    n = 4000
    grupos = rng.integers(0, 80, n)
    y = rng.integers(0, 2, n)
    forte = np.clip(0.5 + 0.4 * (y - 0.5) + rng.normal(0, 0.3, n), 0, 1)
    fraco = np.clip(0.5 + 0.1 * (y - 0.5) + rng.normal(0, 0.3, n), 0, 1)
    d = diferenca_bootstrap_pareada(y, forte, fraco, grupos, roc_auc_score, n_reamostras=60, seed=2)
    assert d["ic_inferior"] <= d["diferenca"] <= d["ic_superior"]
    assert d["ic_inferior"] > 0


def test_auc_da_ausencia_identifica_atalho():
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 2000)
    x = pd.DataFrame(
        {"neutra": rng.normal(size=2000), "atalho": rng.normal(size=2000), "cheia": np.ones(2000)}
    )
    x.loc[rng.random(2000) < 0.1, "neutra"] = np.nan
    x.loc[(y == 0) & (rng.random(2000) < 0.5), "atalho"] = np.nan
    tabela = auc_da_ausencia(x, y)
    assert tabela.iloc[0]["variavel"] == "atalho"
    assert tabela.iloc[0]["auc_ausencia"] > 0.6
    assert "cheia" not in set(tabela["variavel"])
    assert abs(tabela.set_index("variavel").loc["neutra", "auc_ausencia"] - 0.5) < 0.05
