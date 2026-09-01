# Predição e Inteligência Analítica para Alfabetização no Brasil

Projeto da Fase 3 do MBA em AI Scientist (FIAP / POSTECH). A proposta é usar a camada Gold construída na Fase 2, sobre o Indicador Criança Alfabetizada, para treinar modelos supervisionados capazes de prever se um aluno será considerado alfabetizado ao final do 2º ano do ensino fundamental, e transformar esses modelos em inteligência para quem decide política educacional: quais fatores pesam, quais municípios estão em risco, quais territórios se parecem e quem tende a não atingir as metas.

## Contexto do problema

A alfabetização na idade certa é um dos principais indicadores de desenvolvimento educacional e social. O Compromisso Nacional Criança Alfabetizada mobiliza União, estados e municípios para que todas as crianças estejam alfabetizadas até o fim do 2º ano, e o Inep definiu, com a Pesquisa Alfabetiza Brasil, o corte de 743 pontos na escala Saeb como o nível a partir do qual uma criança é considerada alfabetizada. Desse corte nasce o Indicador Criança Alfabetizada, medido por avaliações estaduais e comparado com metas anuais por município e por UF até 2030.

Olhar só o número atual não basta. O gestor precisa antecipar risco, identificar territórios vulneráveis e entender quais fatores mais pesam no resultado. É esse o papel da ciência de dados aqui.

## Objetivo analítico

Construir uma pipeline completa de Machine Learning, do dado da Gold ao modelo interpretado, que:

1. preveja se um aluno será alfabetizado ou não, a partir de variáveis educacionais, territoriais e socioeconômicas;
2. estime o risco de cada município não atingir a meta do ano seguinte;
3. agrupe municípios em perfis com padrões semelhantes;
4. explique quais variáveis mais influenciam as predições.

## Etapas do projeto

O trabalho segue a ordem abaixo. Cada etapa tem um notebook e o código reutilizável fica em `src/`.

| Etapa | Notebook | O que entrega |
|---|---|---|
| Base e qualidade | `notebooks/01_base_gold_e_qualidade.ipynb` | Gold reconstruída com dado real do Inep, bases analíticas e checagens |
| EDA e hipóteses | `notebooks/02_eda_e_hipoteses.ipynb` | distribuições, correlações, hipóteses testadas e decisões de modelagem |
| Modelo do aluno | `notebooks/03_modelo_aluno.ipynb` | pipeline supervisionada, validação e teste temporal |
| Risco municipal | `notebooks/04_modelo_municipio_risco.ipynb` | modelo de risco de não atingir a meta, backtest e projeção |
| Perfis territoriais | `notebooks/05_perfis_territoriais.ipynb` | clusterização e perfis de vulnerabilidade |
| Interpretabilidade | `notebooks/06_interpretabilidade_e_aplicacao.ipynb` | SHAP, importâncias e respostas às perguntas de negócio |

## Estrutura do repositório

```
.
├── data/               raw e external (baixados), gold e processed (versionados)
├── notebooks/          um notebook por etapa, numerados
├── src/
│   ├── data/           catálogo de fontes, download, parsers, gold e bases analíticas
│   ├── preprocessing/  pipeline de preprocessamento e engenharia de atributos
│   ├── modeling/       treino, busca de hiperparâmetros e persistência
│   ├── evaluation/     métricas, validação temporal e interpretabilidade
│   └── visualization/  estilo, rótulos de negócio e gráficos
├── models/             pipelines serializados e métricas
├── tests/              testes de parsers, features e pipeline
├── reports/            rankings, tabelas e apresentação executiva
├── images/             figuras exportadas dos notebooks
├── docs/               documentação técnica e decisões analíticas
├── Makefile            atalhos: setup, data, gold, abt, train, notebooks, test, lint
├── pyproject.toml      dependências gerenciadas pelo uv
└── requirements.txt    exportado do lock, para quem preferir pip
```

## Como rodar

```bash
uv sync            # ou: pip install -r requirements.txt
make data          # baixa as fontes do Inep e do IBGE
make gold          # reconstroi a camada Gold
make abt           # monta as bases analiticas
make notebooks     # executa os notebooks na ordem
make test          # roda os testes
```

As seções de descrição da base, modelagem, métricas, resultados, limitações e aplicação prática são preenchidas conforme as etapas avançam.
