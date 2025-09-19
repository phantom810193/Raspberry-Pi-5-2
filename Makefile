.PHONY: test

TEST_CMD ?= pytest -q

test:
	$(TEST_CMD)
