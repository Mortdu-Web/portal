# hub-web

Pages **publiques** (sans connexion) de mon site personnel : accueil, à propos, contact et projets.

Ce repo ne contient ni authentification ni base de données. Il demande au service **`auth`**
(autre repo, Keycloak) si le visiteur est connecté, et envoie les utilisateurs connectés vers **`hub-app`**
(3e repo). Sans configuration de connexion, c'est un site 100 % public.

## Démarrage rapide

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # optionnel en local

flask --app hub_web run --debug --port 5002   # http://localhost:5002 (5000 = auth, 5001 = hub-app)
pytest                          # tests
flask --app hub_web todo        # liste les « A COMPLETER » restants
```

## Structure

```
hub_web/
├── __init__.py        create_app() : config, contenu, blueprints, erreurs, commande `todo`
├── config.py          variables d'environnement
├── content.py         lecture de content/ (Project, ContentStore, validation)
├── auth.py            « connecté ? » : appel à auth /api/me avec le cookie de session
├── contact.py         validation + anti-spam du formulaire
├── notifications.py   envoi ntfy
├── routes/
│   ├── pages.py       /, /apropos, /contact, /contact/send, /healthz, /robots.txt, /sitemap.xml
│   └── projets.py     /projets/, /projets/<slug>/, /projets/<parent>/<slug>/
├── templates/         base.html, pages, projets/ (hub, project, composants)
└── static/            css/, js/, img/
content/projets/       ← le contenu : un dossier par projet
docs/liaison-des-repos.md   ← lier hub-web, auth et hub-app (réglages, tests, dépannage)
tests/
```

## Ajouter un projet

Créer un dossier dans `content/projets/` : son nom est l'URL (`/projets/<nom>/`).

```
content/projets/mon-projet/
├── header.json   # métadonnées (hub + en-tête de page)
└── page.html     # uniquement les <section class="project-section"> du corps de page
```

`header.json` :

```json
{
  "nom": "Mon projet",
  "date": "2026",
  "type": "personnel",
  "git": "https://github.com/…",
  "court": "Phrase affichée dans la carte du hub.",
  "accroche": "Phrase affichée sous le titre de la page.",
  "stack": ["Python", "Docker"],
  "ordre": 130
}
```

- `type` : `academique` ou `personnel`.
- `ordre` : position dans le hub (plus petit = plus haut).
- `git` : URL ou `null`.

Aucune ligne de Python à écrire. En mode `--debug`, le contenu est relu à chaque requête.
En production il est chargé au démarrage : un JSON invalide empêche l'app de démarrer
au lieu de casser une page plus tard.

### Sous-projets (ex. HomeLab)

Un dossier avec son propre `header.json` placé **dans** un projet devient un sous-projet
(`/projets/homelab/vpn/`). Le parent affiche automatiquement la grille de ses enfants ;
il suffit de lui ajouter `"enfants_titre"` et `"enfants_retour"` dans son `header.json`.
Profondeur maximale : 2 niveaux.

## Formulaire de contact

`POST /contact/send` valide les champs, applique une limite de débit par IP (configurable),
ignore les robots (champ piège) et envoie le message à ntfy (`NOTIFICATIONS_URL`).
Sans `NOTIFICATIONS_URL`, il répond 503.

## Connexion

Trois repos, un cookie de session partagé sur le domaine parent :

| Repo | Rôle |
|------|------|
| `hub-web` (ce repo) | pages publiques ; bouton **Connexion** ; `/` renvoie les connectés vers `hub-app` |
| `auth` | Keycloak, session, API `/api/me` |
| `hub-app` | espace de l'utilisateur connecté (protégé par `auth-client`) |

hub-web ne vérifie pas le cookie lui-même : il le transmet à `auth` (`/api/me`). Si `auth` est en
panne, le site public continue de fonctionner. Configuration : `AUTH_PUBLIC_URL`, `APP_URL`, et
éventuellement `AUTH_INTERNAL_URL` / `AUTH_COOKIE_NAME` (voir `.env.example`). Tout vide = pas de
connexion ; partiellement rempli = l'application refuse de démarrer.

**Réglages à faire dans `auth` et Keycloak, test en local, production et dépannage :
`docs/liaison-des-repos.md`.**

## Déploiement

```bash
docker network create web     # une seule fois, partagé avec auth et hub-app
docker compose up -d --build   # http://localhost:5002
```

Derrière ton reverse proxy Nginx, garde `TRUSTED_PROXIES=1` pour que la limite de débit
s'applique à la vraie IP du visiteur. `/healthz` sert de healthcheck.

## Pour la suite

- Plusieurs projets avec un vrai backend : chacun son repo, protégé par `auth-client`.
- Chaque application avec un vrai backend : son propre repo / service derrière le reverse proxy.
