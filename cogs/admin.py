from discord.ext import commands
from discord import app_commands, Interaction, Embed

import functools, re

from ui.announce import DropdownView


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
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, ctx: Interaction, limit: int):
        await ctx.response.send_message(f'{limit} messages ont été effacés.', ephemeral=True)
        await ctx.channel.purge(limit=limit)

    @purge.error
    async def purge_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
