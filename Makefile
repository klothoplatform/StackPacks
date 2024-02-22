PHONY: run test-backend black

run:
	PYTHONPATH=. \
	DYNAMODB_HOST=http://localhost:8000 \
	AUTH0_DOMAIN="klotho-dev.us.auth0.com" \
	AUTH0_AUDIENCE="A0sIE3wvh8LpG8mtJEjWPnBqZgBs5cNM" \
	pipenv run gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3000 --log-level debug src.main:app 

test-backend:
	PYTHONPATH=. pipenv run coverage run --source=src -m unittest discover
	PYTHONPATH=. pipenv run coverage report -m --fail-under 68

black:
	pipenv run black .