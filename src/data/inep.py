"""Leitura das fontes do Inep em tabelas tidy.

Cada funcao recebe o caminho do arquivo bruto e devolve um DataFrame com nomes de
coluna padronizados (snake_case, chaves id_municipio, sigla_uf, ano). As planilhas
do Inep tem cabecalhos de varias linhas, metas em formato largo e marcadores de
ausencia como "-" ou "--"; tudo isso e resolvido aqui para que o resto do projeto
trabalhe com dados limpos.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

NA_VALUES = ["-", "--", "---", "...", "", " ", "-  ", "- "]
REDE_MICRODADOS = {1: "federal", 2: "estadual", 3: "municipal", 4: "privada"}


def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


# ---------------------------------------------------------------------------
# Resultados e metas do Indicador Crianca Alfabetizada
# ---------------------------------------------------------------------------


def read_ica_municipios(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Planilha de resultados e metas por municipio.

    Devolve duas tabelas em formato longo:
    - resultados: id_municipio, ano, indicador_pct, nivel, participacao_pct
    - metas: id_municipio, ano, meta_pct

    A planilha do ano t traz o resultado de t (com nivel e participacao) e, nas
    versoes de 2024 e 2025, os resultados dos anos anteriores repetidos. Cada
    resultado e anotado com o ano da planilha de origem para que a montagem da
    Gold prefira a versao publicada no proprio ano.
    """
    df = pd.read_excel(path, header=1, na_values=NA_VALUES)
    # linhas de rodape (notas) nao tem codigo de municipio
    df["CO_MUNICIPIO"] = _to_num(df["CO_MUNICIPIO"])
    df = df.dropna(subset=["CO_MUNICIPIO"]).reset_index(drop=True)
    ano_planilha = int(df["ANO"].iloc[0])
    base = pd.DataFrame(
        {
            "id_municipio": df["CO_MUNICIPIO"].astype("int64"),
            "sigla_uf": df["SG_UF"].astype(str).str.strip(),
            "nome_municipio": df["NO_MUNICIPIO"].astype(str).str.strip(),
            "rede": df["NO_TP_REDE"].astype(str).str.strip().str.lower(),
        }
    )

    resultados = []
    for col in df.columns:
        m = re.fullmatch(r"PC_ALUNO_ALFABETIZADO(?:_(\d{4}))?", str(col))
        if not m:
            continue
        ano = int(m.group(1)) if m.group(1) else ano_planilha
        r = base.copy()
        r["ano"] = ano
        r["indicador_pct"] = _to_num(df[col])
        r["ano_planilha"] = ano_planilha
        resultados.append(r)
    resultados = pd.concat(resultados, ignore_index=True)

    nivel_col = next((c for c in df.columns if str(c).startswith(("CO_NIVEL", "NIVEIS_"))), None)
    part_col = "PC_AVALIADOS_LP" if "PC_AVALIADOS_LP" in df.columns else None
    extra = base[["id_municipio"]].copy()
    extra["ano"] = ano_planilha
    extra["nivel"] = _to_num(df[nivel_col]) if nivel_col else np.nan
    extra["participacao_pct"] = _to_num(df[part_col]) if part_col else np.nan
    resultados = resultados.merge(extra, on=["id_municipio", "ano"], how="left")

    metas = []
    for col in df.columns:
        m = re.fullmatch(r"META_FINAL_(\d{4})", str(col))
        if not m:
            continue
        t = base[["id_municipio"]].copy()
        t["ano"] = int(m.group(1))
        t["meta_pct"] = _to_num(df[col])
        t["ano_planilha"] = ano_planilha
        metas.append(t)
    metas = pd.concat(metas, ignore_index=True)
    return resultados, metas


