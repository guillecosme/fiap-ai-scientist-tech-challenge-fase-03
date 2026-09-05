"""Testes do alinhamento temporal das bases analiticas e do leitor do SIDRA.

O ponto central e garantir que nenhuma variavel do ano-alvo (ou posterior) entra
como feature: e isso que evita data leakage na modelagem.
"""

# ruff: noqa: E501  (fixtures compactas)

import json

import numpy as np
import pandas as pd
import pytest

from src.data import abt, ibge


def test_ultima_edicao_respeita_o_ano_de_referencia():
    assert abt._ultima_edicao((2023, 2024), 2024) == 2024
    assert abt._ultima_edicao((2023, 2024), 2023) == 2023
    assert abt._ultima_edicao((2024, 2025), 2026) == 2025  # ainda nao publicado: ultima disponivel
    assert abt._ultima_edicao((2024, 2025), 2020) == 2024  # antes de tudo: a mais antiga


def _ideb():
    linhas = []
    for ano, valor in zip([2015, 2017, 2019, 2021, 2023, 2025], [4.0, 4.4, 4.8, 4.6, 5.2, 5.8], strict=True):
        linhas.append({"id_municipio": 1, "ano": ano, "ideb": valor, "nota_lp": 200.0 + ano - 2015, "nota_mt": np.nan, "rendimento": 0.9})
    return pd.DataFrame(linhas)


def test_bloco_ideb_so_usa_edicoes_anteriores_ao_ano_alvo():
    b2024 = abt.bloco_ideb(_ideb(), 2024).set_index("id_municipio")
    assert b2024.loc[1, "ref_ideb"] == 2023
    assert b2024.loc[1, "ideb_ultimo"] == pytest.approx(5.2)
    assert b2024.loc[1, "ideb_anterior"] == pytest.approx(4.6)
    assert b2024.loc[1, "ideb_variacao"] == pytest.approx(0.6)

    b2026 = abt.bloco_ideb(_ideb(), 2026).set_index("id_municipio")
    assert b2026.loc[1, "ref_ideb"] == 2025  # o IDEB 2025 ja e passado para o alvo 2026
    assert b2026.loc[1, "ideb_ultimo"] == pytest.approx(5.8)


def test_tendencia_do_ideb_e_a_inclinacao_por_edicao():
    # serie perfeitamente linear: +0.3 por edicao nas cinco ultimas (2015 a 2023)
    df = pd.DataFrame(
        {"id_municipio": 1, "ano": [2015, 2017, 2019, 2021, 2023], "ideb": [4.0, 4.3, 4.6, 4.9, 5.2],
         "nota_lp": np.nan, "nota_mt": np.nan, "rendimento": np.nan}
    )
    b = abt.bloco_ideb(df, 2024).set_index("id_municipio")
    assert b.loc[1, "ideb_tendencia"] == pytest.approx(0.3)


def _indicador():
    return pd.DataFrame(
        {
            "ano": [2023, 2024, 2025],
            "id_municipio": [1, 1, 1],
            "indicador_pct": [60.0, 65.0, 70.0],
            "nivel": [2, 3, 4],
            "participacao_pct": [88.0, 90.0, 92.0],
            "atingiu_meta": pd.array([None, True, True], dtype="boolean"),
            "gap_meta_pp": [np.nan, 2.0, 1.0],
        }
    )


def _metas():
    return pd.DataFrame({"id_municipio": 1, "ano": [2024, 2025, 2026], "meta_pct": [63.0, 69.0, 72.0]})


def test_bloco_indicador_usa_t_menos_1_como_feature_e_t_como_alvo():
    b = abt.bloco_indicador(_indicador(), _metas(), 2025).set_index("id_municipio")
    assert b.loc[1, "indicador_t1"] == pytest.approx(65.0)  # 2024
    assert b.loc[1, "indicador_t2"] == pytest.approx(60.0)  # 2023
    assert b.loc[1, "variacao_t1"] == pytest.approx(5.0)
    assert b.loc[1, "meta_t"] == pytest.approx(69.0)
    assert b.loc[1, "salto_necessario"] == pytest.approx(4.0)
    assert b.loc[1, "gap_meta_t1"] == pytest.approx(2.0)  # 65 - 63
    assert b.loc[1, "indicador_t"] == pytest.approx(70.0)  # alvo, 2025
    assert bool(b.loc[1, "atingiu_meta_t"]) is True


def test_bloco_indicador_no_ano_de_projecao_nao_tem_alvo():
    b = abt.bloco_indicador(_indicador(), _metas(), 2026).set_index("id_municipio")
    assert b.loc[1, "indicador_t1"] == pytest.approx(70.0)
    assert pd.isna(b.loc[1, "indicador_t"])
    assert pd.isna(b.loc[1, "atingiu_meta_t"])
    assert b.loc[1, "salto_necessario"] == pytest.approx(2.0)


def test_nenhuma_coluna_de_alvo_vaza_para_a_abt_de_aluno(tmp_path):
    alunos = pd.DataFrame(
        {"ano": [2024, 2025], "id_aluno": [1, 2], "id_municipio": [1, 1], "id_escola": [9, 9],
         "sigla_uf": ["RO", "RO"], "rede": ["municipal", "municipal"], "peso": [1.0, 1.0],
         "proficiencia": [750.0, 700.0], "escola_qtd_avaliados": [10, 12],
         "escola_taxa_presenca": [90.0, 95.0], "alfabetizado": [1, 0]}
    )
    municipio = pd.DataFrame(
        {"ano_alvo": [2024, 2025, 2026], "id_municipio": [1, 1, 1], "nome_municipio": "A",
         "sigla_uf": "RO", "nome_uf": "Rondônia", "nome_regiao": "Norte",
         "indicador_t1": [60.0, 65.0, 70.0], "indicador_t": [65.0, 70.0, np.nan],
         "atingiu_meta_t": pd.array([True, True, None], dtype="boolean"), "gap_meta_t": [2.0, 1.0, np.nan]}
    )
    alunos.to_parquet(tmp_path / "abt_aluno.parquet")
    municipio.to_parquet(tmp_path / "abt_municipio.parquet")

    completa = abt.carregar_abt_aluno(tmp_path)
    assert len(completa) == 2
    for coluna in abt.COLUNAS_ALVO:
        assert coluna not in completa.columns
    # o contexto municipal e o do mesmo ano da prova do aluno
    assert completa.set_index("ano").loc[2025, "indicador_t1"] == pytest.approx(65.0)


def test_leitor_do_sidra_pivota_variaveis(tmp_path):
    payload = [
        {"D1C": "Município (Código)", "D2C": "Variável (Código)", "D3C": "Ano (Código)", "V": "Valor"},
        {"D1C": "1100015", "D2C": "93", "D3C": "2022", "V": "21494"},
        {"D1C": "1100015", "D2C": "6318", "D3C": "2022", "V": "7067.127"},
        {"D1C": "1100015", "D2C": "614", "D3C": "2022", "V": "3.04"},
        {"D1C": "1100023", "D2C": "93", "D3C": "2022", "V": "..."},
    ]
    path = tmp_path / "censo.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    df = ibge.read_censo_2022(path).set_index("id_municipio")

    assert df.loc[1100015, "populacao"] == 21494
    assert df.loc[1100015, "densidade_hab_km2"] == pytest.approx(3.04)
    assert pd.isna(df.loc[1100023, "populacao"])
