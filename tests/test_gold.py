"""Testes das regras de montagem da Gold com dados pequenos em memoria."""

import numpy as np
import pandas as pd
import pytest

from src.data import gold


def _alunos():
    # dois municipios, rede municipal; o segundo tem um ausente e pesos diferentes
    return pd.DataFrame(
        {
            "ano": [2024] * 5,
            "sigla_uf": ["RO"] * 5,
            "id_aluno": [1, 2, 3, 4, 5],
            "id_escola": [10, 10, 20, 20, 20],
            "rede": ["municipal"] * 5,
            "id_municipio": [1100015, 1100015, 1100023, 1100023, 1100023],
            "presente": [1, 1, 1, 1, 0],
            "preencheu": [1, 1, 1, 1, 0],
            "peso": [1.0, 1.0, 3.0, 1.0, np.nan],
            "proficiencia": [760.0, 700.0, 750.0, 730.0, np.nan],
            "alfabetizado": [1, 0, 1, 0, 0],
        }
    )


def test_agregacao_reproduz_percentual_ponderado_e_ignora_ausentes():
    g = gold._agregar_alunos(_alunos(), ["ano", "id_municipio", "rede"]).set_index("id_municipio")

    assert g.loc[1100015, "qtd_avaliados"] == 2
    assert g.loc[1100015, "indicador_pct"] == pytest.approx(50.0)
    # municipio 2: pesos 3 e 1, so o de peso 3 e alfabetizado -> 75% ponderado, 50% bruto
    assert g.loc[1100023, "qtd_avaliados"] == 2  # o ausente fica fora do denominador
    assert g.loc[1100023, "indicador_pct"] == pytest.approx(75.0)
    assert g.loc[1100023, "indicador_pct_bruto"] == pytest.approx(50.0)
    assert g.loc[1100023, "media_proficiencia"] == pytest.approx(745.0)


def test_fato_alfabetizacao_compara_com_a_meta():
    dim = pd.DataFrame(
        {
            "id_municipio": [1100015, 1100023],
            "nome_municipio": ["A", "B"],
            "sigla_uf": ["RO", "RO"],
            "id_uf": [11, 11],
            "nome_uf": ["Rondônia"] * 2,
            "nome_regiao": ["Norte"] * 2,
        }
    )
    metas = pd.DataFrame(
        {
            "id_municipio": [1100015, 1100023],
            "ano": [2024, 2025],
            "meta_pct": [60.0, 70.0],
            "ano_planilha": [2023, 2023],
        }
    )
    fato = gold.build_fato_alfabetizacao(_alunos(), dim, metas).set_index("id_municipio")

    assert not fato.loc[1100015, "atingiu_meta"]
    assert fato.loc[1100015, "gap_meta_pp"] == pytest.approx(-10.0)
    # meta do municipio 2 e de 2025, nao de 2024: sem meta, sem comparacao
    assert pd.isna(fato.loc[1100023, "meta_municipio"])
    assert pd.isna(fato.loc[1100023, "atingiu_meta"])


def test_evolucao_temporal_usa_o_ano_anterior_do_mesmo_municipio():
    indicador = pd.DataFrame(
        {
            "ano": [2023, 2024, 2025, 2024],
            "id_municipio": [1, 1, 1, 2],
            "nome_municipio": ["A", "A", "A", "B"],
            "sigla_uf": ["RO"] * 4,
            "nome_regiao": ["Norte"] * 4,
            "indicador_pct": [60.0, 65.0, 62.0, 50.0],
        }
    )
    ev = gold.build_evolucao_temporal(indicador).set_index(["id_municipio", "ano"])

    assert pd.isna(ev.loc[(1, 2023), "indicador_ano_anterior"])
    assert ev.loc[(1, 2024), "variacao_pp"] == pytest.approx(5.0)
    assert ev.loc[(1, 2025), "variacao_pp"] == pytest.approx(-3.0)
    assert pd.isna(ev.loc[(2, 2024), "variacao_pp"])


def test_regiao_derivada_do_codigo_da_uf():
    assert gold.REGIAO_POR_DIGITO[1100015 // 100000 // 10] == "Norte"
    assert gold.REGIAO_POR_DIGITO[2927408 // 100000 // 10] == "Nordeste"
    assert gold.REGIAO_POR_DIGITO[5300108 // 100000 // 10] == "Centro-Oeste"
