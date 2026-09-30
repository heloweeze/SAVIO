# Assistant IA local — SAVIO

App Django qui intègre un **assistant fonctionnant entièrement en Python pur**.
Aucune dépendance externe : ni librairie tierce, ni modèle à télécharger, ni
service à lancer à côté. Tout repose sur la stdlib Python (modules `re` et
`unicodedata`) et sur deux structures de données déclaratives :

- une **base de connaissances** de motifs techniques (mots-clés + diagnostic +
  étapes + questions),
- un **catalogue d'intentions** de chatbot (mots-clés + réponses templates).

## 1. Trois usages couverts

| Usage                     | Rôle          | Vue                                | Comment c'est calculé |
|---------------------------|---------------|------------------------------------|-----------------------|
| Diagnostic d'un ticket    | Admin / Tech  | `assistant:suggest`                | Détection de mots-clés sur sujet + description + commentaires, puis composition d'une réponse à partir de la base de connaissances |
| Chat libre                | Tous          | `assistant:chat_page`              | Reconnaissance d'intention parmi ~10 intents prédéfinis (salutation, créer ticket, suivre demande, délais, mot de passe, etc.). Détection automatique des références `SAV-YYYYMMDD-XXXX` pour répondre directement avec le statut du ticket |
| Résumé d'activité         | Admin         | `assistant:admin_panel`            | Synthèse textuelle à partir des stats SQL (templates conditionnels selon les seuils) |

## 2. Installation

**Rien à installer.** L'assistant est livré avec le code et utilise uniquement
la stdlib Python. Pas de pip, pas de modèle GGUF, pas d'Ollama.

Il suffit de :

1. Vérifier que `apps.assistant` est dans `INSTALLED_APPS` (déjà fait).
2. Vérifier que `path("assistant/", include("apps.assistant.urls", namespace="assistant"))`
   est dans `config/urls.py` (déjà fait).
3. (Optionnel) Mettre `ASSISTANT_ENABLED=1` dans `.env` (c'est la valeur par défaut).
4. Lancer le serveur — c'est tout.

## 3. Architecture

```
apps/assistant/
├── apps.py            # AppConfig
├── services.py        # KNOWLEDGE_BASE + INTENTS + 3 fonctions de génération
├── views.py           # 6 vues (3 AJAX + 2 pages + reset chat)
├── urls.py            # routes sous /assistant/
└── README.md          # ce fichier

templates/assistant/
├── chat.html          # page chat utilisateur
└── admin_panel.html   # page admin (status + bouton résumé)
```

## 4. Personnaliser l'assistant

### Ajouter une catégorie de diagnostic

Dans `services.py`, ajoute un dict à la liste `KNOWLEDGE_BASE` :

```python
{
    "category": "Mon nouveau cas",
    "keywords": ["mot1", "mot2", "expression cle"],
    "diagnosis": "Description courte de la cause probable.",
    "steps": [
        "Étape 1...",
        "Étape 2...",
    ],
    "questions": [
        "Question 1 ?",
        "Question 2 ?",
    ],
}
```

Les mots-clés doivent être **sans accents ni majuscules** (la normalisation
du texte est faite automatiquement avant comparaison).

### Ajouter une intention de chatbot

Dans `services.py`, ajoute un dict à la liste `INTENTS` :

```python
{
    "name": "ma_nouvelle_intention",
    "keywords": ["mot1", "mot2"],
    "responses": [
        "Réponse template. {name} sera remplacé par le prénom de l'utilisateur.",
    ],
},
```

L'ordre dans la liste compte : la première intention dont un mot-clé matche
gagne. Mets les plus spécifiques en haut.

## 5. Sécurité et confidentialité

- **Aucune donnée ne quitte le serveur** : tout le traitement est local et
  déterministe.
- Les vues `suggest_diagnostic`, `admin_panel`, `admin_summary` sont
  protégées par `@staff_required` ou `@admin_required`.
- Les vues `chat_*` requièrent `@login_required`.
- L'historique du chat est stocké en **session Django** (pas en base).
- Un utilisateur simple ne peut consulter le statut que de **ses propres**
  tickets via la recherche de référence dans le chat.

## 6. Limites assumées

L'assistant **n'est pas une IA générative** :
- il ne peut répondre qu'aux intentions / motifs qu'on lui a appris,
- il ne reformule pas, ne paraphrase pas, ne « comprend » pas hors mots-clés,
- pour les cas hors catalogue, il propose poliment de créer un ticket.

C'est un choix assumé pour :
- garantir des réponses **vérifiables** et **défendables** en soutenance,
- avoir un comportement **reproductible** (les tests passent toujours pareil),
- ne dépendre d'aucune ressource externe (idéal pour un projet académique).
