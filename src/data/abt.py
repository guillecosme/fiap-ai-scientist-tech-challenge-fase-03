"""Montagem das bases analiticas (ABT) de municipio e de aluno.

A regra central e o alinhamento temporal: para o ano-alvo t (prova aplicada em
outubro e novembro de t) so entram variaveis conhecidas antes disso.

    Censo Escolar de t         referencia no fim de maio de t
    rendimento de t-1          ano letivo anterior
    IDEB ate t-1               ultima edicao publicada antes de t
    indicador de t-1           resultado do ano anterior
    meta de t                  definida desde 2023 para todos os anos ate 2030
    Censo 2022, PIB 2022, INSE 2023   estaticos, anteriores a todos os anos-alvo

Quando uma fonte ainda nao foi publicada para o ano-alvo (caso da projecao para
2026), vale a ultima edicao disponivel, e isso fica registrado na coluna de
referencia correspondente.

Uso:
    python -m src.data.abt

Saida:
    data/processed/abt_municipio.parquet   uma linha por municipio x ano-alvo (2024, 2025, 2026)
    data/processed/abt_aluno.parquet       uma linha por aluno avaliado (2024 e 2025), com as
                                           chaves para juntar as variaveis municipais
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data import ibge, inep
from src.data.gold import GOLD_DIR
from src.data.sources import EXTERNAL_DIR

PROCESSED_DIR = Path("data/processed")
ANOS_ALVO = (2024, 2025, 2026)

# edicoes disponiveis de cada fonte; a montagem escolhe a ultima edicao <= ano de referencia
EDICOES_CENSO = (2024, 2025)
EDICOES_REND = (2023, 2024)

CHAVES_ALUNO = ["ano", "id_aluno", "id_municipio", "id_escola", "sigla_uf", "rede"]


def _ultima_edicao(edicoes: tuple[int, ...], ano_referencia: int) -> int:
    disponiveis = [e for e in edicoes if e <= ano_referencia]
    return max(disponiveis) if disponiveis else min(edicoes)


def _zip_xlsx(nome: str) -> Path:
    """Caminho do xlsx dentro da pasta extraida de um zip do Inep."""
    pasta = EXTERNAL_DIR / f"inep/{nome}"
    candidatos = sorted(pasta.rglob("*.xlsx"))
    if not candidatos:
        raise FileNotFoundError(f"Nenhum xlsx em {pasta}; rode `make data`")
    return candidatos[0]


# ---------------------------------------------------------------------------
# Blocos de variaveis
# ---------------------------------------------------------------------------


def bloco_estatico() -> pd.DataFrame:
    """Territorio, renda e nivel socioeconomico: uma linha por municipio."""
    censo = ibge.read_censo_2022(EXTERNAL_DIR / "ibge/censo_2022.json")
    pib = ibge.read_pib(EXTERNAL_DIR / "ibge/pib_municipal.json")
    df = ibge.enriquecer_com_per_capita(censo, pib)
    inse = inep.read_inse_municipios(EXTERNAL_DIR / "inep/inse_2023_municipios.xlsx")
    df = df.merge(inse, on="id_municipio", how="outer")
    return df


def bloco_censo_escolar(ano_alvo: int) -> pd.DataFrame:
    """Indicadores do Censo Escolar do ano-alvo (ou da ultima edicao disponivel)."""
    edicao = _ultima_edicao(EDICOES_CENSO, ano_alvo)
    partes = []
    for indicador in ("afd", "atu", "tdi", "dsu"):
        df = inep.read_indicador_censo(_zip_xlsx(f"{indicador}_{edicao}"), indicador)
        partes.append(df.drop(columns="ano"))
    out = partes[0]
    for p in partes[1:]:
        out = out.merge(p, on="id_municipio", how="outer")
    out["ref_censo_escolar"] = edicao
    return out


def bloco_rendimento(ano_alvo: int) -> pd.DataFrame:
    """Rendimento do ano letivo anterior ao ano-alvo (ou da ultima edicao)."""
    edicao = _ultima_edicao(EDICOES_REND, ano_alvo - 1)
    df = inep.read_indicador_censo(_zip_xlsx(f"rend_{edicao}"), "rend").drop(columns="ano")
    df["ref_rendimento"] = edicao
    return df


def bloco_ideb(ideb: pd.DataFrame, ano_alvo: int) -> pd.DataFrame:
    """Ultimo IDEB publicado antes do ano-alvo, o anterior e a tendencia recente."""
    hist = ideb[ideb["ano"] <= ano_alvo - 1].sort_values(["id_municipio", "ano"])
    ultimo = hist.groupby("id_municipio").tail(1).set_index("id_municipio")
    anterior = hist.groupby("id_municipio").nth(-2).set_index("id_municipio")
    out = pd.DataFrame(
        {
            "ideb_ultimo": ultimo["ideb"],
            "ideb_nota_lp_ultimo": ultimo["nota_lp"],
            "ideb_rendimento_ultimo": ultimo["rendimento"],
            "ref_ideb": ultimo["ano"],
            "ideb_anterior": anterior["ideb"],
        }
    )
    out["ideb_variacao"] = out["ideb_ultimo"] - out["ideb_anterior"]

    # tendencia: inclinacao da reta nas ultimas cinco edicoes (pontos de IDEB por edicao)
    recentes = hist.groupby("id_municipio").tail(5).dropna(subset=["ideb"])

    def _inclinacao(g: pd.DataFrame) -> float:
        if len(g) < 3:
            return np.nan
        x = (g["ano"] - g["ano"].mean()) / 2.0
        return float((x * (g["ideb"] - g["ideb"].mean())).sum() / (x**2).sum())

    out["ideb_tendencia"] = recentes.groupby("id_municipio").apply(
        _inclinacao, include_groups=False
    )
    return out.reset_index()


def bloco_indicador(indicador: pd.DataFrame, metas: pd.DataFrame, ano_alvo: int) -> pd.DataFrame:
    """Historico do indicador ate t-1, meta de t e o alvo (quando t ja aconteceu)."""
    t1 = indicador[indicador["ano"] == ano_alvo - 1].set_index("id_municipio")
    t2 = indicador[indicador["ano"] == ano_alvo - 2].set_index("id_municipio")
    meta_t = metas[metas["ano"] == ano_alvo].set_index("id_municipio")["meta_pct"]
    meta_t1 = metas[metas["ano"] == ano_alvo - 1].set_index("id_municipio")["meta_pct"]
    alvo = indicador[indicador["ano"] == ano_alvo].set_index("id_municipio")

    ids = sorted(set(t1.index) | set(meta_t.index) | set(alvo.index))
    out = pd.DataFrame(index=pd.Index(ids, name="id_municipio"))
    out["indicador_t1"] = t1["indicador_pct"]
    out["nivel_t1"] = t1["nivel"]
    out["participacao_t1"] = t1["participacao_pct"]
    out["indicador_t2"] = t2["indicador_pct"]
    out["variacao_t1"] = out["indicador_t1"] - out["indicador_t2"]
    out["meta_t1"] = meta_t1
    out["gap_meta_t1"] = out["indicador_t1"] - out["meta_t1"]
    out["meta_t"] = meta_t
    out["salto_necessario"] = out["meta_t"] - out["indicador_t1"]
    # alvo
    out["indicador_t"] = alvo["indicador_pct"]
    out["atingiu_meta_t"] = alvo["atingiu_meta"]
    out["gap_meta_t"] = alvo["gap_meta_pp"]
    return out.reset_index()


# ---------------------------------------------------------------------------
# ABTs
# ---------------------------------------------------------------------------

COLUNAS_ALVO = ["indicador_t", "atingiu_meta_t", "gap_meta_t"]


def build_abt_municipio(gold_dir: Path = GOLD_DIR) -> pd.DataFrame:
    dim = pd.read_parquet(gold_dir / "dim_municipio.parquet")
    indicador = pd.read_parquet(gold_dir / "indicador_municipio.parquet")
    metas = pd.read_parquet(gold_dir / "metas_municipio.parquet")
    ideb = inep.read_ideb_anos_iniciais(_zip_xlsx("ideb_anos_iniciais"))
    estatico = bloco_estatico()

    partes = []
    for ano_alvo in ANOS_ALVO:
        base = bloco_indicador(indicador, metas, ano_alvo)
        base.insert(0, "ano_alvo", ano_alvo)
        base = base.merge(bloco_censo_escolar(ano_alvo), on="id_municipio", how="left")
        base = base.merge(bloco_rendimento(ano_alvo), on="id_municipio", how="left")
        base = base.merge(bloco_ideb(ideb, ano_alvo), on="id_municipio", how="left")
        partes.append(base)
    abt = pd.concat(partes, ignore_index=True)
    abt = abt.merge(estatico, on="id_municipio", how="left")
    abt = abt.merge(dim, on="id_municipio", how="left")
    # so municipios com identificacao territorial (os demais sao codigos fora do IBGE)
    abt = abt.dropna(subset=["sigla_uf"])
    abt["log_populacao"] = np.log1p(abt["populacao"])
    colunas_frente = [
        "ano_alvo",
        "id_municipio",
        "nome_municipio",
        "sigla_uf",
        "nome_uf",
        "nome_regiao",
    ]
    outras = [c for c in abt.columns if c not in colunas_frente and c not in COLUNAS_ALVO]
    return (
        abt[colunas_frente + outras + COLUNAS_ALVO]
        .sort_values(["ano_alvo", "id_municipio"])
        .reset_index(drop=True)
    )


def build_abt_aluno(gold_dir: Path = GOLD_DIR) -> pd.DataFrame:
    """Alunos avaliados (presentes com prova preenchida) com atributos de escola.

    As variaveis municipais nao sao repetidas aqui; entram pela juncao com a ABT de
    municipio em `carregar_abt_aluno`, o que mantem o arquivo pequeno.
    """
    alunos = pd.read_parquet(gold_dir / "fato_aluno.parquet")
    p = alunos[(alunos["presente"] == 1) & (alunos["preencheu"] == 1)].copy()
    p = p.dropna(subset=["id_municipio", "id_escola"])
    p["id_municipio"] = p["id_municipio"].astype("int64")
    p["id_escola"] = p["id_escola"].astype("int64")
    p["rede"] = p["rede"].astype(str)

    escola = p.groupby(["ano", "id_escola"]).agg(
        escola_qtd_avaliados=("id_aluno", "size"),
    )
    todos = alunos.dropna(subset=["id_escola"]).copy()
    todos["id_escola"] = todos["id_escola"].astype("int64")
    presenca = todos.groupby(["ano", "id_escola"])["presente"].mean().rename("escola_taxa_presenca")
    escola = escola.join(100 * presenca).reset_index()
    p = p.merge(escola, on=["ano", "id_escola"], how="left")

    colunas = CHAVES_ALUNO + [
        "peso",
        "proficiencia",
        "escola_qtd_avaliados",
        "escola_taxa_presenca",
        "alfabetizado",
    ]
    return (
        p[colunas]
        .sort_values(["ano", "id_municipio", "id_escola", "id_aluno"])
        .reset_index(drop=True)
    )


FEATURES_MUNICIPAIS_EXCLUIDAS_DO_ALUNO = COLUNAS_ALVO + ["nome_municipio", "nome_uf", "sigla_uf"]


def carregar_abt_aluno(processed_dir: Path = PROCESSED_DIR) -> pd.DataFrame:
    """ABT de aluno completa: atributos do aluno e da escola mais o contexto
    municipal alinhado ao ano da prova (ano_alvo == ano)."""
    alunos = pd.read_parquet(processed_dir / "abt_aluno.parquet")
    municipio = pd.read_parquet(processed_dir / "abt_municipio.parquet")
    municipio = municipio.drop(columns=FEATURES_MUNICIPAIS_EXCLUIDAS_DO_ALUNO)
    municipio = municipio.rename(columns={"ano_alvo": "ano"})
    return alunos.merge(municipio, on=["ano", "id_municipio"], how="left")


def run(processed_dir: Path = PROCESSED_DIR) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    municipio = build_abt_municipio()
    municipio.to_parquet(processed_dir / "abt_municipio.parquet", index=False, compression="zstd")
    print(f"[abt] municipio: {len(municipio):,} linhas x {municipio.shape[1]} colunas")
    aluno = build_abt_aluno()
    aluno.to_parquet(processed_dir / "abt_aluno.parquet", index=False, compression="zstd")
    print(f"[abt] aluno: {len(aluno):,} linhas x {aluno.shape[1]} colunas")


if __name__ == "__main__":
    run()
