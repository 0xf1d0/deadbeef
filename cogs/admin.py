from discord.ext import commands
from discord import app_commands, Interaction, Embed, Member

from ui.announce import Announcement
from utils import ROLE_FI, ROLE_FA, ROLE_M1, ROLE_M2, ROLE_DELEGATE, ROLE_MANAGER, ROLE_NOTABLE


class Admin(commands.Cog):    
    @app_commands.command(description="Annoncer un message.")
    @app_commands.checks.has_any_role(ROLE_DELEGATE, ROLE_MANAGER, ROLE_NOTABLE)
    async def announce(self, interaction: Interaction):
        modal = Announcement()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(description="Efface un nombre de messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: Interaction, limit: int):
        await interaction.response.send_message(f'{limit} messages ont été effacés.', ephemeral=True)
        await interaction.channel.purge(limit=limit)
    
    @app_commands.command(description="Réinitialise les grades.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(self, interaction: Interaction, member: Member = None):
        if member:
            roles = [role for role in member.roles if role not in [ROLE_FI, ROLE_FA, ROLE_M1, ROLE_M2]]
            await member.edit(roles=roles)
            await interaction.response.send_message(f'Les rôles de {member.display_name} ont été réinitialisés.', ephemeral=True)
        else:
            members = interaction.guild.members
            for member in members:
                roles = [role for role in member.roles if role not in [ROLE_FI, ROLE_FA, ROLE_M1, ROLE_M2]]
                await member.edit(roles=roles)
                await member.remove_roles(ROLE_FI, ROLE_FA, ROLE_M1, ROLE_M2)
            await interaction.response.send_message(f'Les rôles de **{len(members)}** membres ont été réinitialisés.', ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin())
