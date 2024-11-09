from discord.ext import commands, tasks
import requests
import csv
import io
from datetime import datetime, timedelta

class Schedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.schedule_channel_id = 1304836325010313287
        self.update_schedule.start()

    def get_schedule(self):
        url = "https://docs.google.com/spreadsheets/d/1_FbKo3bwaJ5-PObvIbQrEHUbCbqPro-CH08pyikZ04k/export?format=csv&gid=496614399"
        response = requests.get(url)
        response.raise_for_status()  # Vérifie si la requête a réussi
        data = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(data))
        print(list(reader)[50:])
        return list(reader)[50:]

    def filter_schedule(self, schedule_data):
        today = datetime.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        if today.weekday() >= 3:  # Jeudi (3) ou plus tard
            start_of_week = start_of_week + timedelta(days=7)
            end_of_week = end_of_week + timedelta(days=7)

        filtered_data = []
        for row in schedule_data:
            try:
                date = datetime.strptime(row[0], "%d/%m/%Y")
                if start_of_week <= date <= end_of_week:
                    filtered_data.append(row)
            except ValueError:
                continue  # Ignore les lignes qui ne contiennent pas de date valide

        return filtered_data

    @tasks.loop(hours=24)
    async def update_schedule(self):
        channel = self.bot.get_channel(self.schedule_channel_id)
        if channel:
            schedule_data = self.get_schedule()
            filtered_data = self.filter_schedule(schedule_data)
            schedule_message = "Emploi du temps :\n\n"
            messages = []
            for row in filtered_data:
                line = " | ".join(row) + "\n"
                if len(schedule_message) + len(line) > 2000:
                    messages.append(f"```\n{schedule_message}\n```")
                    schedule_message = ""
                schedule_message += line
            messages.append(f"```\n{schedule_message}\n```")  # Append the last message

            for message in messages:
                await channel.send(message)

    @update_schedule.before_loop
    async def before_update_schedule(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Schedule(bot))