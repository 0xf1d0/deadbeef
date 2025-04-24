import re
from discord import app_commands, Interaction, Member, Embed, File, Color, Activity, ActivityType
from discord.ext import tasks
from discord.ext import commands

from utils import ConfigManager, WELCOME_MESSAGE, WELCOME_CHANNEL, LOG_CHANNEL, CYBER_COLOR, CYBER
from ui.auth import Authentication

from api.api import RootMe


class Common(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_status.start()
    
    @commands.Cog.listener()
    async def on_ready(self):
        welcome = self.bot.get_guild(CYBER.id).get_channel(WELCOME_CHANNEL.id)
        welcome_message = await welcome.fetch_message(WELCOME_MESSAGE.id)

        await welcome_message.edit(content=ConfigManager.get('welcome_message'), view=Authentication())
        
    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        guild = member.guild
        channel = guild.get_channel(LOG_CHANNEL.id)
        embed = Embed(title=f'{member} joined', color=Color.green())\
                .add_field(name='Display Name', value=member.display_name, inline=False)\
                .add_field(name='Joined at', value=member.joined_at.strftime('%Y-%m-%d %H:%M:%S'), inline=False)\
                .add_field(name='Roles', value='\n'.join([f"{i+1}. {role.mention} - {role.id}" for i, role in enumerate(member.roles[1:])]), inline=False)\
                .set_image(url=member.display_avatar.url)\
                .set_footer(text=f'ID: {member.id}')

        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        guild = member.guild
        channel = guild.get_channel(LOG_CHANNEL.id)
        embed = Embed(title=f'{member} left', color=Color.red())\
                .add_field(name='Display Name', value=member.display_name, inline=False)\
                .add_field(name='Joined at', value=member.joined_at.strftime('%Y-%m-%d %H:%M:%S'), inline=False)\
                .add_field(name='Roles', value='\n'.join([f"{i+1}. {role.mention} - {role.id}" for i, role in enumerate(member.roles[1:])]), inline=False)\
                .set_image(url=member.display_avatar.url)\
                .set_footer(text=f'ID: {member.id}')

        await channel.send(embed=embed)

    @app_commands.command(description="Affiche ou inscrit un profil LinkedIn.")
    @app_commands.describe(member='Le profil du membre à afficher', register='Inscrire un profil LinkedIn.')
    async def linkedin(self, ctx: Interaction, member: Member = None, register: str = ''):
        if register:
            pattern = r'https?://([a-z]{2,3}\.)?linkedin\.com/in/[^/]+/?'
            if not re.match(pattern, register):
                await ctx.response.send_message('Le lien LinkedIn est invalide', ephemeral=True)
                return
            user_id = member.id if member and ctx.user.guild_permissions.manage_roles else ctx.user.id
            users = ConfigManager.get("users", [])
            user = next((u for u in users if u["id"] == user_id), None)
            if user:
                user['linkedin'] = register
            else:
                user = {'id': user_id, 'linkedin': register}
                users.append(user)
            ConfigManager.set("users", users)
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

    @app_commands.command(description="Affiche le QR Code d'invitation au serveur.")
    async def invite(self, interaction: Interaction):
        guild = interaction.guild
        invites = await guild.invites()

        embed = Embed(title=f'{guild.name}', description=f'Scannez ce QR Code et rejoignez le serveur discord de la communauté {guild.name}.', color=CYBER_COLOR)\
            .set_image(url='attachment://invite.png')\
            .set_footer(text=f'{guild.name} - {len([member for member in guild.members if not member.bot])} membres', icon_url=guild.icon.url)
        permanent_invite = next((inv for inv in invites if inv.max_age == 0), None)
        if permanent_invite:
            embed.add_field(name="Lien", value=f'{permanent_invite.url}')
            
        file = File("assets/qrcode.png", filename="invite.png")
        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(description="Affiche les informations sur le bot.")
    async def about(self, ctx: Interaction):
        embed = Embed(title='À propos de moi', description='Je suis un bot Discord créé par [Vincent Cohadon](https://fr.linkedin.com/in/vincent-cohadon) pour le Master Cybersécurité de Paris Cité.')
        file = File("assets/f1d0.png", filename="f1d0.png")
        embed.set_thumbnail(url='attachment://f1d0.png')
        await ctx.response.send_message(file=file, embed=embed)

    @app_commands.command(description="Affiche le profil root-me d'un utilisateur.")
    async def profile(self, ctx: Interaction, rootme_id: str = None, discord_user: Member = None):
        users = ConfigManager.get("users", [])
        
        async def fetch_and_send(rootme_id: str, user: Member = None):
            try:
                await RootMe.get_authors(rootme_id)
                base_msg = f"Profil root-me de {rootme_id}: https://www.root-me.org/{rootme_id}"
                if user:
                    base_msg = f"Profil root-me de {user.display_name}: " + base_msg.split(':', 1)[1]
                await ctx.response.send_message(base_msg)
            except Exception as e:
                await ctx.response.send_message(f"Erreur: {str(e)}", ephemeral=True)
        
        # Logique de sélection des cibles
        if rootme_id:
            await fetch_and_send(rootme_id)
            return
        
        target_user = discord_user or ctx.user
        user_data = next((u for u in users if u["id"] == target_user.id), None)
        
        if user_data and user_data.get("rootme"):
            await fetch_and_send(user_data["rootme"], target_user)
        else:
            msg = "Votre profil root-me non trouvé." if target_user == ctx.user else f"Profil root-me pour {target_user.display_name} non trouvé."
            await ctx.response.send_message(msg)
    
    @tasks.loop(hours=1)
    async def update_status(self):
        """Update the bot's status."""
        guild = self.bot.get_guild(CYBER.id)
        if guild:
            await self.bot.change_presence(
                activity=Activity(
                    type=ActivityType.watching,
                    name=f"{len([member for member in guild.members if not member.bot])} members"
                )
            )
    
    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Common(bot))
