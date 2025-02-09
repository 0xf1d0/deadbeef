import discord
from discord.ext import commands, tasks

import requests, csv, io, locale

from datetime import datetime, timedelta

locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

class Schedule(commands.Cog):
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.schedule_channel_id = 1304836325010313287
        self.schedule_message_id = 1325536150227517572
        self.previous_schedule_data = None
        self.update_schedule.start()

    def get_schedule(self):
        url = "https://docs.google.com/spreadsheets/d/1_FbKo3bwaJ5-PObvIbQrEHUbCbqPro-CH08pyikZ04k/export?format=csv&gid=496614399"
        response = requests.get(url)
        response.raise_for_status() # Check if the request was successful
        data = response.content.decode('utf-8')
        reader = list(csv.reader(io.StringIO(data)))
        return reader[8:92] + reader[102:]

    def filter_schedule(self, schedule_data):
        today = datetime.today()
        weekday = today.weekday()
        # february_2025 = datetime(2025, 2, 1)
        
        start_of_week = today - timedelta(days=weekday)
        week_updated = False
        days = 2

        if weekday > 2:
            start_of_week = start_of_week + timedelta(days=7)
            week_updated = True
            """if (next_week := start_of_week + timedelta(days=7)) > february_2025:
                days = 1
                start_of_week = next_week
                week_updated = True
            elif next_week < february_2025:
                start_of_week = next_week
                week_updated = True"""

        for i in range(0, len(schedule_data), 7):
            try:
                date = datetime.strptime(schedule_data[i][1], "%d/%m").replace(year=today.year)
                
                if date.date() == start_of_week.date():
                    schedule_data[i][1] = date.strftime("%A %d %B %Y").capitalize()
                    
                    for j in range(2, days + 2):
                        schedule_data[i][j] = (
                            datetime.strptime(schedule_data[i][j], "%d/%m")
                            .replace(year=today.year)
                            .strftime("%A %d %B %Y")
                            .capitalize()
                        )
                    
                    return [row[:days + 2] for row in schedule_data[i:i + 7]], week_updated
            
            except (ValueError, IndexError):
                continue

        return [], week_updated

    def format_schedule(self, schedule_data):
        formatted_data = []

        for j in range(1, len(schedule_data[0])):
            morning_course = f"{schedule_data[1][0]}: {schedule_data[1][j]} ({schedule_data[2][j]}) -> Salle {schedule_data[3][j]}"
            afternoon_course = f"{schedule_data[4][0]}: {schedule_data[4][j]} ({schedule_data[5][j]}) -> Salle {schedule_data[6][j]}"
            formatted_data.append(f"**{schedule_data[0][j]}**\n```{morning_course}\n{afternoon_course}```")

        return formatted_data
    
    def detect_changes(self, current_data, previous_data):
        if previous_data is None:
            return []

        changes = []
        for j in range(1, len(current_data[0])):
            if (current_data[1][j] != previous_data[1][j] or 
                current_data[2][j] != previous_data[2][j] or 
                current_data[3][j] != previous_data[3][j]):
                changes.append(f"🔄 Modification matin {current_data[0][j]} : {current_data[1][j]} ({current_data[2][j]}) -> Salle {current_data[3][j]}")
            
            if (current_data[4][j] != previous_data[4][j] or 
                current_data[5][j] != previous_data[5][j] or 
                current_data[6][j] != previous_data[6][j]):
                changes.append(f"🔄 Modification après-midi {current_data[0][j]} : {current_data[4][j]} ({current_data[5][j]}) -> Salle {current_data[6][j]}")

        return changes

    @tasks.loop(minutes=15)
    async def update_schedule(self):
        channel = self.bot.get_channel(self.schedule_channel_id)
        if channel:
            schedule_data = self.get_schedule()
            filtered_data, week_updated = self.filter_schedule(schedule_data)
            changes = self.detect_changes(filtered_data, self.previous_schedule_data)

            if changes or self.previous_schedule_data is None:
                formatted_data = self.format_schedule(filtered_data)
                schedule_message = '\n'.join(formatted_data)

                if self.schedule_message_id:
                    try:
                        message = await channel.fetch_message(self.schedule_message_id)
                        await message.edit(content=schedule_message)
                        
                        if changes and not week_updated:
                            modification_message = "📋 Modifications de l'emploi du temps :\n" + "\n".join(changes + ['@everyone'])
                            await channel.send(modification_message, delete_after=3600)
                    
                    except discord.NotFound:
                        message = await channel.send(schedule_message)
                        self.schedule_message_id = message.id
                else:
                    message = await channel.send(schedule_message)
                    self.schedule_message_id = message.id
                
                self.previous_schedule_data = filtered_data

    @update_schedule.before_loop
    async def before_update_schedule(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Schedule(bot))
