"""Testes dos parsers do Inep com planilhas pequenas no mesmo layout das originais."""

# ruff: noqa: E501  (as linhas longas sao as fixtures no layout literal das planilhas)

import pandas as pd
import pytest

from src.data import inep


def _write_xlsx(path, rows, sheet="Divulgação Alfabet Municipio"):
    pd.DataFrame(rows).to_excel(path, header=False, index=False, sheet_name=sheet)


@pytest.fixture
def ica_municipios_2024(tmp_path):
    path = tmp_path / "ica_2024.xlsx"
    rows = [
        ["ANO DA AVALIAÇÃO", "CÓDIGO UF", "SIGLA UF", "CÓDIGO MUNICÍPIO", "NOME DO MUNICÍPIO",
         "REDE", "PCT 2023", "PCT 2024", "META 2024", "META 2025", "NIVEL", "PARTICIPAÇÃO"],
        ["ANO", "CO_UF", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "NO_TP_REDE",
         "PC_ALUNO_ALFABETIZADO_2023", "PC_ALUNO_ALFABETIZADO_2024", "META_FINAL_2024",
         "META_FINAL_2025", "CO_NIVEL_ALFABETIZACAO", "PC_AVALIADOS_LP"],
        [2024, 11, "RO", 1100015, "Alta Floresta D'Oeste", "MUNICIPAL", 64.6, 67.79, 67.08, 69.51, 3, 89.87],
        [2024, 11, "RO", 1100023, "Ariquemes", "MUNICIPAL", "-", 65.62, "-", 68.02, 3, 88.76],
        [None, None, None, None, "(1) nota de rodape", None, None, None, None, None, None, None],
    ]
    _write_xlsx(path, rows)
    return path


def test_ica_municipios_vira_formato_longo(ica_municipios_2024):
    resultados, metas = inep.read_ica_municipios(ica_municipios_2024)

    assert set(resultados["ano"]) == {2023, 2024}
    assert len(resultados) == 4  # dois municipios x dois anos, rodape descartado
    r = resultados.set_index(["id_municipio", "ano"])
    assert r.loc[(1100015, 2024), "indicador_pct"] == pytest.approx(67.79)
    assert r.loc[(1100015, 2024), "nivel"] == 3
    assert pd.isna(r.loc[(1100015, 2023), "nivel"])  # nivel so existe para o ano da planilha
    assert pd.isna(r.loc[(1100023, 2023), "indicador_pct"])  # "-" vira ausente

    assert set(metas["ano"]) == {2024, 2025}
    m = metas.set_index(["id_municipio", "ano"])["meta_pct"]
    assert m.loc[(1100015, 2025)] == pytest.approx(69.51)
    assert pd.isna(m.loc[(1100023, 2024)])
    assert (resultados["ano_planilha"] == 2024).all()


def test_ica_ufs_trata_brasil_e_meta_com_texto(tmp_path):
    path = tmp_path / "ufs.xlsx"
    rows = [
        ["ANO", "CÓDIGO UF", "SIGLA UF", "NOME UF", "REDE", "PCT 2023", "PCT 2024", "META 2024", "META 2030", "PART"],
        ["ANO", "CD_UF", "SIGLA_UF", "NOME_UF", "REDE", "PC_ALUNO_ALFABETIZADO_2023",
         "PC_ALUNO_ALFABETIZADO_2024", "META_FINAL_2024", "META_FINAL_2030", "PC_AVALIADOS_LP"],
        [2024, None, None, "Brasil", "PÚBLICA", 55.9, 59.2, 59.9, "> 80", 87.4],
        [2024, 42, "SC*", "Santa Catarina", "PÚBLICA", 60.1, 64.0, 63.5, "> 80", 90.0],
    ]
    _write_xlsx(path, rows, sheet="Divulgação Alfabet UF e Brasil")
    resultados, metas = inep.read_ica_ufs(path)

    assert set(resultados["sigla_uf"]) == {"BR", "SC"}
    assert metas.set_index(["sigla_uf", "ano"]).loc[("BR", 2030), "meta_pct"] == 80


def test_indicador_censo_localiza_cabecalho_e_filtra_estratos(tmp_path):
    path = tmp_path / "tdi.xlsx"
    rows = [
        [None, "Ministério da Educação"],
        ["Taxa de Distorção"],
        ["Ano", "Região", "Sigla da UF", "Código do Município", "Nome", "Localização", "Dependência", "Total", "Anos Iniciais", "2º Ano"],
        ["NU_ANO_CENSO", "NO_REGIAO", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "NO_CATEGORIA", "NO_DEPENDENCIA", "FUN_CAT_0", "FUN_AI_CAT_0", "FUN_02_CAT_0"],
        [2024, "Norte", "RO", 1100015, "Alta Floresta", "Total", "Total", 10.9, 8.5, 2.8],
        [2024, "Norte", "RO", 1100015, "Alta Floresta", "Total", "Pública", 11.2, 8.9, 3.1],
        [2024, "Norte", "RO", 1100015, "Alta Floresta", "Rural", "Pública", 17.5, 12.9, 4.9],
        [2024, "Norte", "RO", 1100023, "Ariquemes", "Total", "Pública", "--", 6.0, 1.9],
    ]
    _write_xlsx(path, rows, sheet="Plan1")
    out = inep.read_indicador_censo(path, "tdi")

    assert list(out.columns) == ["ano", "id_municipio", "distorcao_ai_pct", "distorcao_2ano_pct"]
    assert len(out) == 2  # so o estrato total x publica, um por municipio
    assert out.set_index("id_municipio").loc[1100015, "distorcao_ai_pct"] == pytest.approx(8.9)


def test_ideb_em_formato_longo(tmp_path):
    path = tmp_path / "ideb.xlsx"
    rows = [
        [None, "Ministério da Educação"],
        ["Sigla da UF", "Código", "Nome", "Rede", "Ideb 2021", "Ideb 2023", "LP 2023", "MT 2023", "Rend 2023"],
        ["SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "REDE", "VL_OBSERVADO_2021", "VL_OBSERVADO_2023",
         "VL_NOTA_PORTUGUES_2023", "VL_NOTA_MATEMATICA_2023", "VL_INDICADOR_REND_2023"],
        ["RO", 1100015, "Alta Floresta", "Pública", 5.1, 5.6, 200.1, 210.5, 0.95],
        ["RO", 1100015, "Alta Floresta", "Municipal", 5.0, 5.5, 199.0, 209.0, 0.94],
        ["RO", 1100023, "Ariquemes", "Pública", "-", 6.0, 205.0, 215.0, 0.97],
    ]
    _write_xlsx(path, rows, sheet="Plan1")
    out = inep.read_ideb_anos_iniciais(path)

    assert set(out["ano"]) == {2021, 2023}
    assert len(out) == 4
    o = out.set_index(["id_municipio", "ano"])
    assert o.loc[(1100015, 2023), "ideb"] == pytest.approx(5.6)
    assert pd.isna(o.loc[(1100023, 2021), "ideb"])
    assert pd.isna(o.loc[(1100015, 2021), "nota_lp"])  # coluna ausente para o ano vira NaN
