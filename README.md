# Deadbeef Bot – Guide complet (FR)

Bot Discord moderne pour la communauté (M1/M2) intégrant : authentification avancée (étudiants et professionnels), gestion CTF avec workflows UI, devoirs, emploi du temps, actualités, outils cyber, musique, et intégration Root-Me avec cache.

## Sommaire
- Présentation générale
- Installation rapide
- Configuration requise
- Lancement du bot
- Système d’authentification (Étudiants/Professionnels)
- Intégration Root‑Me (+ système de cache)
- CTF Team Management System
- Tasks (Tasks)
- Emploi du temps (Schedule)
- Actualités (News)
- Outils Cyber / Musique / Divers
- Commandes d’administration utiles
- Bonnes pratiques et dépannage

---

## Présentation générale
Le bot propose une expérience « UI-first »: les actions principales sont pilotées via des boutons, modales et menus déroulants. Les données sont stockées en base SQLAlchemy asynchrone, avec des relations propres et des contraintes (ex: un joueur ne peut appartenir qu’à une seule équipe CTF).

Points clés:
- Authentification étudiante (M1/M2 + FI/FA) via jeton email, et authentification des professionnels pré-enregistrés.
- Gestion CTF avancée: création d’équipe, canal privé, invitations, candidatures, panneau de gestion, statistiques Root‑Me.
- Intégration Root‑Me avec cache en base (limite les appels API et accélère l’affichage).
- Systèmes devoirs, emploi du temps et actualités orientés UI et base de données.

---

## Installation rapide
Pré-requis:
- Python 3.11+
- Un bot Discord (token) et un serveur cible
- Accès aux fichiers CSV étudiants dans `assets/`

Installation:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Configuration requise
Variables d’environnement (exemples):
- `TOKEN`: token du bot Discord
- `ROOTME`: clé API Root‑Me (facultatif si anonyme, recommandé)

Configuration interne (voir `utils.__init__`):
- Canaux/roles constants: `WELCOME_CHANNEL`, `WELCOME_MESSAGE`, `LOG_CHANNEL`, `CTF_CATEGORY`, rôles `ROLE_STUDENT`, `ROLE_M1`, `ROLE_M2`, `ROLE_FI`, `ROLE_FA`, etc.
- Emails: `ConfigManager` pour objet et contenu des emails (jeton).
- CSV étudiants: dans `assets/`, utilisés par `utils.csv_parser`.

Base de données:
- SQLAlchemy asynchrone (sqlite par défaut). Les modèles sont dans `db/models.py`.
- Les tables sont créées automatiquement au premier lancement si non présentes.

---

## Lancement du bot
```bash
source venv/bin/activate
python main.py
```
Le bot synchronise les commandes slash à la connexion.

---

## Système d’authentification (Étudiants/Professionnels)
Emplacement: `ui/auth.py`, `cogs/common.py`, modèles `AuthenticatedUser`, `Professional`.

Flux utilisateur:
1. Message d’accueil (canal d’accueil) avec boutons.
2. Bouton « S’authentifier »:
   - Étudiant (rôle Étudiant requis): modal demandant le numéro étudiant + niveau (M1/M2). Le bot vérifie dans les CSV (FI/FA), envoie un jeton par email et attend la saisie du jeton.
   - Professionnel (rôle Pro requis): modal email (doit correspondre à un Pro enregistré). Jeton envoyé également.
3. Bouton « Entrer le jeton »: saisie du JWT → si valide, l’utilisateur est authentifié, reçoit les rôles (M1/M2 + FI/FA) ou accès aux canaux de cours (Pro).

Boutons supplémentaires (authentification requise):
- « Root‑Me »: lier l’ID Root‑Me (contrôle strict: numérique, unicité, vérification via API). Affiche une erreur si non authentifié.
- « LinkedIn »: lier/modifier l’URL LinkedIn (erreur si non authentifié).

---

## Intégration Root‑Me (+ système de cache)
Emplacement: `api/` (client Root‑Me), `utils/rootme_cache.py` (gestion de cache), modèles `RootMeCache`.

Fonctionnement:
- Au premier appel, le bot requête l’API Root‑Me, normalise les données (pseudo, score, rang, position, nombre de challenges) et les stocke dans `rootme_cache`.
- Les lectures suivantes utilisent le cache pendant la durée configurée (6h par défaut) pour réduire la charge et accélérer l’affichage.
- Indicateur « (cached) » affiché dans les embeds lorsque les données proviennent du cache.

Commandes utiles:
- `/refresh_rootme_cache [membre]` (admin): force un rafraîchissement du cache pour un utilisateur.

