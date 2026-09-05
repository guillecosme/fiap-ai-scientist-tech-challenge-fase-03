"""Reconstrucao da camada Gold com dado real.

A Fase 2 definiu o contrato da Gold: uma dimensao de municipio, uma tabela fato no
grao ano x municipio x rede e tres marts (indicador por municipio contra a meta,
comparacao por UF e evolucao temporal). Naquela fase o indicador e as metas foram
simulados. Aqui as mesmas tabelas sao recompostas a partir das fontes reais do Inep
e ganham uma tabela nova, fato_aluno, no grao de aluno, possivel porque o Inep
passou a publicar os microdados da avaliacao.

Uso:
    python -m src.data.gold

Saida em data/gold/*.parquet.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data import inep
from src.data.sources import RAW_DIR

GOLD_DIR = Path("data/gold")
ANOS_MICRODADOS = (2024, 2025)
ANOS_PLANILHA = (2023, 2024, 2025)

REGIAO_POR_DIGITO = {1: "Norte", 2: "Nordeste", 3: "Sudeste", 4: "Sul", 5: "Centro-Oeste"}


def _microdados_dir(ano: int) -> Path:
    return RAW_DIR / f"inep/microdados_{ano}/DADOS"


# ---------------------------------------------------------------------------
# Fontes
# ---------------------------------------------------------------------------


def carregar_resultados_e_metas() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Uniao das planilhas municipais de 2023, 2024 e 2025.

    Para cada (municipio, ano) o resultado preferido e o da planilha publicada no
    proprio ano, que traz nivel e participacao e nao sofre o arredondamento das
    republicacoes. A meta e a mesma em todas as planilhas; fica a versao com mais
    casas decimais (a mais antiga) e as demais so preenchem lacunas.
    """
    resultados, metas = [], []
    for ano in ANOS_PLANILHA:
        r, m = inep.read_ica_municipios(RAW_DIR / f"inep/ica_municipios_{ano}.xlsx")
        resultados.append(r)
        metas.append(m)
    resultados = pd.concat(resultados, ignore_index=True)
    metas = pd.concat(metas, ignore_index=True)

    resultados["prioridade"] = (resultados["ano_planilha"] - resultados["ano"]).abs()
    resultados = (
        resultados.sort_values(["id_municipio", "ano", "prioridade"])
        .drop_duplicates(["id_municipio", "ano"], keep="first")
        .drop(columns="prioridade")
        .reset_index(drop=True)
    )
    metas = (
        metas.dropna(subset=["meta_pct"])
        .sort_values(["id_municipio", "ano", "ano_planilha"])
        .drop_duplicates(["id_municipio", "ano"], keep="first")
        .reset_index(drop=True)
    )
    return resultados, metas


def carregar_ufs() -> tuple[pd.DataFrame, pd.DataFrame]:
    resultados, metas = [], []
    for ano in ANOS_PLANILHA:
        r, m = inep.read_ica_ufs(RAW_DIR / f"inep/ica_ufs_{ano}.xlsx")
        resultados.append(r)
        metas.append(m)
    resultados = pd.concat(resultados, ignore_index=True)
    metas = pd.concat(metas, ignore_index=True)
    resultados["prioridade"] = (resultados["ano_planilha"] - resultados["ano"]).abs()
    resultados = (
        resultados.dropna(subset=["indicador_pct"])
        .sort_values(["sigla_uf", "fonte", "ano", "prioridade"])
        .drop_duplicates(["sigla_uf", "fonte", "ano"], keep="first")
        .drop(columns="prioridade")
        .reset_index(drop=True)
    )
    metas = (
        metas.dropna(subset=["meta_pct"])
        .sort_values(["sigla_uf", "ano", "ano_planilha"])
        .drop_duplicates(["sigla_uf", "ano"], keep="first")
        .reset_index(drop=True)
    )
    return resultados, metas


# ---------------------------------------------------------------------------
# Tabelas da Gold
# ---------------------------------------------------------------------------


def build_fato_aluno() -> pd.DataFrame:
    """Grao de aluno: todos os avaliados, presentes ou nao, de 2024 e 2025."""
    partes = [
        inep.read_microdados_alunos(_microdados_dir(ano) / "TS_ALUNO.csv")
        for ano in ANOS_MICRODADOS
    ]
    df = pd.concat(partes, ignore_index=True)
    df["sigla_uf"] = df["sigla_uf"].astype(str).astype("category")
    df["rede"] = df["rede"].astype(str).replace({"nan": None}).astype("category")
    return df


