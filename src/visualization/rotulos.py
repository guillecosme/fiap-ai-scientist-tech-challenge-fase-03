"""Rotulos de negocio para as variaveis do projeto.

Os graficos e as tabelas de interpretabilidade usam estes nomes no lugar dos
identificadores tecnicos, para que um gestor entenda o que cada variavel mede
sem consultar o dicionario de dados.
"""

from __future__ import annotations

ROTULOS: dict[str, str] = {
    # alvo e historico do indicador
    "alfabetizado": "Aluno alfabetizado",
    "indicador_t": "% alfabetizados no ano",
    "atingiu_meta_t": "Atingiu a meta do ano",
    "gap_meta_t": "Distância para a meta (p.p.)",
    "indicador_t1": "% alfabetizados no ano anterior",
    "indicador_t2": "% alfabetizados dois anos antes",
    "nivel_t1": "Nível de alfabetização no ano anterior (0 a 5)",
    "participacao_t1": "Participação na prova no ano anterior (%)",
    "variacao_t1": "Variação do indicador no ano anterior (p.p.)",
    "meta_t1": "Meta do ano anterior (%)",
    "gap_meta_t1": "Distância para a meta no ano anterior (p.p.)",
    "meta_t": "Meta do ano (%)",
    "salto_necessario": "Salto necessário para a meta (p.p.)",
    # censo escolar
    "afd_ai_grupo1_pct": "Docentes com formação adequada, anos iniciais (%)",
    "afd_ai_grupo5_pct": "Docentes sem licenciatura, anos iniciais (%)",
    "afd_inf_grupo1_pct": "Docentes com formação adequada, educação infantil (%)",
    "alunos_por_turma_ai": "Alunos por turma, anos iniciais",
    "alunos_por_turma_2ano": "Alunos por turma no 2o ano",
    "alunos_por_turma_pre": "Alunos por turma na pré-escola",
    "distorcao_ai_pct": "Distorção idade-série, anos iniciais (%)",
    "distorcao_2ano_pct": "Distorção idade-série no 2o ano (%)",
    "docentes_superior_ai_pct": "Docentes com curso superior, anos iniciais (%)",
    "docentes_superior_inf_pct": "Docentes com curso superior, educação infantil (%)",
    "aprovacao_ai_pct": "Taxa de aprovação, anos iniciais (%)",
    "aprovacao_1ano_pct": "Taxa de aprovação no 1o ano (%)",
    "aprovacao_2ano_pct": "Taxa de aprovação no 2o ano (%)",
    "reprovacao_ai_pct": "Taxa de reprovação, anos iniciais (%)",
    "abandono_ai_pct": "Taxa de abandono, anos iniciais (%)",
    # ideb
    "ideb_ultimo": "IDEB anos iniciais (última edição)",
    "ideb_nota_lp_ultimo": "Nota de português no Saeb 5o ano (última edição)",
    "ideb_rendimento_ultimo": "Indicador de rendimento do IDEB (última edição)",
    "ideb_anterior": "IDEB anos iniciais (edição anterior)",
    "ideb_variacao": "Variação do IDEB entre edições",
    "ideb_tendencia": "Tendência do IDEB (pontos por edição)",
    # territorio e renda
    "populacao": "População (Censo 2022)",
    "log_populacao": "População (escala log)",
    "area_km2": "Área (km²)",
    "densidade_hab_km2": "Densidade demográfica (hab/km2)",
    "pib_mil_reais": "PIB (mil R$)",
    "pib_per_capita": "PIB per capita (R$)",
    "pct_vab_agro": "Peso da agropecuária na economia (%)",
    "pct_vab_industria": "Peso da indústria na economia (%)",
    "pct_vab_adm_publica": "Peso da administração pública na economia (%)",
    "pct_vab_servicos": "Peso dos serviços na economia (%)",
    "capital": "Capital de UF",
    # socioeconomico
    "inse_medio": "Nível socioeconômico médio dos alunos (INSE)",
    "inse_qtd_alunos": "Alunos com INSE calculado",
    "pct_alunos_rural": "Alunos em escolas rurais (%)",
    "inse_pct_nivel_baixo": "Alunos nos níveis socioeconômicos baixos (%)",
    "inse_pct_nivel_alto": "Alunos nos níveis socioeconômicos altos (%)",
    # aluno e escola
    "rede": "Rede de ensino",
    "sigla_uf": "UF",
    "nome_regiao": "Região",
    "peso": "Peso amostral",
    "proficiencia": "Proficiência em português (Saeb)",
    "escola_qtd_avaliados": "Alunos avaliados na escola",
    "escola_taxa_presenca": "Presença na prova na escola (%)",
    "ano": "Ano da avaliação",
    "ano_alvo": "Ano-alvo",
}


def rotulo(nome: str) -> str:
    """Rotulo de negocio da variavel; trata as colunas one-hot (prefixo=valor)."""
    if nome in ROTULOS:
        return ROTULOS[nome]
    for sep in ("=", "_"):
        base, _, valor = nome.partition(sep)
        if base in ROTULOS and valor:
            return f"{ROTULOS[base]}: {valor}"
    return nome


def rotular(nomes) -> list[str]:
    return [rotulo(n) for n in nomes]
