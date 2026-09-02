.PHONY: validate test doctor checklist

validate:
	./bin/iosflow validate

test:
	python3 -m unittest discover -s tests -v

doctor:
	./bin/iosflow doctor

checklist:
	./bin/iosflow checklist . --purpose commit
