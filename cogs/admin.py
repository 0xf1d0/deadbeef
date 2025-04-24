from discord.ext import commands
from discord import app_commands, Interaction, Embed, Member

import re

from ui.announce import Announcement
from utils import ROLE_FI, ROLE_FA, ROLE_M1, ROLE_M2


class Admin(commands.Cog):    
    @app_commands.command(description="Annoncer un message.")
    @app_commands.describe(title='Le titre de l\'annonce.', message='Le message à annoncer.')
    @app_commands.checks.has_any_role(1291503961139838987, 1293714448263024650, 1293687392368197712)
    async def announce(self, ctx: Interaction, title: str, message: str):
        embed = Embed(title=title, description=message.replace('\\n', '\n'), color=0x8B1538)
        embed.set_footer(text=f"Annoncé par {ctx.user.display_name}", icon_url=ctx.user.avatar.url)
        mentions = set(re.findall(r'<@\d+>', message))
        await ctx.response.send_message('Quels rôles voulez-vous mentionner ?', view=Announcement(embed, mentions), ephemeral=True)
    
    @announce.error
    async def announce_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)

    @app_commands.command(description="Efface un nombre de messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, ctx: Interaction, limit: int):
        await ctx.response.send_message(f'{limit} messages ont été effacés.', ephemeral=True)
        await ctx.channel.purge(limit=limit)
    
    @app_commands.command(description="Réinitialise les grades.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(self, ctx: Interaction, member: Member = None):
        if member:
            roles = [role for role in member.roles if role not in [ROLE_FI, ROLE_FA, ROLE_M1, ROLE_M2]]
            await member.edit(roles=roles)
            await ctx.response.send_message(f'Les rôles de {member.display_name} ont été réinitialisés.', ephemeral=True)
        else:
            members = ctx.guild.members
            for member in members:
                roles = [role for role in member.roles if role not in [ROLE_FI, ROLE_FA, ROLE_M1, ROLE_M2]]
                await member.edit(roles=roles)
                await member.remove_roles(ROLE_FI, ROLE_FA, ROLE_M1, ROLE_M2)
            await ctx.response.send_message(f'Les rôles de **{len(members)}** membres ont été réinitialisés.', ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin())
