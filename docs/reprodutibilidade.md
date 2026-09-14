# Reprodutibilidade

Como executar o projeto do zero, o que cada comando produz, quanto tempo leva e o que é determinístico.

## Pré-requisitos

- Python 3.12 e [uv](https://docs.astral.sh/uv/) (ou pip, com `requirements.txt`)
- cerca de 2 GB de disco para as fontes brutas e 8 GB de memória para o modelo do aluno
- acesso à internet só para `make data`; tudo o mais roda offline

## Dois caminhos

**Caminho curto (sem baixar as fontes).** A Gold (`data/gold/`), as bases analíticas (`data/processed/`) e a malha municipal estão versionadas. Basta:

```bash
uv sync
make notebooks      # executa os seis notebooks na ordem e regenera images/, models/ e reports/
make test           # testes de parsers, bases, pipeline e métricas
```

**Caminho completo (do dado bruto).**

```bash
uv sync
make data           # baixa 22 fontes (cerca de 900 MB) com verificação de integridade
make gold           # reconstrói a Gold em data/gold (cerca de 1 min)
make abt            # monta as bases analíticas (cerca de 6 min; as planilhas do Inep são lentas de ler)
make notebooks
make test
```

`make train` roda a busca de hiperparâmetros e o ajuste final pela linha de comando (sem notebook) e sobrescreve `models/`.

**Modo rápido.** O notebook 03 leva perto de uma hora e usa 6 GB de memória. Para conferir o fluxo em poucos minutos, sem sobrescrever os artefatos com um modelo pior, rode uma cópia com a variável de ambiente:

```bash
cp notebooks/03_modelo_aluno.ipynb /tmp/03_rapido.ipynb
TC_RAPIDO=1 uv run jupyter nbconvert --to notebook --execute /tmp/03_rapido.ipynb
```

No modo rápido o treino usa 200 mil alunos, a busca 30 mil e poucas iterações; as métricas ficam um pouco abaixo das reportadas e servem para validar a execução. O notebook 03 não deve rodar em paralelo com outro processo pesado; com 15 GB de memória, a execução simultânea com o notebook 06 foi encerrada pelo sistema.

## Tempo de execução aproximado

| Etapa | Tempo (8 núcleos) |
|---|---|
| download | 5 a 15 min, conforme o servidor do Inep |
| gold | 1 min |
| abt | 6 min |
| notebook 01 | 1 min |
| notebook 02 | 2 min |
| notebook 03 (modelo do aluno) | cerca de 60 min (3 min no modo rápido) |
| notebook 04 (risco municipal) | 5 min |
| notebook 05 (perfis) | 1 min |
| notebook 06 (interpretabilidade) | 3 min |

## Determinismo

- `random_state=42` em todo passo estocástico (splits, busca aleatória, modelos, amostras, K-Means, PCA).
- A busca aleatória de hiperparâmetros é reproduzível para o mesmo ambiente; versões diferentes de LightGBM ou scikit-learn podem mudar os melhores hiperparâmetros por diferenças numéricas pequenas. As versões exatas estão em `uv.lock` e `requirements.txt`.
- O paralelismo fica em um nível só (busca em paralelo com modelo em uma thread, ou o contrário), o que mantém o resultado idêntico entre execuções.
- Os downloads são conferidos por MD5 (zips do Inep) e SHA-256 (`data/manifest.json`). Se uma fonte mudar no servidor, o log avisa.

## Estrutura dos artefatos gerados

| Pasta | Conteúdo | Versionado |
|---|---|---|
| `data/raw`, `data/external` | fontes brutas | não (exceto a malha) |
| `data/gold` | Gold em Parquet | sim |
| `data/processed` | ABTs em Parquet | sim |
| `models` | pipelines completos (`.joblib`), metadados (`.json`), predições fora da amostra e do backtest (`.parquet`) | sim |
| `reports` | rankings de risco, perfis, importâncias, apresentação | sim |
| `images` | figuras dos notebooks | sim |

## Problemas conhecidos

- O servidor `download.inep.gov.br` tem cadeia de certificado incompleta e às vezes recusa conexões; o download tenta seis vezes com espera crescente. Se falhar, basta rodar `make data` de novo (arquivos já baixados são pulados).
- A leitura das planilhas do Censo Escolar (65 mil linhas cada) é o gargalo de `make abt`.
- O notebook 03 usa em torno de 6 GB de memória no ajuste final com 1,85 milhão de alunos.
