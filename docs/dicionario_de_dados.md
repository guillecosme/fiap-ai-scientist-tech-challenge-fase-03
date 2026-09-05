# Dicionário de dados

Tabelas da camada Gold (`data/gold/`) e das bases analíticas (`data/processed/`). A Gold segue o contrato definido na Fase 2 (mesmos nomes de tabela e de campo), agora alimentada pelas fontes reais do Inep, e ganha a tabela `fato_aluno`. As chaves são consistentes entre as tabelas: `id_municipio` (código IBGE de 7 dígitos), `sigla_uf`, `ano`.

## Camada Gold

### dim_municipio
Um registro por município presente em qualquer planilha de resultados ou nos microdados (5.570).

| Campo | Tipo | Descrição |
|---|---|---|
| id_municipio | int | Código IBGE de 7 dígitos |
| nome_municipio | string | Nome do município |
| sigla_uf | string | Sigla da UF |
| id_uf | int | Código IBGE da UF (dois primeiros dígitos do município) |
| nome_uf | string | Nome da UF |
| nome_regiao | string | Grande região (Norte, Nordeste, Sudeste, Sul, Centro-Oeste) |

### fato_aluno
Grão aluno. Todos os estudantes do 2º ano listados pelas redes na avaliação estadual, presentes ou não (4,34 milhões em 2024 e 2025).

| Campo | Tipo | Descrição |
|---|---|---|
| ano | int | Ano da avaliação |
| sigla_uf | category | UF da escola |
| id_aluno | int | Identificador anônimo do aluno (não persiste entre anos) |
| id_escola | int (nulo permitido) | Código mascarado da escola, consistente dentro do ano |
| rede | category | Dependência administrativa: estadual, municipal, privada |
| id_municipio | int (nulo permitido) | Município da escola |
| presente | int | 1 se compareceu à prova de língua portuguesa |
| preencheu | int | 1 se a prova foi preenchida |
| peso | float | Peso amostral do aluno (nulo para ausentes) |
| proficiencia | float | Proficiência em língua portuguesa na escala Saeb (nulo para ausentes) |
| alfabetizado | int | 1 se proficiência >= 743; 0 caso contrário (inclusive ausentes) |

Regra de uso: o universo do indicador são os avaliados (`presente == 1 e preencheu == 1`). Ausentes não entram no denominador do percentual oficial.

### fato_alfabetizacao
Grão ano x município x rede, calculado a partir de `fato_aluno` reproduzindo o cálculo oficial (média ponderada pelo peso amostral). Diferença média para o número publicado pelo Inep: 0,02 ponto percentual.

| Campo | Tipo | Descrição |
|---|---|---|
| ano, id_municipio, nome_municipio, sigla_uf, id_uf, nome_regiao | | chaves e atributos da dimensão |
| rede | string | estadual, municipal ou privada |
| qtd_avaliados | int | Alunos presentes com prova preenchida |
| qtd_alfabetizados | int | Avaliados com proficiência >= 743 |
| media_proficiencia | float | Média ponderada da proficiência |
| indicador_pct | float | Percentual ponderado de alfabetizados (cálculo oficial) |
| indicador_pct_bruto | float | Percentual sem ponderação, para referência |
| meta_municipio | float | Meta do município no ano (a meta é definida para a rede municipal) |
| atingiu_meta | boolean | indicador_pct >= meta_municipio |
| gap_meta_pp | float | indicador_pct - meta_municipio, em pontos percentuais |

### indicador_municipio
Série oficial da rede municipal, 2023 a 2025, como publicada pelo Inep, comparada à meta. É a tabela usada pelo modelo de risco municipal.

| Campo | Tipo | Descrição |
|---|---|---|
| ano, id_municipio, nome_municipio, sigla_uf, id_uf, nome_uf, nome_regiao | | chaves e atributos |
| qtd_avaliados, qtd_alfabetizados, media_proficiencia | | volumes dos microdados (2024 e 2025; nulos em 2023) |
| indicador_pct | float | Percentual de alunos alfabetizados publicado pelo Inep |
| nivel | int | Nível de alfabetização do município (0 a 5), como divulgado |
| participacao_pct | float | Percentual de participação dos alunos na prova |
| meta_municipio | float | Meta do ano (não há meta para 2023, ano de linha de base) |
| atingiu_meta | boolean | indicador_pct >= meta_municipio |
| gap_meta_pp | float | Distância para a meta em pontos percentuais |

### metas_municipio
Metas anuais por município, 2024 a 2030, em formato longo (`id_municipio`, `ano`, `meta_pct`). Quando a mesma meta aparece em mais de uma planilha, vale a versão com mais casas decimais.

### evolucao_temporal
Série por município com `indicador_ano_anterior` e `variacao_pp`.

### comparacao_meta_uf
Indicador por UF e Brasil (`sigla_uf = BR`) contra a meta estadual. A coluna `fonte` separa o indicador (2023 a 2025) do Saeb 2019 e 2021, incluídos como referência histórica.

### metas_uf
Metas anuais por UF e Brasil, 2024 a 2030.

## Campos derivados

- **indicador_pct**: soma dos pesos dos alfabetizados dividida pela soma dos pesos dos avaliados, vezes 100.
- **atingiu_meta**: verdadeiro quando `indicador_pct >= meta`.
- **gap_meta_pp**: `indicador_pct - meta`, em pontos percentuais; negativo significa abaixo da meta.
- **nome_regiao**: derivado do primeiro dígito do código da UF.

## Bases analíticas

As bases analíticas (`abt_municipio.parquet` e `abt_aluno.parquet`) são descritas em `docs/metodologia.md`, com a lista de variáveis, o ano de referência de cada uma e a regra de alinhamento temporal.
