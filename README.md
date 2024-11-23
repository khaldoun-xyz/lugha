# evaluate your language level

----

# how to get going on your laptop
- create a .env file and provide relevant parameters
- create a virtualenv or conda environment using the requirements.txt file & activate it
- navigate to `src` & start chatting with `python chat.py -u <your_user_name>`
- App Interface: To use the app interface, navigate to `src` & run: `python app.py`

----

# build & run docker
- `docker build -t groq .`
- `docker run -p 5000:5000 --env-file .env groq`

