from discord import app_commands, Interaction, Embed, NotFound
from discord.ext import commands, tasks

from datetime import datetime, timedelta
import re


class Calendar(commands.Cog):
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminders = bot.config.get('reminders', [])
        self.calendar_channel = bot.get_channel(1293319532361809986)
        self.calendar_message_id = bot.config.get('calendar_message_id', 0)
        self.check_reminders.start()
    
    def save_reminders(self):
        self.bot.config.set('reminders', self.reminders)
    
    async def channel_autocomplete(self, _: Interaction, current: str) -> list[app_commands.Choice[str]]:
        category = self.bot.get_channel(1289244121004900487)

        return [
            app_commands.Choice(name=channel.name, value=channel.name)
            for channel in category.text_channels
            if current.lower() in re.sub(r':.+?:', '', channel.name.lower())
        ]
    
    async def event_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        option = interaction.namespace.option
        course = interaction.namespace.course
        courses = [reminder['name'] for reminder in self.reminders]
        if option not in ["2", "3"] and not course in courses:
            return []

        return [
            app_commands.Choice(name=field['name'], value=field['name'])
            for field in self.reminders[courses.index(course)]['fields']
            if current.lower() in field['name'].lower()
        ]

    @app_commands.command(description="Etablit un rappel pour un événement.")
    @app_commands.describe(course="Choisir le cours.", date="Choisir la date de l'événement.", event="Nom de l'événement", modality="Modalité de l'événement")
    @app_commands.checks.has_any_role(1291503961139838987, 1293714448263024650, 1293687392368197712)
    @app_commands.choices(option=[
        app_commands.Choice(name="add", value="1"),
        app_commands.Choice(name="edit", value="2"),
        app_commands.Choice(name="remove", value="3")
    ])
    @app_commands.autocomplete(course=channel_autocomplete)
    @app_commands.autocomplete(event=event_autocomplete)
    async def calendar(self, interaction: Interaction, option: app_commands.Choice[str], course: str, date: str, event: str, description: str = '', modality: str = ''):
        try:
            if ' ' not in date:
                date += ' 23:59'
            reminder_date = datetime.strptime(date, "%d/%m/%Y %H:%M")
            reminder_timestamp = f'<t:{int(reminder_date.timestamp())}:R>'

            match option.name:
                case "add":
                    if description:
                        description = f'{description}\n\n'
                    if modality:
                        modality = f'\n\n``{modality}``'
                    reminder = {
                        "name": course,
                        "fields": [
                            {
                                "name": event,
                                "date": f'{reminder_date}',
                                "description": description,
                                "modality": modality
                            }
                        ]
                    }
                    print('before')
                    try:
                        print('try')
                        msg = await self.calendar_channel.fetch_message(self.calendar_message_id)
                        for embed in msg.embeds:
                            if embed.title == course.upper():
                                embed.add_field(name=f'__{event}__', value=f'{description}Echéance: {reminder_timestamp}{modality}', inline=False)
                                await msg.edit(embeds=msg.embeds)
                                break
                    except NotFound:
                        print('except')
                        embed = Embed(title=course.upper())
                        embed.add_field(name=f'__{event}__', value=f'{description}Echéance: {reminder_timestamp}{modality}', inline=False)
                        msg = await self.calendar_channel.send(embed=embed)
                        self.bot.config.set('calendar_message_id', msg.id)
                    print('after')

                    for existing_reminder in self.reminders:
                        if existing_reminder['name'] == course:
                            existing_reminder['fields'].append(reminder['fields'][0])
                            break
                    else:
                        self.reminders.append(reminder)
                    self.save_reminders()
                    await interaction.response.send_message(f"Rappel créé pour {reminder_timestamp}", ephemeral=True)
                case "edit":
                    try:
                        msg = await self.calendar_channel.fetch_message(self.calendar_message_id)
                        for embed in msg.embeds:
                            if embed.title == course.upper():
                                for index, field in enumerate(embed.fields):
                                    if event in field.name:
                                        embed.set_field_at(index, name=f'__{event}__', value=f'{description}Echéance: {reminder_timestamp}{modality}', inline=False)
                                        await msg.edit(embeds=msg.embeds)
                                        for existing_reminder in self.reminders:
                                            if existing_reminder['name'] == course:
                                                for field in existing_reminder['fields']:
                                                    if field['name'] == event:
                                                        field['date'] = f'{reminder_date}'
                                                        field['description'] = description
                                                        field['modality'] = modality
                                                        break
                                                break

                                        self.save_reminders()

                                        await interaction.response.send_message(f"Rappel pour l'événement '{event}' du cours '{course}' modifié.", ephemeral=True)
                                        break
                                else:
                                    await interaction.response.send_message("Événement non trouvé.", ephemeral=True)
                                break
                        else:
                            await interaction.response.send_message("Cours non trouvé.", ephemeral=True)
                    except NotFound:
                        await interaction.response.send_message("Aucun message de rappel trouvé.", ephemeral=True)
                case "remove":
                    for existing_reminder in self.reminders:
                        if existing_reminder['name'] == course:
                            for field in existing_reminder['fields']:
                                if field['name'] == event:
                                    await self.remove_event(existing_reminder, field)
                                    await interaction.response.send_message(f"Rappel pour l'événement '{event}' du cours '{course}' supprimé.", ephemeral=True)
                                    break
                            else:
                                await interaction.response.send_message("Événement non trouvé.", ephemeral=True)
                            break
                    else:
                        await interaction.response.send_message("Cours non trouvé.", ephemeral=True)

        except ValueError:
            await interaction.response.send_message("Format invalide - JJ/MM/AAAA <HH:II>.", ephemeral=True)

    @calendar.error
    async def calendar_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Une erreur est survenue.\n{error}", ephemeral=True)

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        now = datetime.now()
        for reminder in self.reminders:
            for event in reminder['fields']:
                event_time = datetime.strptime(event['date'], "%Y-%m-%d %H:%M:%S")
                if now + timedelta(hours=1) - timedelta(seconds=30) <= event_time <= now + timedelta(hours=1) + timedelta(seconds=30):
                    await self.calendar_channel.send(f":warning: L'échéance *{event['name']}* du cours **{reminder['name'].upper()}** a lieu dans 1 heure !\n|| @everyone ||", delete_after=3600)
                elif now + timedelta(days=1) - timedelta(seconds=30) <= event_time <= now + timedelta(days=1) + timedelta(seconds=30):
                    await self.calendar_channel.send(f":warning: L'échéance *{event['name']}* du cours **{reminder['name'].upper()}** a lieu dans 1 jour !\n|| @everyone ||", delete_after=3600)
                elif now + timedelta(weeks=1) - timedelta(seconds=30) <= event_time <= now + timedelta(weeks=1) + timedelta(seconds=30):
                    await self.calendar_channel.send(f":warning: L'échéance *{event['name']}* du cours **{reminder['name'].upper()}** a lieu dans 1 semaine !\n|| @everyone ||", delete_after=3600)
                elif event_time <= now:
                    await self.calendar_channel.send(f":warning: L'échéance *{event['name']}* du cours **{reminder['name'].upper()}** vient d'avoir lieu !\n|| @everyone ||", delete_after=60)
                    await self.remove_event(reminder, event)

    async def remove_event(self, reminder, event):
        if self.calendar_message_id:
            try:
                msg = await self.calendar_channel.fetch_message(self.calendar_message_id)
                for embed in msg.embeds:
                    if embed.title == reminder['name'].upper():
                        for field in embed.fields:
                            if event['name'] in field.name:
                                embed.remove_field(embed.fields.index(field))
                                if not embed.fields:
                                    msg.embeds.remove(embed)
                                    if not msg.embeds:
                                        await msg.delete()
                                        self.bot.config.remove('calendar_message_id')
                                        break
                                await msg.edit(embeds=msg.embeds)
                                break
                        break
            except NotFound:
                pass

        reminder['fields'] = [field for field in reminder['fields'] if field['name'] != event['name']]
        if not reminder['fields']:
            self.reminders.remove(reminder)

        self.save_reminders()

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Calendar(bot))
