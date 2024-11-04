from discord.ext import commands
from discord import app_commands, Interaction, ui, ButtonStyle, Embed, SelectOption
import functools, re


def restrict_channel(channel_id):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, ctx: Interaction, *args, **kwargs):
            if ctx.channel.id != channel_id:
                await ctx.response.send_message(f"Cette commande ne peut être utilisée que dans le salon <#{channel_id}>.", ephemeral=True)
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(description="Annoncer un message.")
    @app_commands.describe(title='Le titre de l\'annonce.', message='Le message à annoncer.')
    @app_commands.checks.has_any_role(1291503961139838987, 1293714448263024650)
    async def announce(self, ctx: Interaction, title: str, message: str):
        embed = Embed(title=title, description=message.replace('\\n', '\n'), color=0x8B1538)
        embed.set_footer(text=f"Annoncé par {ctx.user.display_name}", icon_url=ctx.user.avatar.url)
        matches = []
        for match in re.finditer(r'<@(\d{17}|\d{18})>', message):
            if match.group(1) not in matches:
                matches.append(match)
        await ctx.response.send_message('Quels rôles voulez-vous mentionner ?', view=DropdownView(ctx.guild, embed, matches), ephemeral=True)
    
    @announce.error
    async def announce_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)

    @app_commands.command(description="Efface un nombre de messages.")
    @app_commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: Interaction, limit: int):
        await ctx.response.send_message(f'{limit} messages ont été effacés.', ephemeral=True)
        await ctx.channel.purge(limit=limit)

    @purge.error
    async def purge_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)


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


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
