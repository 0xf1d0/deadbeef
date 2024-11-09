from discord.ext import commands, tasks
import requests
import csv
import io
from datetime import datetime, timedelta

class Schedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.schedule_channel_id = 1304836325010313287  # Remplacez par l'ID du channel où vous voulez envoyer l'emploi du temps
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
                        filtered_data.append(schedule_data[i:i+6])  # Inclure les 6 prochaines lignes
                        break
                except ValueError:
                    continue  # Ignore les colonnes qui ne contiennent pas de date valide

        return filtered_data

    def format_schedule(self, schedule_data):
        formatted_data = []
        block = schedule_data[0]
        for i in range(1, len(schedule_data[0])):
            if "Entreprise" in block[1][i] or "stage" in block[1][i]:
                continue  # Ignore les jours en entreprise ou stage
            date = block[0][i]
            morning_course = f"{block[1][0]}: {block[1][i]:<15} | {block[2][i]:<15} | {block[3][i]:<15}"
            afternoon_course = f"{block[4][0]}: {block[4][i]:<15} | {block[5][i]:<15} | {block[6][i]:<15}"
            formatted_data.append(f"{date:<15}\n{morning_course}\n{afternoon_course}")
        return formatted_data


    @tasks.loop(hours=24)
    async def update_schedule(self):
        channel = self.bot.get_channel(self.schedule_channel_id)
        if channel:
            schedule_data = self.get_schedule()
            filtered_data = self.filter_schedule(schedule_data)
            formatted_data = self.format_schedule(filtered_data)
            schedule_message = "Emploi du temps :\n\n"
            messages = []
            for line in formatted_data:
                if len(schedule_message) + len(line) + 6 > 2000:  # 6 caractères pour les balises de code
                    messages.append(f"```\n{schedule_message}\n```")
                    schedule_message = ""
                schedule_message += line + "\n"
            messages.append(f"```\n{schedule_message}\n```")  # Append the last message

            for message in messages:
                await channel.send(message)

    @update_schedule.before_loop
    async def before_update_schedule(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Schedule(bot))