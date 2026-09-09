"""Testes do preprocessamento integrado, das metricas e da validacao."""

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from src.evaluation import metricas, validacao
from src.preprocessing import features
from src.preprocessing.pipeline import build_pipeline, build_preprocessor, nomes_das_features

GRUPOS = {
    "historico": ["indicador_t1"],
    "log": ["populacao"],
    "numericas": ["distorcao_ai_pct"],
    "categoricas": ["sigla_uf"],
}


def _base(n=200, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "indicador_t1": rng.uniform(20, 90, n),
            "populacao": rng.lognormal(9, 1.2, n).round(),
            "distorcao_ai_pct": rng.uniform(0, 30, n),
            "sigla_uf": rng.choice(["CE", "BA", "SP"], n),
            "id_municipio": np.arange(n) // 4,  # quatro linhas por municipio
        }
    )
    df.loc[:9, "indicador_t1"] = np.nan  # historico ausente em alguns
    df.loc[10:14, "populacao"] = np.nan
    logit = 0.08 * (df["indicador_t1"].fillna(55) - 55) - 0.05 * df["distorcao_ai_pct"]
    df["alvo"] = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    return df


def test_preprocessador_imputa_transforma_e_nomeia():
    df = _base()
    prep = build_preprocessor(GRUPOS)
    xt = prep.fit_transform(df)
    nomes = list(prep.get_feature_names_out())

    assert not np.isnan(xt).any()  # nada de NaN depois da imputacao
    assert "missingindicator_indicador_t1" in nomes  # indicador de ausencia do historico
    assert {"sigla_uf_BA", "sigla_uf_CE", "sigla_uf_SP"} <= set(nomes)
    # log1p aplicado: a coluna de populacao escalonada tem assimetria bem menor que a original
    col = nomes.index("populacao")
    assert abs(pd.Series(xt[:, col]).skew()) < abs(df["populacao"].skew())


def test_categoria_desconhecida_nao_quebra_o_pipeline():
    df = _base()
    pipe = build_pipeline(GRUPOS, LogisticRegression(max_iter=500))
    pipe.fit(df, df["alvo"])
    novo = df.head(3).copy()
    novo["sigla_uf"] = "RR"  # UF que nao estava no treino
    proba = pipe.predict_proba(novo)[:, 1]
    assert proba.shape == (3,)
    assert np.all((proba >= 0) & (proba <= 1))


def test_nomes_das_features_traduzem_indicador_de_ausencia():
    df = _base()
    pipe = build_pipeline(GRUPOS, LogisticRegression(max_iter=500)).fit(df, df["alvo"])
    nomes = nomes_das_features(pipe)
    assert "ausente_indicador_t1" in nomes
    assert not any(n.startswith("missingindicator_") for n in nomes)


def test_preparar_xy_exige_colunas_e_converte_alvo():
    df = _base()
    x, y = features.preparar_xy(df, GRUPOS, "alvo")
    assert list(x.columns) == features.colunas(GRUPOS)
    assert y.dtype == int
    with pytest.raises(KeyError):
        features.preparar_xy(df.drop(columns="populacao"), GRUPOS, "alvo")


def test_listas_de_features_nao_contem_alvo_nem_colunas_futuras():
    proibidas = {
        "indicador_t", "atingiu_meta_t", "gap_meta_t", "nivel_t1", "meta_t", "indicador_t2",
        "variacao_t1", "meta_t1", "gap_meta_t1", "proficiencia", "alfabetizado",
    }
    for grupos in (features.grupos_municipio(), features.grupos_aluno()):
        assert proibidas.isdisjoint(features.colunas(grupos))


def test_metricas_em_caso_conhecido():
    y = np.array([0, 0, 1, 1, 1, 0])
    proba = np.array([0.1, 0.6, 0.8, 0.4, 0.9, 0.2])
    m = metricas.avaliar_classificacao(y, proba, limiar=0.5)
    # previstos: 0,1,1,0,1,0 -> tp=2, fp=1, fn=1, tn=2
    assert m["acuracia"] == pytest.approx(4 / 6)
    assert m["precisao"] == pytest.approx(2 / 3)
    assert m["recall"] == pytest.approx(2 / 3)
    assert m["recall_negativos"] == pytest.approx(2 / 3)
    assert m["taxa_base"] == pytest.approx(0.5)
    assert 0 < m["auc_roc"] <= 1


def test_limiar_por_recall_negativos_sobe_quando_exige_mais():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 500)
    proba = np.clip(0.5 * y + rng.normal(0.25, 0.2, 500), 0, 1)
    t_baixo = metricas.limiar_por_recall_negativos(y, proba, 0.6)
    t_alto = metricas.limiar_por_recall_negativos(y, proba, 0.9)
    assert t_alto >= t_baixo
    m = metricas.avaliar_classificacao(y, proba, t_alto)
    assert m["recall_negativos"] >= 0.9


def test_validacao_por_grupos_nao_mistura_municipios():
    df = _base(400)
    pipe = build_pipeline(GRUPOS, LogisticRegression(max_iter=500))
    x, y = features.preparar_xy(df, GRUPOS, "alvo")
    tabela, oof = validacao.validar_por_grupos(pipe, x, y, df["id_municipio"], n_splits=4)
    assert set(tabela["conjunto"]) == {"treino", "validacao"}
    assert len(tabela) == 8
    assert not np.isnan(oof).any()  # toda linha recebe uma probabilidade fora da amostra
    resumo = validacao.resumir_folds(tabela)
    assert ("media", "auc_roc") in resumo.columns


def test_risco_derivado_do_nivel_cresce_com_a_folga_para_a_meta():
    residuos = np.array([-4.0, -2.0, 0.0, 2.0, 4.0])
    pred = np.array([60.0, 60.0, 60.0, np.nan])
    meta = np.array([56.0, 60.0, 65.0, 60.0])
    risco = metricas.risco_de_nao_atingir(pred, meta, residuos)
    assert risco[0] < risco[1] < risco[2]
    assert risco[2] == 1.0  # meta 5 pontos acima do previsto: todos os residuos ficam abaixo
    assert np.isnan(risco[3])


def test_metricas_de_regressao():
    y = np.array([50.0, 60.0, 70.0, 80.0])
    pred = np.array([52.0, 58.0, 71.0, 79.0])
    m = metricas.avaliar_regressao(y, pred)
    assert m["mae"] == pytest.approx(1.5)
    assert m["vies"] == pytest.approx(0.0)
    assert m["spearman"] == pytest.approx(1.0)
    assert m["r2"] > 0.95
