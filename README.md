# SAVIO — Gestion du Service Après-Vente

SAVIO est une application web de gestion du **Service Après-Vente** développée avec **Django 5.2**, **SQLite** (dev) / **PostgreSQL** (prod), **Bootstrap 5** et le template d'administration **NiceAdmin**. Elle couvre le cycle complet d'une demande SAV (création, affectation, suivi, clôture) avec historique, notifications internes, reporting, import/export CSV et paramétrage.

---

## 1. Fonctionnalités

- **Authentification** : login / logout / changement de mot de passe / profil
- **Rôles** : Administrateur, Technicien, Utilisateur — chacun avec son interface et ses permissions
- **Clients** : CRUD complet (particuliers / entreprises)
- **Techniciens** : CRUD, lien optionnel vers un compte utilisateur
- **Demandes SAV (tickets)** : référence auto-générée `SAV-YYYYMMDD-XXXX`, statuts, priorités, affectation, commentaires, clôture
- **Historique** : trace automatique de toutes les actions (création, modification, statut, affectation, commentaire, clôture, suppression)
- **Notifications internes** : cloche dans la barre supérieure, notifications automatiques lors des affectations et changements de statut
- **Dashboard administrateur** : 8 indicateurs clés + 3 graphiques (ApexCharts)
  - *Line* : évolution des demandes sur 30 jours
  - *Pie* : répartition par statut
  - *Bar* : nombre de tickets par technicien
- **Rapports** : global, tickets, par technicien, par client
- **Import / Export CSV** : clients, techniciens, demandes, historique
- **Configuration** : paramètres généraux, statuts et priorités personnalisables
- **Assistant IA local** (optionnel) : `llama-cpp-python` — diagnostic ticket pour les techniciens, chatbot utilisateur, résumés d'activité pour l'admin (voir [`apps/assistant/README.md`](apps/assistant/README.md))
- **Pages d'erreur** : 403 / 404 / 500 intégrées

---

## 2. Stack technique

- **Python** : 3.10 – 3.13 recommandé (3.14 fonctionne avec `Pillow>=11.0.0` comme indiqué dans `requirements.txt`)
- **Framework** : Django 5.2
- **Base de données** : SQLite (par défaut, dev) ou PostgreSQL (prod)
- **Frontend** : Bootstrap 5 + Bootstrap Icons
- **UI & Scripts** : jQuery 3 + Simple-DataTables
- **Graphiques** : ApexCharts (dashboard)
- **Thème** : NiceAdmin (intégré sous `static/niceadmin/`)
- **Production** : whitenoise (fichiers statiques) et gunicorn

---

## 3. Arborescence

```text
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
