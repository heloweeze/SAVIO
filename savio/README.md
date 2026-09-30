# SAVIO — Gestion du Service Après-Vente

SAVIO est une application web de gestion du **Service Après-Vente** développée
avec **Django 5.2**, **SQLite** (dev) / **PostgreSQL** (prod), **Bootstrap 5**
et le template d'administration **NiceAdmin**. Elle couvre le cycle complet
d'une demande SAV (création, affectation, suivi, clôture) avec historique,
notifications internes, reporting, import/export CSV et paramétrage.

## 1. Fonctionnalités

- **Authentification** : login / logout / changement de mot de passe / profil
- **Rôles** : Administrateur, Technicien, Utilisateur — chacun avec son interface et ses permissions
- **Clients** : CRUD complet (particuliers / entreprises)
- **Techniciens** : CRUD, lien optionnel vers un compte utilisateur
- **Demandes SAV (tickets)** : référence auto-générée `SAV-YYYYMMDD-XXXX`, statuts, priorités, affectation, commentaires, clôture
- **Historique** : trace automatique de toutes les actions (création, modification, statut, affectation, commentaire, clôture, suppression)
- **Notifications internes** : cloche dans la barre supérieure, notifications automatiques lors des affectations et changements de statut
- **Dashboard administrateur** : 8 indicateurs clés + 3 graphiques (ApexCharts)
  - Line : évolution des demandes sur 30 jours
  - Pie : répartition par statut
  - Bar : nombre de tickets par technicien
- **Rapports** : global, tickets, par technicien, par client
- **Import / Export CSV** : clients, techniciens, demandes, historique
- **Configuration** : paramètres généraux, statuts et priorités personnalisables
- **Assistant IA local** (optionnel) : `llama-cpp-python` — diagnostic ticket pour les techniciens, chatbot utilisateur, résumés d'activité pour l'admin (voir [`apps/assistant/README.md`](apps/assistant/README.md))
- **Pages d'erreur 403 / 404 / 500** intégrées

## 2. Stack technique

- **Python 3.10 – 3.13 recommandé** (3.14 fonctionne avec `Pillow>=11.0.0` comme indiqué dans `requirements.txt`)
- Django 5.2
- SQLite (par défaut, dev) ou PostgreSQL (prod)
- Bootstrap 5 + Bootstrap Icons
- jQuery 3 + Simple-DataTables
- ApexCharts (graphiques du dashboard)
- Thème NiceAdmin (copié sous `static/niceadmin/`)
- whitenoise pour le service des statiques en production
- gunicorn pour l'exécution en production

## 3. Arborescence

```
savio/
├── manage.py
├── requirements.txt
├── .env.example
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/        # User custom + rôles + auth + management commands
│   ├── clients/
│   ├── technicians/
│   ├── tickets/         # Demandes SAV + commentaires
│   ├── history/         # Traçabilité
│   ├── notifications/
│   ├── dashboard/       # Dashboards + endpoints JSON pour ApexCharts
│   ├── reports/
│   ├── importexport/
│   └── configuration/
├── templates/
│   ├── base.html
│   ├── base_admin.html
│   ├── base_user.html
│   ├── partials/
│   └── <app>/...
├── static/
│   ├── niceadmin/       # assets du template (css, js, img, vendor)
│   ├── css/savio.css
│   └── js/savio.js
└── media/               # uploads (avatars...)
```

## 4. Installation locale

```bash
# 1. Cloner / récupérer le projet
cd savio

# 2. Créer un environnement virtuel
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Préparer l'environnement
cp .env.example .env
# Modifier DJANGO_SECRET_KEY dans .env

# 5. Migrations
python manage.py makemigrations
python manage.py migrate

# 6. Créer un compte administrateur (admin / admin)
python manage.py create_admin

# 7. (Optionnel) Charger des données de démonstration
python manage.py seed_savio

# 8. Lancer le serveur de développement
python manage.py runserver
```

L'application est accessible sur <http://127.0.0.1:8000/>.

## 5. Comptes de démonstration (après `seed_savio`)