def build_dim_municipio(resultados: pd.DataFrame, nomes_uf: pd.DataFrame) -> pd.DataFrame:
    """Municipios que aparecem em qualquer planilha ou nos microdados."""
    partes = [resultados[["id_municipio", "nome_municipio", "sigla_uf"]]]
    for ano in ANOS_MICRODADOS:
        ts = inep.read_microdados_municipio(_microdados_dir(ano) / "TS_MUNICIPIO.csv")
        partes.append(ts[["id_municipio", "nome_municipio", "sigla_uf"]])
    dim = pd.concat(partes, ignore_index=True).drop_duplicates("id_municipio", keep="first")
    dim["id_uf"] = (dim["id_municipio"] // 100000).astype("int64")
    dim["nome_regiao"] = (dim["id_uf"] // 10).map(REGIAO_POR_DIGITO)
    dim = dim.merge(nomes_uf, on="sigla_uf", how="left")
    return (
        dim[["id_municipio", "nome_municipio", "sigla_uf", "id_uf", "nome_uf", "nome_regiao"]]
        .sort_values("id_municipio")
        .reset_index(drop=True)
    )


def _agregar_alunos(alunos: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """Agrega os avaliados (presentes com prova preenchida) reproduzindo o calculo
    oficial: percentual e media ponderados pelo peso amostral do aluno."""
    p = alunos[(alunos["presente"] == 1) & (alunos["preencheu"] == 1)].copy()
    p = p.dropna(subset=chaves)
    p["w"] = p["peso"].astype("float64")
    p["w_alf"] = p["w"] * p["alfabetizado"]
    p["w_prof"] = p["w"] * p["proficiencia"].astype("float64")
    g = p.groupby(chaves, observed=True).agg(
        qtd_avaliados=("alfabetizado", "size"),
        qtd_alfabetizados=("alfabetizado", "sum"),
        soma_peso=("w", "sum"),
        soma_peso_alf=("w_alf", "sum"),
        soma_peso_prof=("w_prof", "sum"),
    )
    g["indicador_pct"] = (100 * g["soma_peso_alf"] / g["soma_peso"]).round(2)
    g["media_proficiencia"] = (g["soma_peso_prof"] / g["soma_peso"]).round(1)
    g["indicador_pct_bruto"] = (100 * g["qtd_alfabetizados"] / g["qtd_avaliados"]).round(2)
    return g.drop(columns=["soma_peso", "soma_peso_alf", "soma_peso_prof"]).reset_index()


def build_fato_alfabetizacao(
    alunos: pd.DataFrame, dim: pd.DataFrame, metas: pd.DataFrame
) -> pd.DataFrame:
    """Fato no grao ano x municipio x rede, com a meta municipal ao lado."""
    fato = _agregar_alunos(alunos, ["ano", "id_municipio", "rede"])
    fato["id_municipio"] = fato["id_municipio"].astype("int64")
    fato["rede"] = fato["rede"].astype(str)
    fato = fato.merge(
        dim[["id_municipio", "nome_municipio", "sigla_uf", "id_uf", "nome_regiao"]],
        on="id_municipio",
        how="left",
    )
    fato = fato.merge(
        metas.rename(columns={"meta_pct": "meta_municipio"})[
            ["id_municipio", "ano", "meta_municipio"]
        ],
        on=["id_municipio", "ano"],
        how="left",
    )
    fato["atingiu_meta"] = np.where(
        fato["meta_municipio"].isna(), None, fato["indicador_pct"] >= fato["meta_municipio"]
    )
    fato["atingiu_meta"] = fato["atingiu_meta"].astype("boolean")
    fato["gap_meta_pp"] = (fato["indicador_pct"] - fato["meta_municipio"]).round(1)
    colunas = [
        "ano",
        "id_municipio",
        "nome_municipio",
        "sigla_uf",
        "id_uf",
        "nome_regiao",
        "rede",
        "qtd_avaliados",
        "qtd_alfabetizados",
        "media_proficiencia",
        "indicador_pct",
        "indicador_pct_bruto",
        "meta_municipio",
        "atingiu_meta",
        "gap_meta_pp",
    ]
    return fato[colunas].sort_values(["ano", "id_municipio", "rede"]).reset_index(drop=True)


def build_indicador_municipio(
    resultados: pd.DataFrame, metas: pd.DataFrame, dim: pd.DataFrame, fato: pd.DataFrame
) -> pd.DataFrame:
    """Mart: serie oficial do indicador da rede municipal (2023 a 2025) contra a meta.

    O percentual vem da planilha de divulgacao do Inep, que e a referencia usada
    para cobrar a meta. Os volumes de avaliados vem dos microdados quando existem.
    """
    ind = resultados.drop(columns=["nome_municipio", "sigla_uf", "rede", "ano_planilha"])
    ind = ind.merge(dim, on="id_municipio", how="left")
    ind = ind.merge(
        metas.rename(columns={"meta_pct": "meta_municipio"})[
            ["id_municipio", "ano", "meta_municipio"]
        ],
        on=["id_municipio", "ano"],
        how="left",
    )
    volumes = fato[fato["rede"] == "municipal"][
        ["ano", "id_municipio", "qtd_avaliados", "qtd_alfabetizados", "media_proficiencia"]
    ]
    ind = ind.merge(volumes, on=["ano", "id_municipio"], how="left")
    ind["atingiu_meta"] = np.where(
        ind["meta_municipio"].isna() | ind["indicador_pct"].isna(),
        None,
        ind["indicador_pct"] >= ind["meta_municipio"],
    )
    ind["atingiu_meta"] = ind["atingiu_meta"].astype("boolean")
    ind["gap_meta_pp"] = (ind["indicador_pct"] - ind["meta_municipio"]).round(1)
    colunas = [
        "ano",
        "id_municipio",
        "nome_municipio",
        "sigla_uf",
        "id_uf",
        "nome_uf",
        "nome_regiao",
        "qtd_avaliados",
        "qtd_alfabetizados",
        "media_proficiencia",
        "indicador_pct",
        "nivel",
        "participacao_pct",
        "meta_municipio",
        "atingiu_meta",
        "gap_meta_pp",
    ]
    return ind[colunas].sort_values(["ano", "id_municipio"]).reset_index(drop=True)


def build_metas_municipio(metas: pd.DataFrame) -> pd.DataFrame:
    """Metas anuais por municipio, 2024 a 2030, em formato longo."""
    return (
        metas.drop(columns="ano_planilha")
        .sort_values(["id_municipio", "ano"])
        .reset_index(drop=True)
    )


def build_evolucao_temporal(indicador: pd.DataFrame) -> pd.DataFrame:
    """Mart: serie do indicador por municipio com o valor do ano anterior e a variacao."""
    ev = indicador[
        ["ano", "id_municipio", "nome_municipio", "sigla_uf", "nome_regiao", "indicador_pct"]
    ].copy()
    ev = ev.sort_values(["id_municipio", "ano"])
    ev["indicador_ano_anterior"] = ev.groupby("id_municipio")["indicador_pct"].shift(1)
    ev["variacao_pp"] = (ev["indicador_pct"] - ev["indicador_ano_anterior"]).round(1)
    return ev.reset_index(drop=True)


def build_comparacao_meta_uf(resultados_uf: pd.DataFrame, metas_uf: pd.DataFrame) -> pd.DataFrame:
    """Mart: indicador por UF (e Brasil) contra a meta estadual, com o Saeb 2019 e 2021
    como serie de referencia anterior ao indicador."""
    r = resultados_uf.drop(columns="ano_planilha")
    r = r.merge(
        metas_uf.rename(columns={"meta_pct": "meta_uf"})[["sigla_uf", "ano", "meta_uf"]],
        on=["sigla_uf", "ano"],
        how="left",
    )
    r["atingiu_meta"] = np.where(r["meta_uf"].isna(), None, r["indicador_pct"] >= r["meta_uf"])
    r["atingiu_meta"] = r["atingiu_meta"].astype("boolean")
    r["gap_meta_pp"] = (r["indicador_pct"] - r["meta_uf"]).round(1)
    return r.sort_values(["sigla_uf", "fonte", "ano"]).reset_index(drop=True)


def build_metas_uf(metas_uf: pd.DataFrame) -> pd.DataFrame:
    return (
        metas_uf.drop(columns="ano_planilha")
        .sort_values(["sigla_uf", "ano"])
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Execucao
# ---------------------------------------------------------------------------


def run(gold_dir: Path = GOLD_DIR) -> dict[str, pd.DataFrame]:
    gold_dir.mkdir(parents=True, exist_ok=True)
    resultados, metas = carregar_resultados_e_metas()
    resultados_uf, metas_uf = carregar_ufs()
    nomes_uf = resultados_uf[["sigla_uf", "nome_uf"]].drop_duplicates("sigla_uf")

    alunos = build_fato_aluno()
    dim = build_dim_municipio(resultados, nomes_uf)
    fato = build_fato_alfabetizacao(alunos, dim, metas)
    indicador = build_indicador_municipio(resultados, metas, dim, fato)

    tabelas = {
        "dim_municipio": dim,
        "fato_aluno": alunos,
        "fato_alfabetizacao": fato,
        "indicador_municipio": indicador,
        "metas_municipio": build_metas_municipio(metas),
        "evolucao_temporal": build_evolucao_temporal(indicador),
        "comparacao_meta_uf": build_comparacao_meta_uf(resultados_uf, metas_uf),
        "metas_uf": build_metas_uf(metas_uf),
    }
    for nome, df in tabelas.items():
        destino = gold_dir / f"{nome}.parquet"
        df.to_parquet(destino, index=False, compression="zstd")
        print(f"[gold] {nome}: {len(df):,} linhas x {df.shape[1]} colunas -> {destino}")
    return tabelas


if __name__ == "__main__":
    run()
