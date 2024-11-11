from discord import app_commands, Interaction, Embed
from discord.errors import NotFound
from discord.ext import commands, tasks

from datetime import datetime, timedelta
import re


class Reminder(commands.Cog):
    """
    @brief A Discord bot cog for managing reminders.
    This class provides functionality to create, edit, and remove reminders for events in a Discord server. It also includes
    autocomplete features for channels and events, and periodically checks for upcoming reminders to notify users.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initializes the Reminder cog.
        @param bot: The instance of the bot.
        """
        

        self.bot = bot
        self.reminders = self.load_reminders()
        self.reminder_channel_id = 1293319532361809986
        self.check_reminders.start()

    def load_reminders(self):
        """
        @brief Loads the reminders from the bot's configuration.
        @return A list of reminders if they exist, otherwise an empty list.
        """

        return self.bot.config.get('reminders', [])
    
    def save_reminders(self):
        """
        @brief Saves the current reminders to the bot's configuration.
        This method updates the bot's configuration with the current state of reminders.
        It stores the reminders in the 'reminders' section of the configuration.
        @return None
        """

        self.bot.config.set('reminders', self.reminders)
    
    async def channel_autocomplete(self, _: Interaction, current: str) -> list[app_commands.Choice[str]]:
        """
        @brief Autocompletes channel names based on the current input.
        @param _ Unused Interaction parameter.
        @param current The current input string to match against channel names.
        @return A list of app_commands.Choice objects containing matching channel names.
        """

        category = self.bot.get_channel(1289244121004900487)

        return [
            app_commands.Choice(name=channel.name, value=channel.name)
            for channel in category.text_channels
            if current.lower() in re.sub(r':.+?:', '', channel.name.lower())
        ]
    
    async def event_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        """
        Handles the autocomplete event for the reminder options.
        @param interaction: The interaction object containing the context of the command.
        @type interaction: Interaction
        @param current: The current input string to match against reminder fields.
        @type current: str
        @return: A list of app_commands.Choice objects that match the current input.
        @rtype: list[app_commands.Choice[str]]
        """

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
        """
        @brief Handles calendar-related interactions for reminders.
        @param interaction The interaction object representing the user's interaction.
        @param option The choice option selected by the user.
        @param course The name of the course for which the reminder is being set.
        @param date The date and time for the reminder in the format "DD/MM/YYYY HH:MM".
        @param event The name of the event for which the reminder is being set.
        @param description (Optional) A description of the event.
        @param modality (Optional) The modality of the event.
        @return None
        This function handles three types of operations based on the option selected by the user:
        - Option 1: Creates a new reminder for the specified course and event.
        - Option 2: Modifies an existing reminder for the specified course and event.
        - Option 3: Deletes an existing reminder for the specified course and event.
        The function also handles errors related to invalid date formats and missing reminders.
        """

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
        """
        Handles errors that occur during the execution of calendar-related commands.
        @param interaction: The interaction that triggered the error.
        @type interaction: Interaction
        @param error: The exception that was raised.
        @type error: Exception
        If the error is an instance of app_commands.MissingAnyRole, it sends a message indicating that the user does not have permission to use the command.
        """

        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        """
        @brief Checks for upcoming reminders and sends notifications.
        This asynchronous method iterates through the list of reminders and checks if any events are 
        scheduled to occur within the next hour or the next day. If an event is found to be within 
        these timeframes, a notification message is sent to the specified reminder channel. If an 
        event has already occurred, it is removed from the list of reminders.
        @details
        - Sends a notification 1 hour before the event.
        - Sends a notification 1 day before the event.
        - Sends a notification 1 week before the event.
        - Removes the event if it has already occurred.
        @param self The instance of the class containing the reminders and bot information.
        @return None
        """
        
        now = datetime.now()
        reminder_channel = self.bot.get_channel(self.reminder_channel_id)
        for reminder in self.reminders:
            for event in reminder['fields']:
                event_time = datetime.strptime(event['date'], "%Y-%m-%d %H:%M:%S")
                if now + timedelta(hours=1) - timedelta(seconds=30) <= event_time <= now + timedelta(hours=1) + timedelta(seconds=30):
                    await reminder_channel.send(f":warning: L'échéance *{event['name']}* du cours **{reminder['name'].upper()}** a lieu dans 1 heure !\n|| @everyone ||", delete_after=3600)
                elif now + timedelta(days=1) - timedelta(seconds=30) <= event_time <= now + timedelta(days=1) + timedelta(seconds=30):
                    await reminder_channel.send(f":warning: L'échéance *{event['name']}* du cours **{reminder['name'].upper()}** a lieu dans 1 jour !\n|| @everyone ||", delete_after=3600)
                elif now + timedelta(weeks=1) - timedelta(seconds=30) <= event_time <= now + timedelta(weeks=1) + timedelta(seconds=30):
                    await reminder_channel.send(f":warning: L'échéance *{event['name']}* du cours **{reminder['name'].upper()}** a lieu dans 1 semaine !\n|| @everyone ||", delete_after=3600)
                elif event_time <= now:
                    await reminder_channel.send(f":warning: L'échéance *{event['name']}* du cours **{reminder['name'].upper()}** vient d'avoir lieu !\n|| @everyone ||", delete_after=60)
                    await self.remove_event(reminder, event, reminder_channel)

    async def remove_event(self, reminder, event, reminder_channel):
        """
        @brief Removes an event from a reminder and updates the reminder message in the specified channel.
        This function removes a specified event from a given reminder. It updates the reminder message
        in the specified channel by removing the event from the message embed. If the reminder or event
        no longer contains any fields, they are removed accordingly. The function also handles the case
        where the reminder message is deleted if it becomes empty.
        @param reminder The reminder dictionary containing the event to be removed.
        @param event The event dictionary to be removed from the reminder.
        @param reminder_channel The channel object where the reminder message is posted.
        @return None
        """

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
        """
        @brief Waits until the bot is ready before checking reminders.
        This asynchronous method ensures that the bot is fully initialized and ready
        before proceeding with any reminder checks.
        """

        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    """
    @brief Asynchronous function to set up the Reminder cog for the bot.
    This function is used to add the Reminder cog to the bot instance.
    @param bot The instance of the bot to which the Reminder cog will be added.
    """

    await bot.add_cog(Reminder(bot))