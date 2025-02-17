import re
from discord import app_commands, Interaction, Member, Embed, File
from discord.ext import commands

from utils import ConfigManager


class Common(commands.Cog):
    @app_commands.command(description="Affiche ou inscrit un profil LinkedIn.")
    @app_commands.describe(member='Le profil du membre à afficher', register='Inscrire un profil LinkedIn.')
    async def linkedin(self, ctx: Interaction, member: Member = None, register: str = ''):
        if register:
            pattern = r'https?://([a-z]{2,3}\.)?linkedin\.com/in/[^/]+/?'
            if not re.match(pattern, register):
                await ctx.response.send_message('Le lien LinkedIn est invalide', ephemeral=True)
                return
            user = {'linkedin': register}
            if member and ctx.user.guild_permissions.manage_roles:
                user['id'] = member.id
            else:
                user['id'] = ctx.user.id
            ConfigManager.append("users", user)
            await ctx.response.send_message(f'Profil LinkedIn enregistré pour {member.display_name if member else ctx.user.display_name}.')
        elif member:
            user_profile = next((user for user in ConfigManager.get("users", []) if user["id"] == member.id), None)
            if user_profile:
                await ctx.response.send_message(f'Profil LinkedIn de {member.display_name}: {user_profile["linkedin"]}')
            else:
                await ctx.response.send_message(f'Profil LinkedIn pour {member.display_name} non trouvé.')
        else:
            user_profile = next((user for user in ConfigManager.get("users", []) if user["id"] == ctx.user.id), None)
            if user_profile:
                await ctx.response.send_message(f'Votre profil LinkedIn: {user_profile["linkedin"]}')
            else:
                await ctx.response.send_message('Votre profil LinkedIn non trouvé.')

    @app_commands.command(description="S'attribuer ou s'enlever le rôle de joueur.")
    async def gaming(self, ctx: Interaction):
        role = ctx.guild.get_role(1291867840067932304)
        if role in ctx.user.roles:
            await ctx.user.remove_roles(role)
            await ctx.response.send_message('Rôle de joueur retiré.', ephemeral=True)
        else:
            await ctx.user.add_roles(role)
            await ctx.response.send_message('Rôle de joueur attribué.', ephemeral=True)

    @app_commands.command(description="Affiche le lien d'invitation du serveur.")
    async def invite(self, ctx: Interaction):
        embed = Embed(title='Invitation', description='Scannez ce QR Code et rejoignez le serveur discord du Master Cybersécurité de Paris Cité.\n\nTous profils acceptés, curieux, intéressés ou experts en cybersécurité ! Bot multifonction intégré afin de dynamiser au maximum le serveur.', color=0x8B1538)
        file = File("assets/qrcode.png", filename="invite.png")
        embed.set_image(url='attachment://invite.png')
        embed.set_footer(text=f'Master Cybersécurité - Université Paris Cité - {len([member for member in ctx.guild.members if not member.bot])} membres', icon_url=ctx.guild.icon.url)
        await ctx.response.send_message(file=file, embed=embed)

    @app_commands.command(description="Affiche les informations sur le bot.")
    async def about(self, ctx: Interaction):
        embed = Embed(title='À propos de moi', description='Je suis un bot Discord créé par [Vincent Cohadon](https://fr.linkedin.com/in/vincent-cohadon) pour le Master Cybersécurité de Paris Cité.')
        file = File("assets/f1d0.png", filename="f1d0.png")
        embed.set_thumbnail(url='attachment://f1d0.png')
        await ctx.response.send_message(file=file, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Common())