def read_ica_ufs(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Planilha de resultados e metas por UF (e Brasil, sigla 'BR')."""
    df = pd.read_excel(path, header=1, na_values=NA_VALUES)
    df = df.dropna(subset=["NOME_UF"]).reset_index(drop=True)
    ano_planilha = int(df["ANO"].iloc[0])
    # a planilha de 2025 marca uma UF com asterisco de nota de rodape
    sigla = df["SIGLA_UF"].fillna("BR").astype(str).str.replace("*", "", regex=False).str.strip()
    base = pd.DataFrame({"sigla_uf": sigla, "nome_uf": df["NOME_UF"].astype(str).str.strip()})

    resultados = []
    for col in df.columns:
        c = str(col)
        if m := re.fullmatch(r"PC_ALUNO_ALFABETIZADO(?:_(\d{4}))?", c):
            ano, fonte = (int(m.group(1)) if m.group(1) else ano_planilha), "indicador"
        elif m := re.fullmatch(r"SAEB_(\d{4})", c):
            ano, fonte = int(m.group(1)), "saeb"
        else:
            continue
        r = base.copy()
        r["ano"] = ano
        r["fonte"] = fonte
        r["indicador_pct"] = _to_num(df[col])
        r["ano_planilha"] = ano_planilha
        resultados.append(r)
    resultados = pd.concat(resultados, ignore_index=True)

    metas = []
    for col in df.columns:
        m = re.fullmatch(r"META_FINAL_(\d{4})", str(col))
        if not m:
            continue
        t = base[["sigla_uf"]].copy()
        t["ano"] = int(m.group(1))
        # a meta de 2030 vem como texto "> 80"
        t["meta_pct"] = _to_num(df[col].astype(str).str.replace(">", "").str.strip())
        t["ano_planilha"] = ano_planilha
        metas.append(t)
    metas = pd.concat(metas, ignore_index=True)
    return resultados, metas


# ---------------------------------------------------------------------------
# INSE e indicadores do Censo Escolar
# ---------------------------------------------------------------------------


def read_inse_municipios(path: Path) -> pd.DataFrame:
    """INSE por municipio, no estrato total da rede publica (federal, estadual e
    municipal) e localizacao total, mais a fatia rural dos alunos."""
    df = pd.read_excel(path, sheet_name="INSE_MUN_2023", na_values=NA_VALUES)
    publica = df[df["TP_TIPO_REDE"] == 6]
    total = publica[publica["TP_LOCALIZACAO"] == 0].copy()
    rural = publica[publica["TP_LOCALIZACAO"] == 2][["CO_MUNICIPIO", "QTD_ALUNOS_INSE"]]
    rural = rural.rename(columns={"QTD_ALUNOS_INSE": "qtd_rural"})
    out = total.merge(rural, on="CO_MUNICIPIO", how="left")
    out["qtd_rural"] = out["qtd_rural"].fillna(0)
    res = pd.DataFrame(
        {
            "id_municipio": out["CO_MUNICIPIO"].astype("int64"),
            "capital": (out["TP_CAPITAL"] == 1).astype("int8"),
            "inse_medio": _to_num(out["MEDIA_INSE"]),
            "inse_qtd_alunos": _to_num(out["QTD_ALUNOS_INSE"]),
            "pct_alunos_rural": 100 * out["qtd_rural"] / out["QTD_ALUNOS_INSE"],
        }
    )
    baixo = out[["PC_NIVEL_1", "PC_NIVEL_2", "PC_NIVEL_3"]].apply(_to_num).fillna(0).sum(axis=1)
    alto = out[["PC_NIVEL_6", "PC_NIVEL_7", "PC_NIVEL_8"]].apply(_to_num).fillna(0).sum(axis=1)
    res["inse_pct_nivel_baixo"] = baixo.values
    res["inse_pct_nivel_alto"] = alto.values
    return res


def _read_censo_sheet(path: Path) -> pd.DataFrame:
    """Le uma planilha de indicador do Censo Escolar localizando a linha de cabecalho
    (a que comeca com NU_ANO_CENSO) e filtrando o estrato total de localizacao."""
    raw = pd.read_excel(path, header=None, nrows=15)
    header_row = next(
        i for i in range(len(raw)) if str(raw.iloc[i, 0]).strip() == "NU_ANO_CENSO"
    )
    df = pd.read_excel(path, header=header_row, na_values=NA_VALUES)
    df = df[df["NO_CATEGORIA"] == "Total"].copy()
    df["CO_MUNICIPIO"] = _to_num(df["CO_MUNICIPIO"]).astype("Int64")
    df = df.dropna(subset=["CO_MUNICIPIO"])
    return df


# colunas de interesse por indicador: nome de saida -> coluna na planilha
CENSO_COLUNAS = {
    "afd": {
        "afd_ai_grupo1_pct": "FUN_AI_CAT_1",
        "afd_ai_grupo5_pct": "FUN_AI_CAT_5",
        "afd_inf_grupo1_pct": "ED_INF_CAT_1",
    },
    "atu": {
        "alunos_por_turma_ai": "FUN_AI_CAT_0",
        "alunos_por_turma_2ano": "FUN_02_CAT_0",
        "alunos_por_turma_pre": "PRE_CAT_0",
    },
    "tdi": {
        "distorcao_ai_pct": "FUN_AI_CAT_0",
        "distorcao_2ano_pct": "FUN_02_CAT_0",
    },
    "dsu": {
        "docentes_superior_ai_pct": "FUN_AI_CAT_0",
        "docentes_superior_inf_pct": "ED_INF_CAT_0",
    },
    "rend": {
        "aprovacao_ai_pct": "1_CAT_FUN_AI",
        "aprovacao_1ano_pct": "1_CAT_FUN_01",
        "aprovacao_2ano_pct": "1_CAT_FUN_02",
        "reprovacao_ai_pct": "2_CAT_FUN_AI",
        "abandono_ai_pct": "3_CAT_FUN_AI",
    },
}


def read_indicador_censo(path: Path, indicador: str, dependencia: str = "Pública") -> pd.DataFrame:
    """Indicador do Censo Escolar por municipio para uma dependencia administrativa.

    O padrao e a rede publica (estadual + municipal), que e o universo avaliado
    pelo Indicador Crianca Alfabetizada.
    """
    colunas = CENSO_COLUNAS[indicador]
    df = _read_censo_sheet(path)
    df = df[df["NO_DEPENDENCIA"] == dependencia]
    out = pd.DataFrame(
        {
            "ano": df["NU_ANO_CENSO"].astype("int64"),
            "id_municipio": df["CO_MUNICIPIO"].astype("int64"),
        }
    )
    for nome, col in colunas.items():
        out[nome] = _to_num(df[col]).values
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# IDEB anos iniciais
# ---------------------------------------------------------------------------


def read_ideb_anos_iniciais(path: Path, rede: str = "Pública") -> pd.DataFrame:
    """IDEB dos anos iniciais em formato longo: id_municipio, ano, ideb, nota_lp,
    nota_mt, aprovacao (indicador de rendimento)."""
    raw = pd.read_excel(path, header=None, nrows=15)
    header_row = next(i for i in range(len(raw)) if str(raw.iloc[i, 0]).strip() == "SG_UF")
    df = pd.read_excel(path, header=header_row, na_values=NA_VALUES)
    df = df[df["REDE"] == rede].copy()
    df["CO_MUNICIPIO"] = _to_num(df["CO_MUNICIPIO"]).astype("Int64")
    df = df.dropna(subset=["CO_MUNICIPIO"])

    padrao_ano = re.compile(r"VL_OBSERVADO_(\d{4})")
    anos = sorted({int(m.group(1)) for c in df.columns if (m := padrao_ano.fullmatch(str(c)))})
    colunas = {
        "ideb": "VL_OBSERVADO_{}",
        "nota_lp": "VL_NOTA_PORTUGUES_{}",
        "nota_mt": "VL_NOTA_MATEMATICA_{}",
        "rendimento": "VL_INDICADOR_REND_{}",
    }
    partes = []
    for ano in anos:
        p = pd.DataFrame({"id_municipio": df["CO_MUNICIPIO"].astype("int64"), "ano": ano})
        for nome, padrao in colunas.items():
            col = padrao.format(ano)
            p[nome] = _to_num(df[col]).values if col in df.columns else np.nan
        partes.append(p)
    return pd.concat(partes, ignore_index=True)
