from discord import ui, Interaction, ButtonStyle, SelectOption


class DropdownView(ui.View):
    def __init__(self, guild, embed, mentions):
        super().__init__()
        self.add_item(Dropdown([SelectOption(label=role.name, value=role.id) for role in guild.roles if role.name not in ['@everyone', 'DeadBeef']], len(guild.roles) - 2, embed, mentions))


class Dropdown(ui.Select):
    def __init__(self, options, max_values, embed, mentions):
        super().__init__(placeholder='Choisissez un rôle', options=options, min_values=1, max_values=max_values)
        self.embed = embed
        self.mentions = mentions
    
    async def callback(self, interaction: Interaction):
        roles = [interaction.guild.get_role(int(value)) for value in self.values]
        value = ' '.join([role.mention for role in roles])
        self.embed.add_field(name='Rôles concernés', value=value)
        if self.mentions:
            value += ' ' + ' '.join([match.group(0) for match in self.mentions])
        await interaction.response.send_message(embed=self.embed, view=ConfirmView(self.embed, value), ephemeral=True)


class ConfirmView(ui.View):
    def __init__(self, embed, value):
        super().__init__()
        self.add_item(ConfirmButton(embed, value))


class ConfirmButton(ui.Button):
    def __init__(self, embed, value):
        super().__init__(label='Confirmer', style=ButtonStyle.success)
        self.embed = embed
        self.value = value

    async def callback(self, interaction: Interaction):
        await interaction.channel.send(f'|| {self.value} ||', embed=self.embed)
        await interaction.response.send_message('Annonce envoyée.', ephemeral=True)