Affichage profil (`/profile`):
- Montre pseudo, score, rang, position, compteur de challenges (sans lister les 10 derniers, volontairement retiré).

---

## CTF Team Management System
Emplacement: `cogs/ctf.py`, `ui/ctf.py`, modèles `PlayerProfile`, `Team`, `TeamInvite`, `TeamApplication`.

Principes:
- Un utilisateur doit être authentifié pour utiliser le système CTF.
- `PlayerProfile` est lié 1‑à‑1 à `AuthenticatedUser` (pas de doublons d’infos). Un utilisateur ne peut être que dans UNE équipe.

Fonctionnalités clés:
- Profil CTF `/ctf profile`:
  - Création automatique du `PlayerProfile` si manquant (auth requis).
  - Statut (« Looking for Team », etc.).
  - Vue profil CTF.
- Création d’équipe `/ctf team create`:
  - Modal: nom, description, statut de recrutement.
  - Création d’un canal privé sous la catégorie CTF + thread "📥 Inbox".
  - Message d’accueil avec bouton « ⚙️ Manage Team » (propriétaire uniquement).
- Découverte des équipes `/ctf teams`:
  - Liste paginée des équipes qui recrutent.
  - Boutons « Voir stats », « Postuler » (modal raison, envoi dans l’Inbox du staff de l’équipe).
- Panneau de gestion (bouton ⚙️ dans le canal d’équipe):
  - Modifier infos, inviter membre (sélecteur paginé d’utilisateurs authentifiés), gérer membres (kick), transfert de propriété, dissolution d’équipe.
- Statistiques d’équipe `/ctf profile team_stats`:
  - Agrégation des stats Root‑Me des membres avec cache.
  - Classement interne des membres par score.

Notes UI:
- Sélecteurs paginés pour choisir un utilisateur (affiche pseudo Discord, email, Root‑Me si dispo).
- Gestion stricte des interactions (une réponse par interaction, suivi via followup si nécessaire).

---

## Tâches (Tasks)
Emplacement: `cogs/tasks.py` (+ `ui/` si applicable).

Principes:
- Les tâches sont associés à des canaux de cours.
- Détermination automatique des rôles à mentionner (FI/FA) selon les permissions du canal.
- Tableau/embeds par cours; gestion via une commande admin centralisée (tableau de bord) plutôt que des boutons visibles par tous.

---

## Emploi du temps (Schedule)
Emplacement: `cogs/schedule.py`.

Principes:
- Admin: choisir le(s) canal(aux) de destination (M1, M2) via UI, publier et mettre à jour l’EDT chaque semaine.
- Source compatible Google Sheets (exemple fourni) avec récupération asynchrone via `aiohttp`.
- Notifications de changements.

---

## Actualités (News)
Emplacement: `cogs/news.py`.

Principes:
- Flux d’actualités administrables; stockage en base (pas de JSON de config).
- Affichage sous forme d’embeds; pagination si nécessaire.

---

## Outils Cyber / Musique / Divers
- `cogs/cybertools.py`: catalogues/outils sécurité.
- `cogs/music.py`: lecture audio via `discord.py[voice]`.
- `cogs/mistral.py`: intégration Mistral AI (exemples).
- `cogs/common.py`: utilitaires communs (profil, annonce, purge, ping, refresh cache Root‑Me, etc.).

---

## Commandes d’administration utiles
- `/announce`: afficher une modale d’annonce (rôles autorisés configurés).
- `/purge <n>`: supprimer n messages.
- `/refresh_rootme_cache [membre]`: rafraîchir le cache Root‑Me d’un membre.
- Gestion CTF: via UI (dans le canal d’équipe) + contraintes en base.

---

## Bonnes pratiques et dépannage
- Interactions Discord: une seule réponse initiale par interaction; utiliser `interaction.followup.send` pour les réponses supplémentaires.
- SQLAlchemy async: toujours effectuer les accès aux relations dans une session active; éviter les lazy loads en contexte async (utiliser `join`/`selectinload`).
- Erreurs de formulaire Discord: les champs d’une modale doivent respecter `min_length`/`max_length` et valeurs par défaut valides.
- Cache Root‑Me: par défaut 6h. Utilisez `/refresh_rootme_cache` pour forcer une mise à jour en cas de décalage.
- Rôles FI/FA/M1/M2: s’assurer que les IDs de rôles sont correctement configurés dans `utils`.

---

## Support & contributions
- Ouvrez des issues/PRs pour bugs et améliorations.
- Merci de respecter le style de code (typage, early-returns, pas de nesting excessif, commentaires utiles uniquement).

---

Bon usage et GLHF 🚀