"""Leitura das respostas da API SIDRA do IBGE.

O SIDRA devolve uma lista de registros em que o primeiro elemento e o cabecalho
descritivo. Cada registro traz o codigo do municipio (D1C), o codigo da variavel
(D2C), o ano (D3C) e o valor (V), que pode vir como "..." ou "-" quando nao
disponivel.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

VARIAVEIS_CENSO = {"93": "populacao", "6318": "area_km2", "614": "densidade_hab_km2"}
VARIAVEIS_PIB = {
    "37": "pib_mil_reais",
    "516": "pct_vab_agro",
    "520": "pct_vab_industria",
    "528": "pct_vab_adm_publica",
    "6574": "pct_vab_servicos",
}


def _sidra_para_tabela(path: Path, variaveis: dict[str, str]) -> pd.DataFrame:
    registros = json.loads(Path(path).read_text(encoding="utf-8"))[1:]
    df = pd.DataFrame(registros)[["D1C", "D2C", "D3C", "V"]]
    df["V"] = pd.to_numeric(df["V"], errors="coerce")
    df = df[df["D2C"].isin(variaveis)]
    wide = df.pivot_table(
        index=["D1C", "D3C"], columns="D2C", values="V", aggfunc="first", dropna=False
    )
    wide = wide.rename(columns=variaveis).reset_index()
    wide = wide.rename(columns={"D1C": "id_municipio", "D3C": "ano"})
    wide["id_municipio"] = wide["id_municipio"].astype("int64")
    wide["ano"] = wide["ano"].astype("int64")
    wide.columns.name = None
    return wide


def read_censo_2022(path: Path) -> pd.DataFrame:
    """Populacao residente, area e densidade por municipio (Censo 2022)."""
    return _sidra_para_tabela(path, VARIAVEIS_CENSO).drop(columns="ano")


def read_pib(path: Path) -> pd.DataFrame:
    """PIB a precos correntes e participacao dos setores no valor adicionado."""
    df = _sidra_para_tabela(path, VARIAVEIS_PIB)
    return df.rename(columns={"ano": "ano_pib"})


def enriquecer_com_per_capita(censo: pd.DataFrame, pib: pd.DataFrame) -> pd.DataFrame:
    """Junta censo e PIB e calcula o PIB per capita (R$ por habitante)."""
    df = censo.merge(pib, on="id_municipio", how="left")
    df["pib_per_capita"] = np.where(
        df["populacao"] > 0, 1000 * df["pib_mil_reais"] / df["populacao"], np.nan
    )
    return df
