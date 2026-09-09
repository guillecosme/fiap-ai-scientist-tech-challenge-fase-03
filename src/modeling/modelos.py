"""Familias de modelos e espacos de busca de hiperparametros.

Tres familias, das aulas de modelos supervisionados e de otimizacao:
- regressao logistica com regularizacao L2 (baseline interpretavel);
- random forest (bagging de arvores);
- gradient boosting (LightGBM), que costuma ser o melhor em dados tabulares.

Os espacos de busca sao os hiperparametros que as aulas apontam como prioritarios
para cada familia. A busca e aleatoria (RandomizedSearchCV), que explora melhor o
espaco do que a grade para o mesmo custo.
"""

from __future__ import annotations

from lightgbm import LGBMClassifier, LGBMRegressor
from scipy.stats import loguniform, randint, uniform
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge

SEED = 42


def criar_modelos(n_jobs: int = 1) -> dict[str, tuple[object, dict]]:
    """Nome -> (estimador, distribuicoes de hiperparametros no namespace do pipeline).

    `n_jobs` e o paralelismo interno de cada modelo. Quando a busca de
    hiperparametros ja roda em paralelo (bases pequenas), o modelo fica em uma
    thread; em bases grandes faz-se o contrario. Paralelismo nos dois niveis ao
    mesmo tempo satura a maquina.
    """
    return {
        "logistica": (
            LogisticRegression(max_iter=2000, random_state=SEED),
            {"modelo__C": loguniform(1e-3, 10)},
        ),
        "random_forest": (
            RandomForestClassifier(n_estimators=300, n_jobs=n_jobs, random_state=SEED),
            {
                "modelo__max_depth": randint(4, 20),
                "modelo__min_samples_leaf": randint(5, 100),
                "modelo__max_features": uniform(0.2, 0.6),
            },
        ),
        "lightgbm": (
            LGBMClassifier(
                n_estimators=600,
                learning_rate=0.03,
                random_state=SEED,
                n_jobs=n_jobs,
                verbose=-1,
            ),
            {
                "modelo__num_leaves": randint(15, 96),
                "modelo__max_depth": randint(3, 12),
                "modelo__min_child_samples": randint(20, 300),
                "modelo__subsample": uniform(0.6, 0.4),
                "modelo__subsample_freq": [1],
                "modelo__colsample_bytree": uniform(0.5, 0.5),
                "modelo__reg_lambda": loguniform(1e-2, 10),
            },
        ),
    }


def criar_regressores(n_jobs: int = 1) -> dict[str, tuple[object, dict]]:
    """Mesmas familias, na versao de regressao, para o modelo do nivel do indicador."""
    return {
        "ridge": (
            Ridge(random_state=SEED),
            {"modelo__alpha": loguniform(1e-2, 100)},
        ),
        "random_forest": (
            RandomForestRegressor(n_estimators=300, n_jobs=n_jobs, random_state=SEED),
            {
                "modelo__max_depth": randint(4, 20),
                "modelo__min_samples_leaf": randint(5, 100),
                "modelo__max_features": uniform(0.2, 0.6),
            },
        ),
        "lightgbm": (
            LGBMRegressor(
                n_estimators=600,
                learning_rate=0.03,
                random_state=SEED,
                n_jobs=n_jobs,
                verbose=-1,
            ),
            {
                "modelo__num_leaves": randint(15, 96),
                "modelo__max_depth": randint(3, 12),
                "modelo__min_child_samples": randint(20, 300),
                "modelo__subsample": uniform(0.6, 0.4),
                "modelo__subsample_freq": [1],
                "modelo__colsample_bytree": uniform(0.5, 0.5),
                "modelo__reg_lambda": loguniform(1e-2, 10),
            },
        ),
    }
