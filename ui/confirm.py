import discord

class Confirm(discord.ui.View):
    def __init__(self, **kwargs):
        super().__init__(timeout=None)
        self.kwargs = kwargs

    @discord.ui.button(label='Annuler', style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.edit_message(content='Annonce annulée.', suppress_embeds=True, view=None)
        self.stop()

    @discord.ui.button(label='Confirmer', style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.channel.send(**self.kwargs)
        await interaction.response.edit_message(content='Annonce envoyée.', suppress_embeds=True, view=None)
        self.stop()
