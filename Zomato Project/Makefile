.PHONY: install ingest test

install:
	py -m pip install -e .

ingest:
	py -m scripts.ingest -v --report data/ingest-report.json

filter:
	py -m scripts.filter --location Bengaluru --budget medium --cuisine "North Indian" --min-rating 4.0 --top 5

serve:
	py -m scripts.serve

test:
	py -m pytest tests/ -q
