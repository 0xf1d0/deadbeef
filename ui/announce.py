from discord import ui, Interaction, ButtonStyle

from utils import ROLE_FI, ROLE_FA


class Announcement(ui.View):
    def __init__(self, embed, mentions):
        super().__init__(timeout=None)
        self.embed = embed
        self.mentions = mentions
    
    @ui.select(cls=ui.RoleSelect, placeholder='Choisissez un/des rôle/s', max_values=4, default_values=[ROLE_FI, ROLE_FA])
    async def select_roles(self, interaction: Interaction, select: ui.RoleSelect):
        value = ' '.join([role.mention for role in select.values])
        self.embed.add_field(name='Rôles concernés', value=value)
        if self.mentions:
            value += ' ' + ' '.join(self.mentions)
        await interaction.response.send_message(embed=self.embed, view=Confirm(self.embed, value), ephemeral=True)


class Confirm(ui.View):
    def __init__(self, embed, value):
        super().__init__(timeout=None)
        self.value = value
        self.embed = embed

    @ui.button(label='Annuler', style=ButtonStyle.danger)
    async def cancel(self, _: ui.Button, interaction: Interaction):
        await interaction.response.edit_message('Action annulée.')

    @ui.button(label='Confirmer', style=ButtonStyle.success)
    async def confirm(self, _: ui.Button, interaction: Interaction):
        await interaction.channel.send(f'|| {self.value} ||', embed=self.embed)
        await interaction.response.edit_message('Annonce envoyée.')
