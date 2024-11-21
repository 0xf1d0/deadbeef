import discord
from discord.ext import commands, tasks

import requests, csv, io, locale

from datetime import datetime, timedelta

locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

class Schedule(commands.Cog):
    """
    @brief Schedule class to manage the timetable.
    """

    def __init__(self, bot: commands.Bot):
        """
        @brief Constructor for the Schedule class.
        @param bot Instance of the Discord bot.
        """
        self.bot = bot
        self.schedule_channel_id = 1304836325010313287
        self.schedule_message_id = None
        self.previous_schedule = None
        self.update_schedule.start()

    def get_schedule(self):
        """
        @brief Retrieves the timetable from Google Sheets.
        @return List of timetable rows.
        """
        url = "https://docs.google.com/spreadsheets/d/1_FbKo3bwaJ5-PObvIbQrEHUbCbqPro-CH08pyikZ04k/export?format=csv&gid=496614399"
        response = requests.get(url)
        response.raise_for_status() # Check if the request was successful
        data = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(data))
        return list(reader)[2:92] + list(reader)[102:]

    def filter_schedule(self, schedule_data):
        """
        @brief Filters the timetable to include only events for the current or next week.
        @param schedule_data List of timetable rows.
        @return List of filtered timetable rows.
        """
        today = datetime.today()
        weekday = today.weekday()
        february_2025 = datetime(2025, 2, 1)
        start_of_week = today - timedelta(days=today.weekday())
        next_week = start_of_week + timedelta(days=7)
        days = 2
        week_updated = False

        if weekday > 1 and next_week > february_2025:
            days = 1
            start_of_week += timedelta(days=7)
            week_updated = True
        elif weekday > 2 and next_week < february_2025:
            start_of_week += timedelta(days=7)
            week_updated = True

        # end_of_week = start_of_week + timedelta(days=days)

        i = 0
        while i < len(schedule_data):
            date = datetime.strptime(schedule_data[i][1], "%d/%m").replace(year=today.year)
            if start_of_week.date() == date.date():
                schedule_data[i][1] = date.strftime("%A %d %B %Y").capitalize()
                for j in range(2, days + 2):
                    schedule_data[i][j] = datetime.strptime(schedule_data[i][j], "%d/%m").replace(year=today.year).strftime("%A %d %B %Y").capitalize()
                return [row[:days + 2] for row in schedule_data[i:i + 7]]
            i += 7
        
        return []

    def format_schedule(self, schedule_data):
        """
        @brief Formats the timetable for display.
        @param schedule_data List of filtered timetable rows.
        @return List of formatted timetable rows.
        """
        formatted_data = []

        for j in range(1, len(schedule_data[0])):
            morning_course = f"{schedule_data[1][0]}: {schedule_data[1][j]} ({schedule_data[2][j]}) -> Salle {schedule_data[3][j]}"
            afternoon_course = f"{schedule_data[4][0]}: {schedule_data[4][j]} ({schedule_data[5][j]}) -> Salle {schedule_data[6][j]}"
            formatted_data.append(f"**{schedule_data[0][j]}**\n```{morning_course}\n{afternoon_course}```")

        return formatted_data

    @tasks.loop(hours=1)
    async def update_schedule(self):
        """
        @brief Periodically updates the timetable.
        """
        channel = self.bot.get_channel(self.schedule_channel_id)
        if channel:
            schedule_data = self.get_schedule()
            filtered_data, week_updated = self.filter_schedule(schedule_data)
            formatted_data = self.format_schedule(filtered_data)
            schedule_message = '\n'.join(formatted_data)

            if self.previous_schedule != schedule_message:
                self.previous_schedule = schedule_message
                if self.schedule_message_id:
                    try:
                        message = await channel.fetch_message(self.schedule_message_id)
                        await message.edit(content=schedule_message)
                        if not week_updated:
                            await channel.send("L'emploi du temps a été mis à jour. @everyone", delete_after=10)
                    except discord.NotFound:
                        message = await channel.send(schedule_message)
                        self.schedule_message_id = message.id
                else:
                    message = await channel.send(schedule_message)
                    self.schedule_message_id = message.id

    @update_schedule.before_loop
    async def before_update_schedule(self):
        """
        @brief Waits until the bot is ready before starting the update loop.
        """
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    """
    @brief Sets up the Schedule cog.
    @param bot Instance of the Discord bot.
    """
    await bot.add_cog(Schedule(bot))