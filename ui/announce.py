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
        d = {'content': f'|| {value} ||', 'embed': self.embed}
        await interaction.response.send_message(**d, view=Confirm(**d), ephemeral=True)
        self.stop()


class Confirm(ui.View):
    def __init__(self, **kwargs):
        super().__init__(timeout=None)
        self.kwargs = kwargs

    @ui.button(label='Annuler', style=ButtonStyle.danger)
    async def cancel(self, interaction: Interaction, _: ui.Button):
        await interaction.response.edit_message(content='Annonce annulée.', suppress_embeds=True, view=None)

    @ui.button(label='Confirmer', style=ButtonStyle.success)
    async def confirm(self, interaction: Interaction, _: ui.Button):
        await interaction.channel.send(**self.kwargs)
        await interaction.response.edit_message(content='Annonce envoyée.', suppress_embeds=True, view=None)
