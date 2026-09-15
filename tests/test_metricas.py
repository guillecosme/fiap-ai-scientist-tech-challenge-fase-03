import numpy as np
from sklearn.metrics import roc_auc_score

from src.evaluation.metricas import brier, curva_calibracao, ic_bootstrap, ks


def test_brier_limites():
    y = np.array([0, 1, 1, 0])
    assert brier(y, y) == 0.0
    assert brier(y, np.full(4, 0.5)) == 0.25


def test_ks_separacao_perfeita_e_nula():
    y = np.array([0, 0, 1, 1])
    assert ks(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert ks(y, np.array([0.5, 0.5, 0.5, 0.5])) == 0.0


def test_curva_calibracao_recupera_frequencias():
    rng = np.random.default_rng(0)
    proba = rng.uniform(0, 1, 20000)
    y = (rng.uniform(0, 1, 20000) < proba).astype(int)
    curva = curva_calibracao(y, proba, n_faixas=5)
    assert len(curva) == 5
    assert np.allclose(curva["prevista"], curva["observada"], atol=0.03)


def test_ic_bootstrap_contem_estimativa_e_respeita_grupos():
    rng = np.random.default_rng(1)
    n = 3000
    grupos = rng.integers(0, 60, n)
    y = rng.integers(0, 2, n)
    proba = np.clip(0.5 + 0.3 * (y - 0.5) + rng.normal(0, 0.3, n), 0, 1)
    ic = ic_bootstrap(y, proba, grupos, roc_auc_score, n_reamostras=50, seed=1)
    assert ic["ic_inferior"] <= ic["estimativa"] <= ic["ic_superior"]
    assert ic["ic_superior"] - ic["ic_inferior"] < 0.15
