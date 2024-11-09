from discord import app_commands, Interaction, Embed
from discord.errors import NotFound
from discord.ext import commands, tasks

from datetime import datetime, timedelta
import re


class Reminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminders = self.load_reminders()
        self.reminder_channel_id = 1293319532361809986
        self.check_reminders.start()

    def load_reminders(self):
        return self.bot.config.get('reminders', [])
    
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
    async def calendar(self, interaction: Interaction, option: app_commands.Choice[str], course: str, date: str, event: str, description: str = None, modality: str = None):
        try:
            if ' ' not in date:
                date += ' 23:59'
            reminder_date = datetime.strptime(date, "%d/%m/%Y %H:%M")
            reminder_timestamp = f'<t:{int(reminder_date.timestamp())}:R>'
            reminders_channel = interaction.guild.get_channel(self.reminder_channel_id)
            reminders_message_id = self.bot.config.get('reminders_message_id')
            msg = None

            if reminders_message_id:
                try:
                    msg = await reminders_channel.fetch_message(reminders_message_id)
                except NotFound:
                    pass

            if option.value == "1":
                reminder = {
                    "name": course,
                    "fields": [
                        {
                            "name": event,
                            "date": f'{reminder_date}',
                            "description": description if description else "",
                            "modality": modality if modality else ""
                        }
                    ]
                }

                if msg:
                    for embed in msg.embeds:
                        if embed.title == course.upper():
                            embed.add_field(name=f'__{event}__', value=(description + "\n\n" if description else "") + f'Echéance: {reminder_timestamp}' + ("\n\n``" + modality + '``' if modality else ""), inline=False)
                            await msg.edit(embeds=msg.embeds)
                            break
                    else:
                        embed = Embed(title=course.upper())
                        embed.add_field(name=f'__{event}__', value=(description + "\n\n" if description else "") + f'Echéance: {reminder_timestamp}' + ("\n\n``" + modality + '``' if modality else ""), inline=False)
                        await msg.edit(embeds=msg.embeds + [embed])
                else:
                    embed = Embed(title=course.upper())
                    embed.add_field(name=f'__{event}__', value=(description + "\n\n" if description else "") + f'Echéance: {reminder_timestamp}' + ("\n\n``" + modality + '``' if modality else ""), inline=False)
                    msg = await reminders_channel.send(embeds=[embed])
                    self.bot.config.set('reminders_message_id', msg.id)

                for existing_reminder in self.reminders:
                    if existing_reminder['name'] == course:
                        existing_reminder['fields'].append({
                            "name": event,
                            "date": f'{reminder_date}',
                            "description": description if description else "",
                            "modality": modality if modality else ""
                        })
                        break
                else:
                    self.reminders.append(reminder)

                self.save_reminders()

                await interaction.response.send_message(f"Rappel créé pour {reminder_timestamp}", ephemeral=True)

            elif option.value == "2":
                if msg:
                    for embed in msg.embeds:
                        if embed.title == course.upper():
                            for index, field in enumerate(embed.fields):
                                if event in field.name:
                                    embed.set_field_at(index, name=field.name, value=(description + "\n\n" if description else "") + f'Echéance: {reminder_timestamp}' + ("\n\n``" + modality + '``' if modality else ""), inline=False)
                                    await msg.edit(embeds=msg.embeds)
                                    break
                            else:
                                await interaction.response.send_message("Événement non trouvé.", ephemeral=True)
                                return
                            break
                    else:
                        await interaction.response.send_message("Cours non trouvé.", ephemeral=True)
                        return

                    for existing_reminder in self.reminders:
                        if existing_reminder['name'] == course:
                            for field in existing_reminder['fields']:
                                if field['name'] == event:
                                    field['date'] = f'{reminder_date}'
                                    field['description'] = description if description else ""
                                    field['modality'] = modality if modality else ""
                                    break
                            break

                    self.save_reminders()

                    await interaction.response.send_message(f"Rappel pour l'événement '{event}' du cours '{course}' modifié.", ephemeral=True)
                else:
                    await interaction.response.send_message("Aucun message de rappel trouvé.", ephemeral=True)

            elif option.value == "3":
                for existing_reminder in self.reminders:
                    if existing_reminder['name'] == course:
                        for field in existing_reminder['fields']:
                            if field['name'] == event:
                                await self.remove_event(existing_reminder, field, reminders_channel)
                                await interaction.response.send_message(f"Rappel pour l'événement '{event}' du cours '{course}' supprimé.", ephemeral=True)
                                return
                        await interaction.response.send_message("Événement non trouvé.", ephemeral=True)
                        return
                await interaction.response.send_message("Cours non trouvé.", ephemeral=True)

        except ValueError:
            await interaction.response.send_message("Format invalide - JJ/MM/AAAA <HH:II>.", ephemeral=True)

    @calendar.error
    async def calendar_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        now = datetime.now()
        reminder_channel = self.bot.get_channel(self.reminder_channel_id)
        for reminder in self.reminders:
            for event in reminder['fields']:
                event_time = event['date']
                if now + timedelta(hours=1) - timedelta(seconds=30) <= event_time <= now + timedelta(hours=1) + timedelta(seconds=30):
                    await reminder_channel.send(f"@everyone L'échéance '{event['name']}' du cours '{reminder['name']}' a lieu dans 1 heure!")
                elif now + timedelta(days=1) - timedelta(seconds=30) <= event_time <= now + timedelta(days=1) + timedelta(seconds=30):
                    await reminder_channel.send(f"@everyone L'échéance '{event['name']}' du cours '{reminder['name']}' a lieu dans 1 jour!")
                elif event_time <= now:
                    await self.remove_event(reminder, event, reminder_channel)

    async def remove_event(self, reminder, event, reminder_channel):
        reminders_message_id = self.bot.config.get('reminders_message_id')
        if reminders_message_id:
            try:
                msg = await reminder_channel.fetch_message(reminders_message_id)
                for embed in msg.embeds:
                    if embed.title == reminder['name'].upper():
                        for field in embed.fields:
                            if event['name'] in field.name:
                                embed.remove_field(embed.fields.index(field))
                                if not embed.fields:
                                    msg.embeds.remove(embed)
                                    if not msg.embeds:
                                        await msg.delete()
                                        self.bot.config.remove('reminders_message_id')
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
    await bot.add_cog(Reminder(bot))