| Rôle            | Login    | Mot de passe |
|-----------------|----------|--------------|
| Administrateur  | `admin`  | `admin`      |
| Technicien      | `alice`  | `alice`      |
| Technicien      | `bruno`  | `bruno`      |
| Technicien      | `claire` | `claire`     |
| Utilisateur     | `user1`  | `user1`      |
| Utilisateur     | `user2`  | `user2`      |
| Utilisateur     | `user3`  | `user3`      |

> **Important** : changez ces mots de passe avant toute mise en production.

## 6. Commandes de gestion

```bash
# Recréer la base de démonstration (reset + reseed)
python manage.py seed_savio --reset

# Créer / réinitialiser l'administrateur avec paramètres personnalisés
python manage.py create_admin --username root --email root@savio.fr --password S3cret!

# Lancer les tests
python manage.py test

# Collecter les statiques (production)
python manage.py collectstatic --noinput
```

## 7. Configuration (`.env`)

| Variable                 | Rôle                                           | Exemple                               |
|--------------------------|------------------------------------------------|---------------------------------------|
| `DJANGO_SETTINGS_MODULE` | Module de settings utilisé                     | `config.settings.dev` ou `prod`       |
| `DJANGO_SECRET_KEY`      | Clé secrète Django                              | `change-me-please-32-chars-min`       |
| `DJANGO_DEBUG`           | Mode debug (True/False)                        | `False` en production                 |
| `DJANGO_ALLOWED_HOSTS`   | Hôtes autorisés (séparés par virgule)          | `savio.example.com,www.example.com`   |
| `DJANGO_TIME_ZONE`       | Fuseau horaire                                 | `Europe/Paris`                        |
| `DJANGO_LANGUAGE_CODE`   | Langue                                         | `fr`                                  |
| `DATABASE_URL`           | URL PostgreSQL (prod) — vide = SQLite          | `postgres://user:pwd@host:5432/savio` |
| `EMAIL_BACKEND`          | Backend d'envoi d'emails                       | `django.core.mail.backends.smtp...`   |
| `DEFAULT_FROM_EMAIL`     | Expéditeur par défaut                          | `SAVIO <no-reply@savio.fr>`           |

## 8. Déploiement (exemple générique)

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
pip install -r requirements.txt psycopg[binary]
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

Placez un serveur web (Nginx, Apache, Caddy) devant Gunicorn pour TLS et le
service des fichiers statiques (répertoire `staticfiles/`). Les fichiers
utilisateurs (avatars, etc.) sont servis depuis `media/`.

### Checklist production

- [ ] Définir une `DJANGO_SECRET_KEY` forte (≥ 50 caractères)
- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_ALLOWED_HOSTS` renseigné avec vos domaines
- [ ] Base PostgreSQL configurée via `DATABASE_URL`
- [ ] HTTPS actif (Nginx + certbot par exemple)
- [ ] `collectstatic` exécuté à chaque déploiement
- [ ] Sauvegarde régulière de la base et du dossier `media/`

## 9. Tests

Des tests unitaires et d'intégration couvrent les briques critiques :

```bash
python manage.py test
```

Tests fournis :

- `apps.accounts.tests` — modèle User, rôles, synchronisation des groupes, protection des routes
- `apps.clients.tests` — affichage particulier/entreprise, URL canonique
- `apps.tickets.tests` — génération de référence, gestion `closed_at`, helpers de priorité

## 10. Sécurité

- CSRF actif sur tous les formulaires (`{% csrf_token %}`)
- Décorateurs `@login_required`, `@admin_required`, `@staff_required`
- Mixins `AdminRequiredMixin`, `StaffRequiredMixin` pour les CBV
- Mots de passe hachés (PBKDF2 par défaut)
- Whitenoise pour servir les statiques avec `Cache-Control` approprié
- Redirections vers `/auth/login/` pour les utilisateurs non authentifiés

## 11. Licence / Auteur

Projet académique SAVIO. Le thème **NiceAdmin** est distribué par BootstrapMade
sous licence libre (voir dossier NiceAdmin/).
