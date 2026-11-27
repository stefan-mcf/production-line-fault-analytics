PYTHON ?= python3

.PHONY: demo check
demo:
	$(PYTHON) analytics.py data/events-01.csv data/events-02.csv --review data/practice-review.json --out outputs/demo

check:
	$(PYTHON) -B -m unittest discover -s tests -v
