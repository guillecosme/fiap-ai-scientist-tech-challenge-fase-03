"""Treino: busca de hiperparametros, ajuste final e persistencia.

Uso pela linha de comando (o que `make train` roda):

    python -m src.modeling.train --alvo municipio
    python -m src.modeling.train --alvo aluno --amostra 300000

O fluxo e o mesmo dos notebooks 03 e 04: treino no ano de 2024 com validacao por
grupos de municipio, busca aleatoria de hiperparametros com AUC como criterio,
ajuste final no ano inteiro e avaliacao unica no ano de 2025. O modelo salvo e o
pipeline completo (preprocessamento + modelo), com um json de metadados ao lado.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import Pipeline

from src.data.abt import PROCESSED_DIR, carregar_abt_aluno
from src.evaluation.metricas import (
    avaliar_classificacao,
    avaliar_regressao,
    risco_de_nao_atingir,
)
from src.evaluation.validacao import validar_regressao_por_grupos
from src.modeling.modelos import criar_modelos, criar_regressores
from src.preprocessing.features import grupos_aluno, grupos_municipio, preparar_xy
from src.preprocessing.pipeline import build_pipeline
from src.preprocessing.splits import (
    SEED,
    amostra_estratificada,
    cv_por_municipio,
    cv_por_municipio_regressao,
)

MODELS_DIR = Path("models")


def buscar_hiperparametros(
    pipeline: Pipeline,
    distribuicoes: dict,
    x: pd.DataFrame,
    y: pd.Series,
    grupos: pd.Series,
    n_iter: int = 20,
    n_splits: int = 5,
    sample_weight: np.ndarray | None = None,
    scoring: str = "roc_auc",
    n_jobs: int = -1,
    regressao: bool = False,
) -> RandomizedSearchCV:
    """Busca aleatoria com validacao cruzada por grupos de municipio."""
    cv = cv_por_municipio_regressao(n_splits) if regressao else cv_por_municipio(n_splits)
    busca = RandomizedSearchCV(
        pipeline,
        distribuicoes,
        n_iter=n_iter,
        scoring=scoring,
        cv=cv,
        random_state=SEED,
        n_jobs=n_jobs,
        refit=True,
        return_train_score=True,
    )
    fit_params = {}
    if sample_weight is not None:
        fit_params["modelo__sample_weight"] = sample_weight
    busca.fit(x, y, groups=grupos, **fit_params)
    return busca


def resumo_da_busca(busca: RandomizedSearchCV) -> pd.DataFrame:
    """Tabela com as combinacoes testadas, ordenada pela media na validacao."""
    r = pd.DataFrame(busca.cv_results_)
    cols = [c for c in r.columns if c.startswith("param_")]
    out = r[cols + ["mean_train_score", "mean_test_score", "std_test_score"]].copy()
    out.columns = [c.replace("param_modelo__", "") for c in out.columns]
    return out.sort_values("mean_test_score", ascending=False).reset_index(drop=True)


def salvar_modelo(
    pipeline: Pipeline, nome: str, metadados: dict, models_dir: Path = MODELS_DIR
) -> Path:
    models_dir.mkdir(parents=True, exist_ok=True)
    destino = models_dir / f"{nome}.joblib"
    joblib.dump(pipeline, destino, compress=3)
    meta = dict(metadados)
    meta["salvo_em"] = datetime.now(UTC).isoformat(timespec="seconds")
    (models_dir / f"{nome}.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, default=float) + "\n", encoding="utf-8"
    )
    return destino


def carregar_modelo(nome: str, models_dir: Path = MODELS_DIR) -> Pipeline:
    return joblib.load(models_dir / f"{nome}.joblib")


# ---------------------------------------------------------------------------
# Fluxos completos usados pela linha de comando
# ---------------------------------------------------------------------------


def treinar_municipio(n_iter: int = 20, modelo: str = "lightgbm") -> dict:
    """Modelo de risco municipal: regressao do nivel do indicador com o risco derivado
    da comparacao com a meta (ver notebook 04).

    1. busca de hiperparametros e backtest: treino em 2024, teste em 2025;
    2. ajuste final no retrato mais recente (linhas com alvo em 2025), com os
       residuos de uma validacao por grupos para derivar o risco.
    """
    abt = pd.read_parquet(PROCESSED_DIR / "abt_municipio.parquet")
    abt = abt[abt["atingiu_meta_t"].notna()].copy()
    grupos = grupos_municipio()
    treino, teste = abt[abt["ano_alvo"] == 2024], abt[abt["ano_alvo"] == 2025]
    x_tr, y_tr_cls = preparar_xy(treino, grupos, "atingiu_meta_t")
    x_te, y_te_cls = preparar_xy(teste, grupos, "atingiu_meta_t")
    y_tr, y_te = treino["indicador_t"].astype(float), teste["indicador_t"].astype(float)

    # base pequena: busca em paralelo, modelo em uma thread
    estimador, distribuicoes = criar_regressores(n_jobs=1)[modelo]
    busca = buscar_hiperparametros(
        build_pipeline(grupos, estimador),
        distribuicoes,
        x_tr,
        y_tr,
        treino["id_municipio"],
        n_iter=n_iter,
        n_jobs=-1,
        scoring="neg_mean_absolute_error",
        regressao=True,
    )
    _, oof_tr = validar_regressao_por_grupos(
        busca.best_estimator_, x_tr, y_tr, treino["id_municipio"].values
    )
    residuos_tr = y_tr.values - oof_tr
    pred_te = busca.best_estimator_.predict(x_te)
    risco_te = risco_de_nao_atingir(pred_te, teste["meta_t"].values, residuos_tr)
    backtest = avaliar_regressao(y_te.values, pred_te)
    backtest["auc_risco_teste_2025"] = float(roc_auc_score(y_te_cls, 1 - risco_te))

    # ajuste final no retrato mais recente
    hiper = {k.replace("modelo__", ""): v for k, v in busca.best_params_.items()}
    final = build_pipeline(grupos, clone(estimador).set_params(**hiper))
    _, oof_te = validar_regressao_por_grupos(final, x_te, y_te, teste["id_municipio"].values)
    final.fit(x_te, y_te)
    salvar_modelo(
        final,
        "modelo_municipio",
        {
            "alvo_modelado": "indicador_t",
            "alvo_operacional": "risco de nao atingir a meta, derivado dos residuos",
            "modelo": modelo,
            "hiperparametros": hiper,
            "backtest_2024_para_2025": backtest,
            "treino_final": "linhas com alvo em 2025",
            "residuos_validacao": [float(r) for r in (y_te.values - oof_te)],
            "features": grupos,
        },
    )
    print(
        f"[treino] municipio ({modelo}): MAE 2025 {backtest['mae']:.2f} p.p. "
        f"| AUC do risco 2025 {backtest['auc_risco_teste_2025']:.3f}"
    )
    return backtest


def treinar_aluno(n_iter: int = 10, amostra: int = 300_000, modelo: str = "lightgbm") -> dict:
    alunos = carregar_abt_aluno()
    grupos = grupos_aluno()
    treino, teste = alunos[alunos["ano"] == 2024], alunos[alunos["ano"] == 2025]
    busca_df = amostra_estratificada(treino, amostra, "alfabetizado")
    x_b, y_b = preparar_xy(busca_df, grupos, "alfabetizado")

    # base grande: busca sequencial, modelo com todas as threads
    estimador, distribuicoes = criar_modelos(n_jobs=-1)[modelo]
    pipeline = build_pipeline(grupos, estimador)
    busca = buscar_hiperparametros(
        pipeline,
        distribuicoes,
        x_b,
        y_b,
        busca_df["id_municipio"],
        n_iter=n_iter,
        n_splits=3,
        sample_weight=busca_df["peso"].values,
        n_jobs=1,
    )
    x_tr, y_tr = preparar_xy(treino, grupos, "alfabetizado")
    final = build_pipeline(
        grupos,
        estimador.set_params(
            **{k.replace("modelo__", ""): v for k, v in busca.best_params_.items()}
        ),
    )
    final.fit(x_tr, y_tr, modelo__sample_weight=treino["peso"].values)

    x_te, y_te = preparar_xy(teste, grupos, "alfabetizado")
    proba = final.predict_proba(x_te)[:, 1]
    metricas = avaliar_classificacao(y_te.values, proba, sample_weight=teste["peso"].values)
    salvar_modelo(
        final,
        "modelo_aluno",
        {
            "alvo": "alfabetizado",
            "modelo": modelo,
            "melhores_hiperparametros": busca.best_params_,
            "auc_validacao_amostra": float(busca.best_score_),
            "metricas_teste_2025": metricas,
            "features": grupos,
        },
    )
    print(
        f"[treino] aluno ({modelo}): AUC validacao {busca.best_score_:.3f} "
        f"| teste 2025 {metricas['auc_roc']:.3f}"
    )
    return metricas


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina e persiste os modelos")
    parser.add_argument("--alvo", choices=["municipio", "aluno", "todos"], default="todos")
    parser.add_argument("--modelo", default="lightgbm")
    parser.add_argument("--n-iter", type=int, default=20)
    parser.add_argument("--amostra", type=int, default=300_000)
    args = parser.parse_args()
    if args.alvo in ("municipio", "todos"):
        treinar_municipio(n_iter=args.n_iter, modelo=args.modelo)
    if args.alvo in ("aluno", "todos"):
        treinar_aluno(n_iter=max(5, args.n_iter // 2), amostra=args.amostra, modelo=args.modelo)


if __name__ == "__main__":
    main()
