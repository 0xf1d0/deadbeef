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
        return list(reader)[50:92]

    def filter_schedule(self, schedule_data):
        today = datetime.today()
        weekday = today.weekday()
        february_2025 = datetime(2025, 2, 1)
        start_of_week = today - timedelta(days=today.weekday())
        next_week = start_of_week + timedelta(days=7)
        days = 2

        if weekday > 2 and next_week > february_2025:
            days = 1
            start_of_week += timedelta(days=7)
        elif weekday > 3 and next_week < february_2025:
            start_of_week += timedelta(days=7)

        # end_of_week = start_of_week + timedelta(days=days)

        print(schedule_data)
        i = 0
        while i < len(schedule_data):
            date = datetime.strptime(schedule_data[i][1], "%d/%m").replace(year=today.year)
            if start_of_week == date:
                schedule_data[i][1] = date.strftime("%A %d %B %Y")
                for j in range(2, days + 2):
                    schedule_data[i][j] = datetime.strptime(schedule_data[i][j], "%d/%m").replace(year=today.year).strftime("%A %d %B %Y")
                return schedule_data[i:i+6][:, days + 2]
            i += 7
        
        return []

    def format_schedule(self, schedule_data):
        formatted_data = []

        for line in schedule_data:
            for j in range(1, len(line)):
                morning_course = f"{line[1][0]}: {line[1][j]} ({line[2][j]}) -> Salle {line[3][j]}"
                afternoon_course = f"{line[4][0]}: {line[4][j]} ({line[5][j]}) -> Salle {line[6][j]}"
                formatted_data.append(f"**{line[0][j]}**\n```{morning_course}\n{afternoon_course}```")

        return formatted_data

    @tasks.loop(hours=1)
    async def update_schedule(self):
        channel = self.bot.get_channel(self.schedule_channel_id)
        if channel:
            schedule_data = self.get_schedule()
            filtered_data = self.filter_schedule(schedule_data)
            formatted_data = self.format_schedule(filtered_data)
            schedule_message = '\n'.join(formatted_data)
            print(schedule_message)

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