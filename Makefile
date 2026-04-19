.PHONY: install playwright test run-demo parse apply clean

install:
	python -m pip install -r requirements.txt

playwright:
	python -m playwright install chromium

test:
	pytest -v

run-demo:
	python main.py demo-local-form

parse:
	python main.py parse-resume --resume data/sample_resume.txt

apply:
	python main.py apply --resume data/sample_resume.txt --url http://localhost:8000/local_job_application_form.html --no-submit

clean:
	rm -rf outputs/*.png outputs/*.json outputs/*.html outputs/run.log || true
