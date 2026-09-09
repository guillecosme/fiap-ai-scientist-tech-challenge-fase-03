"""Listas de variaveis dos dois modelos e preparacao de X e y.

As listas seguem as decisoes da EDA (docs/decisoes_analiticas.md):
- UF entra como categorica; regiao fica de fora (D9);
- nivel_t1 e meta_t ficam de fora por redundancia (D16);
- indicador_t2, variacao_t1, meta_t1 e gap_meta_t1 ficam de fora porque so existem a
  partir do ano-alvo 2025 (notebook 01);
- variaveis de porte e renda recebem log1p (D12);
- o historico do indicador recebe indicador de ausencia (D17).
"""

from __future__ import annotations

import pandas as pd

# historico do indicador: imputado pela mediana com indicador de ausencia
HISTORICO = ["indicador_t1", "participacao_t1", "salto_necessario"]

# porte e renda: log1p antes do escalonamento
LOG_MUNICIPIO = ["populacao", "area_km2", "densidade_hab_km2", "pib_per_capita", "inse_qtd_alunos"]

# demais numericas do contexto municipal
CONTEXTO_MUNICIPIO = [
    # censo escolar
    "afd_ai_grupo1_pct",
    "afd_ai_grupo5_pct",
    "afd_inf_grupo1_pct",
    "alunos_por_turma_ai",
    "alunos_por_turma_2ano",
    "alunos_por_turma_pre",
    "distorcao_ai_pct",
    "distorcao_2ano_pct",
    "docentes_superior_ai_pct",
    "docentes_superior_inf_pct",
    # rendimento do ano anterior
    "aprovacao_ai_pct",
    "aprovacao_1ano_pct",
    "aprovacao_2ano_pct",
    "reprovacao_ai_pct",
    "abandono_ai_pct",
    # ideb
    "ideb_ultimo",
    "ideb_nota_lp_ultimo",
    "ideb_rendimento_ultimo",
    "ideb_anterior",
    "ideb_variacao",
    "ideb_tendencia",
    # socioeconomico e territorio
    "inse_medio",
    "pct_alunos_rural",
    "inse_pct_nivel_baixo",
    "inse_pct_nivel_alto",
    "capital",
    "pct_vab_agro",
    "pct_vab_industria",
    "pct_vab_adm_publica",
    "pct_vab_servicos",
]

CATEGORICAS_MUNICIPIO = ["sigla_uf"]

# aluno: atributos da escola mais o contexto municipal
LOG_ALUNO = ["escola_qtd_avaliados", *LOG_MUNICIPIO]
CONTEXTO_ALUNO = ["escola_taxa_presenca", *CONTEXTO_MUNICIPIO]
CATEGORICAS_ALUNO = ["rede", "sigla_uf"]


def grupos_municipio() -> dict[str, list[str]]:
    return {
        "historico": list(HISTORICO),
        "log": list(LOG_MUNICIPIO),
        "numericas": list(CONTEXTO_MUNICIPIO),
        "categoricas": list(CATEGORICAS_MUNICIPIO),
    }


def grupos_aluno() -> dict[str, list[str]]:
    return {
        "historico": list(HISTORICO),
        "log": list(LOG_ALUNO),
        "numericas": list(CONTEXTO_ALUNO),
        "categoricas": list(CATEGORICAS_ALUNO),
    }


def colunas(grupos: dict[str, list[str]]) -> list[str]:
    return [c for lista in grupos.values() for c in lista]


def preparar_xy(
    df: pd.DataFrame, grupos: dict[str, list[str]], alvo: str
) -> tuple[pd.DataFrame, pd.Series]:
    """Seleciona as colunas do modelo e o alvo como inteiro 0/1."""
    cols = colunas(grupos)
    faltando = [c for c in cols if c not in df.columns]
    if faltando:
        raise KeyError(f"Colunas ausentes na base: {faltando}")
    x = df[cols].copy()
    for c in grupos.get("categoricas", []):
        x[c] = x[c].astype(str)
    y = df[alvo].astype(int)
    return x, y
