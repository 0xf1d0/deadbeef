from discord import app_commands, Interaction, TextChannel, Embed
from discord.errors import NotFound
from discord.ext import commands
from datetime import datetime


class Reminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminders = self.load_reminders()

    def load_reminders(self):
        return self.bot.config.get('reminders', [])
    
    def save_reminders(self):
        self.bot.config.set('reminders', self.reminders)

    @app_commands.command(description="Etablit un rappel pour un événement.")
    @app_commands.describe(course="Choisir le cours.", date="Choisir la date de l'événement.", event="Nom de l'événement", modality="Modalité de l'événement")
    @app_commands.checks.has_role(1291503961139838987)
    @app_commands.choices(option=[
        app_commands.Choice(name="add", value="1"),
        app_commands.Choice(name="remove", value="2")
    ])
    async def calendar(self, interaction: Interaction, option: app_commands.Choice[str], course: TextChannel, date: str, event: str, description: str = None, modality: str = None):
        try:
            reminder_date = f'<t:{int(datetime.strptime(date, "%d/%m/%Y").timestamp())}:'
            reminders_channel = interaction.guild.get_channel(1293319532361809986)
            reminders_message_id = self.bot.config.get('reminders_message_id')
            msg = None

            if reminders_message_id:
                try:
                    msg = await reminders_channel.fetch_message(reminders_message_id)
                except NotFound:
                    pass

            if option.value == "1":
                reminder = {
                    "name": course.name,
                    "fields": [
                        {
                            "name": event,
                            "date": reminder_date,
                            "description": description if description else "",
                            "modality": modality if modality else ""
                        }
                    ]
                }

                if msg:
                    for embed in msg.embeds:
                        if embed.title == course.name.upper():
                            embed.add_field(name=event, value=(description + "\n\n" if description else "") + f'{reminder_date}R>' + ("\n\n" + modality if modality else ""))
                            await msg.edit(embeds=msg.embeds)
                            break
                    else:
                        embed = Embed(title=course.name.upper())
                        embed.add_field(name=event, value=(description + "\n\n" if description else "") + f'{reminder_date}R>' + ("\n\n" + modality if modality else ""))
                        await msg.edit(embeds=msg.embeds + [embed])
                else:
                    embed = Embed(title=course.name.upper())
                    embed.add_field(name=event, value=(description + "\n\n" if description else "") + f'{reminder_date}R>' + ("\n\n" + modality if modality else ""))
                    msg = await reminders_channel.send(embeds=[embed])
                    self.bot.config.set('reminders_message_id', msg.id)

                self.reminders.append(reminder)
                self.save_reminders()

                await interaction.response.send_message(f"Rappel créé pour le {reminder_date + 'D>'}", ephemeral=True)

            elif option.value == "2":
                if msg:
                    for embed in msg.embeds:
                        if embed.title == course.name.upper():
                            for field in embed.fields:
                                if field.name == event:
                                    embed.remove_field(embed.fields.index(field))
                                    await msg.edit(embeds=msg.embeds)
                                    break
                            else:
                                await interaction.response.send_message("Événement non trouvé.", ephemeral=True)
                                return
                            break
                    else:
                        await interaction.response.send_message("Cours non trouvé.", ephemeral=True)
                        return

                    self.reminders = [reminder for reminder in self.reminders if not (reminder['name'] == course.name and any(field['name'] == event for field in reminder['fields']))]
                    self.save_reminders()

                    await interaction.response.send_message(f"Rappel pour l'événement '{event}' du cours '{course.name}' supprimé.", ephemeral=True)
                else:
                    await interaction.response.send_message("Aucun message de rappel trouvé.", ephemeral=True)

        except ValueError:
            await interaction.response.send_message("Format invalide - JJ/MM/AAAA.", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        if self.reminders:
            channel = self.bot.get_channel(1293319532361809986)
            reminders_message_id = self.bot.config.get('reminders_message_id')
            msg = None

            if reminders_message_id:
                try:
                    msg = await channel.fetch_message(reminders_message_id)
                except NotFound:
                    pass

            if not msg:
                embed = Embed(title=self.reminders[0]['name'].upper())
                for field in self.reminders[0]['fields']:
                    modality = field['modality']
                    description = field['description']
                    embed.add_field(name=field['name'], value=(description + "\n\n" if description else "") + f'{field['date']}R>' + ("\n\n" + modality if modality else ""))
                msg = await channel.send(embeds=[embed])
                self.bot.config.set('reminders_message_id', msg.id)

                if len(self.reminders) > 1:
                    embeds = []
                    for reminder in self.reminders[1:]:
                        embed = Embed(title=reminder['name'].upper())
                        for field in reminder['fields']:
                            modality = field['modality']
                            description = field['description']
                            embed.add_field(name=field['name'], value=(description + "\n\n" if description else "") + f'{field['date']}R>' + ("\n\n" + modality if modality else ""))
                        embeds.append(embed)
                    await msg.edit(embeds=msg.embeds + embeds)


async def setup(bot: commands.Bot):
    await bot.add_cog(Reminder(bot))
