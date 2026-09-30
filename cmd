cd savio
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations && python manage.py migrate
python manage.py seed_savio
python manage.py runserver