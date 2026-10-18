# Lier hub-web, auth et hub-app

| Repo | Rôle | Port local | Sous-domaine en prod (exemple) |
|------|------|-----------|-------------------------------|
| `hub-web` | pages publiques | **5002** | `www.exemple.fr` |
| `auth` | connexion Keycloak, session, API `/api/me` | 5000 | `auth.exemple.fr` |
| `hub-app` | espace de l'utilisateur connecté | 5001 | `app.exemple.fr` |

## Le parcours

```
Visiteur anonyme sur hub-web
   │  clic « Connexion »
   ▼
auth /login?next=https://www.exemple.fr/ ──▶ Keycloak ──▶ auth /callback
   │  pose le cookie de session (partagé sur .exemple.fr), puis redirige vers next
   ▼
hub-web « / » : demande à auth « /api/me » avec le cookie ──▶ 200
   │  302
   ▼
hub-app (page d'accueil de l'utilisateur connecté)
```

- **hub-web ne vérifie pas le cookie lui-même** : la session est signée avec un secret qui reste dans `auth`.
  hub-web transmet le cookie à `GET {AUTH_INTERNAL_URL}/api/me` : **200 = connecté**, tout le reste = anonyme.
- Les visiteurs **sans cookie** ne déclenchent **aucun appel** à `auth`.
- Si `auth` est lent (> 1,5 s) ou en panne, le visiteur est traité comme anonyme : **le site public reste en ligne**.
- Un utilisateur connecté peut toujours consulter les pages publiques (projets, à propos, contact) ;
  seule la page `/` l'envoie vers `hub-app`. La barre affiche alors **Mon espace** et **Déconnexion**.
- **Déconnexion** : `auth /logout?next=<page courante>` (session locale + Keycloak), puis retour sur la page.
- `hub-app` protégé par `require_auth` renvoie un non-connecté vers `auth /login`, jamais vers `hub-web /` :
  c'est ce qui évite une boucle de redirections.

## Réglages à faire, repo par repo

### hub-web (`.env`)

| Variable | Local | Production |
|----------|-------|------------|
| `AUTH_PUBLIC_URL` | `http://localhost:5000` | `https://auth.exemple.fr` |
| `AUTH_INTERNAL_URL` | vide (= `AUTH_PUBLIC_URL`) | `http://auth:5000` (nom du service sur le réseau Docker `web`) |
| `APP_URL` | `http://localhost:5001/` | `https://app.exemple.fr/` |
| `AUTH_COOKIE_NAME` | `session` | `session` (nom du cookie d'`auth`) |
| `SITE_URL` | vide | `https://www.exemple.fr` (adresse de retour après connexion) |
| `TRUSTED_PROXIES` | `0` | `1` |

### auth (`.env`) : à modifier

- `ALLOWED_REDIRECT_DOMAINS` : **ajouter l'hôte de hub-web** (`localhost` en local, `www.exemple.fr` en prod).
  Sans cela, `auth` refusera le `next` envoyé par hub-web (c'est la protection contre la redirection ouverte).
- `SESSION_COOKIE_DOMAIN=.exemple.fr` en prod (vide en local) : sans cela le cookie n'est pas envoyé à hub-web.
- `SESSION_COOKIE_SECURE=true` en prod (HTTPS), `false` en local.

### Keycloak (client `auth-service`) : à modifier

- **Post logout redirect URIs** : ajouter `http://localhost:5002/*` en local, `https://www.exemple.fr/*` en prod
  (comme tu l'as fait pour `http://localhost:5001/*` avec hub-app). Sans cela, la déconnexion depuis hub-web échoue.
- Les « redirect URIs » de connexion ne changent pas : seule `…/callback` d'`auth` compte.

### hub-app

Rien d'obligatoire. Option : un lien « Retour au site » vers hub-web.

## Tester en local

1. Dans chaque repo : `docker network create web` (une seule fois pour tous), `cp .env.example .env`, régler selon ci-dessus.
2. Démarrer `auth` (5000), `hub-app` (5001), puis `hub-web` : `docker compose up -d --build` (5002).
   Sans Docker : `flask --app hub_web run --debug --port 5002`.
3. Scénario :
   - `http://localhost:5002/` → accueil public, bouton **Connexion**.
   - Clic → Keycloak → retour : tu arrives sur **hub-app** (5001).
   - `http://localhost:5002/projets/` → toujours accessible, la barre affiche **Mon espace** / **Déconnexion**.
   - **Déconnexion** → retour sur la page, bouton **Connexion** de nouveau.
   - Arrêter `auth` : le site public continue de répondre.

Les cookies ne sont pas isolés par port : la session posée par `localhost:5000` est envoyée à `5001` et `5002`.

## Production : reverse proxy

Un bloc par sous-domaine, tous en HTTPS (les noms de conteneurs et ports sont à adapter) :

```nginx
server {
    server_name www.exemple.fr;
    listen 443 ssl;
    location / {
        proxy_pass http://hub-web:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host  $host;
    }
}
# idem pour auth.exemple.fr → auth, app.exemple.fr → hub-app
```

Pas de `proxy_cache` devant hub-web : ses pages dépendent du cookie (`Vary: Cookie`).

## Dépannage

| Symptôme | Cause probable |
|----------|---------------|
| Après connexion on reste sur le site public, bouton **Connexion** toujours là | Le cookie n'arrive pas à hub-web : `SESSION_COOKIE_DOMAIN` mal réglé, ou `AUTH_COOKIE_NAME` différent de celui d'`auth`. Ouvre les outils du navigateur > Cookies. |
| Idem, cookie bien présent | hub-web n'atteint pas `auth` : vérifier `AUTH_INTERNAL_URL`, le réseau `web`, et les logs (« auth injoignable »). |
| `auth` affiche une erreur sur `next` | L'hôte de hub-web n'est pas dans `ALLOWED_REDIRECT_DOMAINS`. |
| La déconnexion affiche une erreur Keycloak | `https://www.exemple.fr/*` absent des « post logout redirect URIs ». |
| Boucle de redirections entre `/` et hub-app | hub-app renvoie vers hub-web `/` un utilisateur qu'il refuse ; il doit renvoyer vers `auth /login` ou afficher un 403. |
| hub-web refuse de démarrer | Variables de connexion à moitié remplies : le message nomme celles qui manquent. |

## Hypothèses à vérifier (je n'ai vu que les README d'`auth` et `hub-app`, pas leur code)

- `GET /api/me` répond **200** pour une session valide et **401** sinon, sans rediriger.
- Le cookie de session s'appelle `session` (nom par défaut de Flask ; sinon régler `AUTH_COOKIE_NAME`).
- `GET /logout?next=` accepte une URL de hub-web si son hôte est dans `ALLOWED_REDIRECT_DOMAINS`.
