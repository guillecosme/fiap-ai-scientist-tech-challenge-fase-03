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
