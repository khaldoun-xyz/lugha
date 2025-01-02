# evaluate your language level

----

Install pre-commit hook
- run `pre-commit install`
----

# how to get going on your laptop
- create a .env file and provide relevant parameters
- create a virtualenv or conda environment using the requirements.txt file & activate it
- App Interface: To use the app interface, navigate to `src` & run: `python -m flask_interface.app`

----

# build & run docker
- `docker build -t groq .`
- `docker run -p 5000:5000 --env-file .env groq`
