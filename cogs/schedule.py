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
        self.previous_schedule_data = None
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
        return list(reader)[8:92] + list(reader)[103:]

    def filter_schedule(self, schedule_data):
        """
        Filters the timetable to include only events for the current or next week.
        
        Args:
            schedule_data (List): List of timetable rows.
        
        Returns:
            Tuple[List, bool]: Filtered timetable rows and whether the week was updated.
        """
        today = datetime.today()
        weekday = today.weekday()
        february_2025 = datetime(2025, 2, 1)
        
        # Determine the start of the week and number of days to include
        start_of_week = today - timedelta(days=weekday)
        week_updated = False
        days = 2

        # Adjust start of week and days based on specific conditions
        if weekday > 1:
            if (next_week := start_of_week + timedelta(days=7)) > february_2025:
                days = 1
                start_of_week = next_week
                week_updated = True
            elif next_week < february_2025:
                start_of_week = next_week
                week_updated = True

        # Vectorize the filtering process
        for i in range(0, len(schedule_data), 7):
            try:
                date = datetime.strptime(schedule_data[i][1], "%d/%m").replace(year=today.year)
                
                if date.date() == start_of_week.date():
                    # Format dates for the matching week
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
                # Skip rows that don't match the expected format
                continue

        return [], week_updated

    def format_schedule(self, schedule_data):
        """
        Formats the timetable for display.
        """
        formatted_data = []

        for j in range(1, len(schedule_data[0])):
            morning_course = f"{schedule_data[1][0]}: {schedule_data[1][j]} ({schedule_data[2][j]}) -> Salle {schedule_data[3][j]}"
            afternoon_course = f"{schedule_data[4][0]}: {schedule_data[4][j]} ({schedule_data[5][j]}) -> Salle {schedule_data[6][j]}"
            formatted_data.append(f"**{schedule_data[0][j]}**\n```{morning_course}\n{afternoon_course}```")

        return formatted_data
    
    def detect_changes(self, current_data, previous_data):
        """
        Detect changes between two schedules.
        
        Returns:
            List of change descriptions
        """
        if previous_data is None:
            return []

        changes = []
        for j in range(1, len(current_data[0])):
            # Compare morning courses
            if (current_data[1][j] != previous_data[1][j] or 
                current_data[2][j] != previous_data[2][j] or 
                current_data[3][j] != previous_data[3][j]):
                changes.append(f"🔄 Modification matin {current_data[0][j]} : {current_data[1][j]} ({current_data[2][j]}) -> Salle {current_data[3][j]}")
            
            # Compare afternoon courses
            if (current_data[4][j] != previous_data[4][j] or 
                current_data[5][j] != previous_data[5][j] or 
                current_data[6][j] != previous_data[6][j]):
                changes.append(f"🔄 Modification après-midi {current_data[0][j]} : {current_data[4][j]} ({current_data[5][j]}) -> Salle {current_data[6][j]}")

        return changes

    @tasks.loop(hours=1)
    async def update_schedule(self):
        """
        Periodically updates the timetable in the designated Discord channel.
        
        Handles schedule updates, message editing, and notification dispatching.
        """
        channel = self.bot.get_channel(self.schedule_channel_id)
        if channel:
            schedule_data = self.get_schedule()
            filtered_data, week_updated = self.filter_schedule(schedule_data)
            changes = self.detect_changes(filtered_data, self.previous_schedule_data)

            # Format only if there are changes or the previous schedule data is None
            if changes or self.previous_schedule_data is None:
                formatted_data = self.format_schedule(filtered_data)
                schedule_message = '\n'.join(formatted_data)

                # Update message
                if self.schedule_message_id:
                    try:
                        message = await channel.fetch_message(self.schedule_message_id)
                        await message.edit(content=schedule_message)
                        
                        # Send edits
                        if changes and not week_updated:
                            modification_message = "📋 Modifications de l'emploi du temps :\n" + "\n".join(changes + ['@everyone'])
                            await channel.send(modification_message, delete_after=3600)
                    
                    except discord.NotFound:
                        message = await channel.send(schedule_message)
                        self.schedule_message_id = message.id
                else:
                    message = await channel.send(schedule_message)
                    self.schedule_message_id = message.id
                
                # Update previous schedule data
                self.previous_schedule_data = filtered_data

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
