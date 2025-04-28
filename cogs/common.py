import datetime
from typing import Optional
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

    @app_commands.command(description="Affiche le QR Code d'invitation au serveur.")
    async def invite(self, interaction: Interaction):
        guild = interaction.guild
        invites = await guild.invites()

        embed = Embed(title=f'{guild.name}', description=f'Scannez ce QR Code pour rejoindre la communauté {guild.name}. 🚀', color=CYBER_COLOR)\
            .set_image(url='attachment://invite.png')\
            .set_footer(text=f'{guild.name} - {len([member for member in guild.members if not member.bot])} membres', icon_url=guild.icon.url)
        permanent_invite = next((inv for inv in invites if inv.max_age == 0), None)
        if permanent_invite:
            embed.add_field(name="Lien", value=f'{permanent_invite.url}')
            
        file = File("assets/qrcode.png", filename="invite.png")
        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(description="Affiche les informations du bot.")
    async def about(self, interaction: Interaction):
        embed = Embed(title='À propos de moi', description=f'Je suis un bot développé par [Vincent Cohadon](https://fr.linkedin.com/in/vincent-cohadon) pour la communauté {interaction.guild.name}.')
        file = File("assets/f1d0.png", filename="f1d0.png")
        embed.set_thumbnail(url='attachment://f1d0.png')
        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(description="Afficher son profil ou celui d'un autre utilisateur.")
    @app_commands.describe(member="Le membre dont vous souhaitez voir le profil")
    async def profile(self, interaction: Interaction, member: Optional[Member] = None):
        users = ConfigManager.get("users", [])
        
        # Définir l'utilisateur cible en fonction des paramètres
        target_user = member or interaction.user
        
        await interaction.response.defer(thinking=True)
        
        # Créer l'embed pour l'affichage du profil
        embed = Embed(
            title=f"🔍 Profil de {target_user.display_name}",
            color=Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # Ajouter les informations Discord
        member_since = target_user.joined_at or datetime.datetime.now()
        
        embed.add_field(
            name="📊 Info Discord",
            value=f"🕒 Sur le serveur depuis: <t:{int(member_since.timestamp())}:d>\n"
                f"🆔 ID: {target_user.id}",
            inline=False
        )
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Trouver les données utilisateur dans la configuration
        user_data = next((u for u in users if u["id"] == target_user.id), None)
        
        # Gérer le profil LinkedIn
        if user_data and user_data.get("linkedin"):
            embed.add_field(
                name="💼 LinkedIn",
                value=f"[Profil LinkedIn]({user_data['linkedin']})",
                inline=False
            )
        
        # Gérer le profil Root-Me
        if user_data and user_data.get("rootme"):
            rootme_id = user_data.get("rootme")
        

        if rootme_id:
            try:
                # Configurer l'API Root-Me
                RootMe.setup()
                
                # Récupérer les informations d'utilisateur de l'API Root-Me
                rootme_data = await RootMe.get_author(str(rootme_id))
                
                # Extraire les informations
                nom = rootme_data.get("nom", rootme_id)
                score = rootme_data.get("score", "N/A")
                position = rootme_data.get("position", "N/A")
                
                # Ajouter les informations Root-Me à l'embed
                embed.add_field(
                    name="🛡️ Root-Me",
                    value=f"👤 Pseudo: {nom}\n"
                        f"🏆 Score: {score} points\n"
                        f"📈 Classement: #{position}\n"
                        f"🔗 [Voir le profil](https://www.root-me.org/{nom})",
                    inline=False
                )
                
                # Récupérer les défis récents
                recent_challenges = rootme_data.get("validations", [])
                
                if recent_challenges:
                    challenges_text = "\n".join([
                        f"• [{c.get('titre', 'Challenge')}](https://www.root-me.org/{c.get('titre', '').replace(' ', '-')}) (<t:{datetime.datetime.strptime(c.get('date', datetime.datetime.now()), '%Y-%m-%d %H:%M:%S').timestamp()}:F>)"
                        for c in recent_challenges[:10]
                    ])
                    
                    embed.add_field(
                        name="🚩 Challenges récents",
                        value=challenges_text or "Aucun défi récent trouvé.",
                        inline=False
                    )
            except Exception as e:
                embed.add_field(
                    name="❌ Erreur Root-Me",
                    value=f"Impossible de récupérer les données: {str(e)}",
                    inline=False
                )
        else:
            embed.add_field(
                name="🛡️ Root-Me",
                value=f"Profil non lié. Rendez vous dans le salon `{interaction.guild.get_channel(WELCOME_CHANNEL.id).mention}` pour lier votre compte.",
                inline=False
            )
        
        embed.set_footer(text=f"Demandé par {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)
    
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
