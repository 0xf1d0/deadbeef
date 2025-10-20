# DeadBeef

DeadBeef is a `discord.py` bot for M1 Cybersecurity's Discord at Paris Cité University.

This bot embeds all the features to make everyday life easier for students.

## Features

- 🎓 **Student Authentication** - Verify students and professionals
- 📅 **Calendar Management** - Schedule and event tracking
- 🎵 **Music Player** - Play music in voice channels
- 🤖 **AI Integration** - Mistral AI chat functionality
- 🔧 **Cybersecurity Tools** - Browse, search, and suggest security tools
- 📚 **Homework To-Do System** - Track assignments and deadlines by grade level
- 📊 **Course Schedule System** - Automated weekly schedule from Google Sheets
- 📰 **RSS News System** - Automated news feeds with custom sources (NEW!)

## Installation

```sh
# Clone repository
git clone https://github.com/0xf1d0/deadbeef

# Get into the project
cd deadbeef

# Consider using a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Execute program
./start.sh
```

### Cybersecurity Tools Feature Setup

To use the Cybersecurity Tools Management System:

1. **Add to `.env` file:**
```env
ADMIN_CHANNEL_ID=your_admin_channel_id_here
DATABASE_URL=sqlite+aiosqlite:///db/database.db
```

2. **Initialize with sample data:**
```bash
python setup_cybertools.py
```

### Homework To-Do System Setup

To use the Homework Tracking System:

1. **Set up a channel for M1:**
```
/setup_homework_channel grade_level:M1
```

2. **Set up a channel for M2:**
```
/setup_homework_channel grade_level:M2
```

3. **Add courses and assignments** using the interactive buttons on the to-do list.

### Course Schedule System Setup

To use the automated schedule system:

1. **Make your Google Sheet public** (anyone with link can view)

2. **Get your sheet information:**
   - Spreadsheet URL
   - GID (from URL after `#gid=`)

3. **Configure M1 channel:**
```
/manage_schedule
```
Then click "Setup New Channel" and provide M1 sheet details.

4. **Configure M2 channel:**
Repeat in M2 channel with M2 sheet details.

Schedules will update automatically every 15 minutes!

### RSS News System Setup

To use the automated news feed system:

1. **Configure news channel:**
```
/manage_news
```
Then click "Setup Channel" and provide a channel name.

2. **Add RSS feeds:**
Click "Add Feed" and provide:
- Feed name (e.g., "CERT-FR")
- Feed URL (e.g., `https://www.cert.ssi.gouv.fr/feed/`)
- Color (optional, e.g., "red" or "#FF0000")

3. **Repeat for more feeds:**
Add as many feeds as you want!

News will update automatically every 30 minutes!

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