# DeadBeef

DeadBeef is a `discord.py` bot for M1 Cybersecurity's Discord at Paris Cité University.

This bot embeds all the features to make everyday life easier for students.

## Installation

```sh
# Clone repository
git clone https://github.com/0xf1d0/deadbeef

cd deadbeef
# Consider using a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Execute program
./start.sh
```

## Config

The bot needs a `config.json` file to gather some values to be able to work.
Here is an example :

```json
{
    "token": "secret",
    "welcome_message": "<:upc:1291788754775965819> Bienvenue chez les M1 Cybers\u00e9curit\u00e9 de l'Universit\u00e9 Paris Cit\u00e9 <:upc:1291788754775965819> !\n\n:student: Etudiant(e) en Cybers\u00e9curit\u00e9, tu trouveras ici des informations utiles pour ton ann\u00e9e universitaire. N'h\u00e9site pas \u00e0 poser des questions, \u00e0 partager des informations ou \u00e0 discuter avec les autres \u00e9tudiants ! :smiley:\n\n:warning: Merci de respecter les r\u00e8gles de bonne conduite et de ne pas partager d'informations sensibles. :warning:\n\nInvit\u00e9(e) ou Etudiant(e) ? Choisissez votre identit\u00e9 dans le menu d\u00e9roulant ci-dessous.\n\n:warning: **TOUTE USURPATION D'IDENTITE EST ENREGISTREE ET RAPPORTEE** :warning:\n\n:bug: __Si vous rencontrez un probl\u00e8me lors de cette \u00e9tape, contactez <@253616158895243264>__\n\nBonne ann\u00e9e universitaire \u00e0 tous ! :mortar_board:",
    "welcome_message_id": 1293963282721407030,
    "reminders": []
}
```

## Features

### Calendar System

![Calendar](./assets/calendar.png)

### Multiple capabilities

![Card](./assets/card.png)

### Music System using yt-dlp

![Music](./assets/music.png)

And more ...