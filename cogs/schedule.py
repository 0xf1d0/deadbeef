from discord.ext import commands, tasks
import requests
import csv
import io

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
        return list(reader)

    @tasks.loop(hours=24)
    async def update_schedule(self):
        channel = self.bot.get_channel(self.schedule_channel_id)
        if channel:
            schedule_data = self.get_schedule()
            schedule_message = "Emploi du temps :\n\n"
            messages = []
            for row in schedule_data:
                line = " | ".join(row) + "\n"
                if len(schedule_message) + len(line) > 2000:
                    messages.append(schedule_message)
                    schedule_message = ""
                schedule_message += line
            messages.append(schedule_message)  # Append the last message

            for message in messages:
                await channel.send(message)

    @update_schedule.before_loop
    async def before_update_schedule(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Schedule(bot))