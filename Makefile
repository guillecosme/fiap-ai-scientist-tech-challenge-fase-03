.PHONY: help setup lint test data gold abt train notebooks requirements clean

PY = uv run python

help:
	@echo "Setup e qualidade:"
	@echo "  setup         instala as dependencias com uv"
	@echo "  lint          roda o ruff"
	@echo "  test          roda a suite de testes"
	@echo "  requirements  exporta requirements.txt a partir do uv.lock"
	@echo ""
	@echo "Dados (na ordem):"
	@echo "  data          baixa as fontes do Inep e do IBGE para data/raw e data/external"
	@echo "  gold          reconstroi a camada Gold no contrato da fase 2 em data/gold"
	@echo "  abt           monta as bases analiticas de aluno e municipio em data/processed"
	@echo ""
	@echo "Modelos e notebooks:"
	@echo "  train         treina e persiste os modelos em models/"
	@echo "  notebooks     executa os notebooks de ponta a ponta, na ordem"
	@echo "  clean         limpa caches"

setup:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest -q

requirements:
	uv export --no-dev --no-hashes --no-emit-project -o requirements.txt

data:
	$(PY) -m src.data.download

gold:
	$(PY) -m src.data.gold

abt:
	$(PY) -m src.data.abt

train:
	$(PY) -m src.modeling.train

notebooks:
	for nb in notebooks/0*.ipynb; do \
		uv run jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 $$nb || exit 1; \
	done

clean:
	rm -rf .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
