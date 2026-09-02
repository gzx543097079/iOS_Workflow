.PHONY: validate test doctor

validate:
	./bin/iosflow validate

test:
	python3 -m unittest discover -s tests -v

doctor:
	./bin/iosflow doctor

