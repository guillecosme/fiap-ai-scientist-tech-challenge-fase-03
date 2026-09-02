# Fontes de dados

Todas as fontes são públicas, baixadas por `make data` (módulo `src/data/download.py`) a partir do catálogo em `src/data/sources.py`. Nenhuma exige credencial ou projeto de billing. Os arquivos brutos ficam em `data/raw/` (fontes principais) e `data/external/` (enriquecimento) e não são versionados; o que vai para o git é a Gold e as bases analíticas derivadas delas.

## Por que não a Base dos Dados

Na Fase 2 a pipeline lia da Base dos Dados. O microdado do Indicador Criança Alfabetizada só sai de lá pelo BigQuery, que exige projeto de billing, e por isso parte das entidades acabou simulada. O Inep passou a publicar diretamente os resultados por município, as metas até 2030 e, em agosto de 2025, os microdados por aluno. Nesta fase as fontes vêm direto do Inep e do IBGE, o que elimina a simulação e mantém o mesmo esquema da Gold.

## Fontes principais (Inep)

| Nome no catálogo | Conteúdo | Grão | Anos | Observações |
|---|---|---|---|---|
| `ica_municipios_2023/2024/2025` | Percentual de alunos alfabetizados, metas 2024 a 2030, nível e participação | município (rede municipal) | 2023, 2024, 2025 | metas em formato largo (uma coluna por ano); cada planilha traz também os anos anteriores |
| `ica_ufs_2023/2024/2025` | O mesmo por UF e Brasil, com Saeb 2019 e 2021 | UF | 2023 a 2025 | rede pública |
| `microdados_2024`, `microdados_2025` | Avaliação estadual da alfabetização por aluno: presença, peso, proficiência, indicador de alfabetizado, escola (mascarada), rede, município | aluno | 2024, 2025 | csv com `;` e latin-1; 2025 traz também respostas por item |

A regra do indicador: aluno alfabetizado é quem atinge 743 pontos na escala Saeb (`IN_ALFABETIZADO = 1`). O percentual do município é calculado sobre os alunos avaliados (presentes com prova preenchida).

## Enriquecimento (Inep e IBGE)

| Nome no catálogo | Conteúdo | Grão | Anos | Uso no projeto |
|---|---|---|---|---|
| `inse_2023` | Nível socioeconômico médio dos alunos e distribuição por nível | município x rede x localização | 2023 | contexto socioeconômico |
| `afd_2024/2025` | Adequação da formação docente (grupos 1 a 5) por etapa | município x rede x localização | 2024, 2025 | qualidade docente nos anos iniciais |
| `atu_2024/2025` | Média de alunos por turma por etapa | idem | 2024, 2025 | condição de ensino |
| `tdi_2024/2025` | Taxa de distorção idade-série por etapa e ano escolar | idem | 2024, 2025 | fluxo escolar |
| `dsu_2024/2025` | Percentual de docentes com curso superior | idem | 2024, 2025 | qualidade docente |
| `rend_2023/2024` | Taxas de aprovação, reprovação e abandono por ano escolar | idem | 2023, 2024 | fluxo escolar do ano anterior |
| `ideb_anos_iniciais` | IDEB, nota Saeb e fluxo dos anos iniciais | município x rede | 2005 a 2025 (bienal) | série histórica: nível e tendência |
| `ibge_censo_2022` | População residente, área e densidade | município | 2022 | porte e territorialidade |
| `ibge_pib` | PIB a preços correntes e participação dos setores no valor adicionado | município | 2021, 2022 | renda e estrutura produtiva |

## Alinhamento temporal

Para prever o resultado do ano *t* (prova aplicada entre outubro e novembro), só entram variáveis conhecidas antes disso:

- Censo Escolar de *t* (data de referência no fim de maio): formação docente, alunos por turma, distorção, docentes com superior;
- rendimento escolar de *t-1* (aprovação, reprovação, abandono do ano letivo anterior);
- IDEB até *t-1*;
- resultado do indicador em *t-1* e a meta de *t*;
- Censo 2022, PIB do último ano disponível anterior a *t*, INSE 2023.

Essa regra é aplicada em `src/data/abt.py` e verificada em `tests/`.

## Integridade dos downloads

O servidor `download.inep.gov.br` publica uma cadeia de certificado incompleta, o que faz a verificação TLS falhar em ambientes limpos. O download é feito por HTTP e a integridade é garantida de duas formas: os zips do Inep trazem um arquivo `MD5_*.txt` que é conferido depois da extração; para os demais arquivos, o SHA-256 é registrado em `data/manifest.json` na primeira execução e comparado nas seguintes.

## Fontes consideradas e não usadas

- FUNDEB (FNDE) e Cadastro Único (MDS): não têm download direto por município em formato aberto estável; ficam como evolução futura.
- Atlas do Desenvolvimento Humano (IDHM 2010): dado de 2010, já bastante defasado frente ao INSE 2023 e ao Censo 2022, que cobrem a mesma dimensão.
- PNAD: amostral, sem representatividade municipal.
