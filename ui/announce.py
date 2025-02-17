from discord import ui, Interaction, ButtonStyle


class Announcement(ui.View):
    def __init__(self, embed, mentions):
        super().__init__(timeout=None)
        self.embed = embed
        self.mentions = mentions
    
    @ui.select(cls=ui.RoleSelect, placeholder='Choisissez un/des rôle/s', max_values=4)
    async def select_roles(self, interaction: Interaction, select: ui.RoleSelect):
        value = ' '.join([role.mention for role in select.values])
        self.embed.add_field(name='Rôles concernés', value=value)
        if self.mentions:
            value += ' ' + ' '.join(self.mentions)
        for child in self.children[1:]:
            child.disabled = False
        await interaction.message.edit(embed=self.embed, ephemeral=True)
    
    @ui.button(label='Annuler', style=ButtonStyle.danger, disabled=True)
    async def cancel(self, interaction: Interaction):
        await interaction.message.edit('Annonce annulée.', ephemeral=True)
        
    @ui.button(label='Confirmer', style=ButtonStyle.success, disabled=True)
    async def confirm(self, interaction: Interaction):
        await interaction.channel.send(f'|| {self.value} ||', embed=self.embed)
        await interaction.response.send_message('Annonce envoyée.', ephemeral=True)
