import discord
from discord.ext import commands, tasks

import requests, csv, io, locale

from datetime import datetime, timedelta

locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

class Schedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.schedule_channel_id = 1304836325010313287
        self.schedule_message_id = None
        self.previous_schedule = None
        self.update_schedule.start()

    def get_schedule(self):
        url = "https://docs.google.com/spreadsheets/d/1_FbKo3bwaJ5-PObvIbQrEHUbCbqPro-CH08pyikZ04k/export?format=csv&gid=496614399"
        response = requests.get(url)
        response.raise_for_status()  # Vérifie si la requête a réussi
        data = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(data))
        return list(reader)[50:]

    def filter_schedule(self, schedule_data):
        today = datetime.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        if today.weekday() >= 3:  # Jeudi (3) ou plus tard
            start_of_week = start_of_week + timedelta(days=7)
            end_of_week = end_of_week + timedelta(days=7)

        filtered_data = []
        for i, row in enumerate(schedule_data):
            for j in range(1, len(row)):
                try:
                    date = datetime.strptime(row[j], "%d/%m")
                    date = date.replace(year=today.year)  # Ajoute l'année actuelle
                    if start_of_week <= date <= end_of_week:
                        filtered_data.append(schedule_data[i:i+7])  # Inclure les 6 prochaines lignes
                        break
                except ValueError:
                    continue  # Ignore les colonnes qui ne contiennent pas de date valide

        return filtered_data

    def format_schedule(self, schedule_data):
        formatted_data = []
        block = schedule_data[0]
        for i in range(1, len(schedule_data[0]) - 1):
            if any(keyword in block[1][i] for keyword in ["Entreprise", "stage", "FERIE"]):
                continue  # Ignore les jours en entreprise, fériés ou stage
            date = datetime.strptime(block[0][i], "%d/%m").replace(year=datetime.now().year)
            formatted_date = date.strftime("%A %d %B %Y")
            morning_course = f"{block[1][0]}: {block[1][i]} ({block[2][i]}) -> Salle {block[3][i]}"
            afternoon_course = f"{block[4][0]}: {block[4][i]} ({block[5][i]}) -> Salle {block[6][i]}"
            formatted_data.append(f"**{formatted_date}**\n```{morning_course}\n{afternoon_course}```")
        return formatted_data

    @tasks.loop(hours=1)
    async def update_schedule(self):
        channel = self.bot.get_channel(self.schedule_channel_id)
        if channel:
            schedule_data = self.get_schedule()
            filtered_data = self.filter_schedule(schedule_data)
            formatted_data = self.format_schedule(filtered_data)
            schedule_message = '\n'.join(formatted_data)

            if self.previous_schedule != schedule_message:
                self.previous_schedule = schedule_message
                if self.schedule_message_id:
                    try:
                        message = await channel.fetch_message(self.schedule_message_id)
                        await message.edit(content=schedule_message)
                        await channel.send("L'emploi du temps a été mis à jour. @everyone", delete_after=10)
                    except discord.NotFound:
                        message = await channel.send(schedule_message)
                        self.schedule_message_id = message.id
                else:
                    message = await channel.send(schedule_message)
                    self.schedule_message_id = message.id

    @update_schedule.before_loop
    async def before_update_schedule(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Schedule(bot))