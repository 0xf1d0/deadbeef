import datetime, re
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
                .set_thumbnail(url=member.display_avatar.url)\
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
                .set_thumbnail(url=member.display_avatar.url)\
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
            title=f"🔍 {target_user.display_name}",
            description=f"\u200b",
            color=Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # Ajouter les informations Discord
        member_since = target_user.joined_at or datetime.datetime.now()
        
        # Trouver les données utilisateur dans la configuration
        user_data = next((u for u in users if u["id"] == target_user.id), None)
        
        informations = f"\u200b\n🕒 A rejoint : <t:{int(member_since.timestamp())}:R>"
        
        if user_data:
            if "studentId" in user_data:
                informations += "\n\n🎓 Etudiant authentifié"
            elif "courses" in user_data:
                channels = []
                for c in user_data["courses"]:
                    if channel := interaction.guild.get_channel(c):
                        channels.append(channel.name)
                        
                informations += f"\n\n🧑‍🏫 Professionnel authentifié\n\n📚 Cours : {', '.join(channels)}"
        
        informations += "\n\u200b\n\u200b"

        embed.add_field(
            name="📊 __Informations__",
            value=informations
        )
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Gérer le profil LinkedIn
        if user_data and user_data.get("linkedin"):
            embed.add_field(
                name="💼 __LinkedIn__",
                value=f"\u200b\n[Voir le profil]({user_data['linkedin']})\n\u200b\n\u200b",
            )
        
        # Gérer le profil Root-Me
        rootme_id = None
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
                rank = rootme_data.get("rang", "N/A")
                
                # Ajouter les informations Root-Me à l'embed
                embed.add_field(
                    name="<:rootme:1366510489521356850> __Root-Me__",
                    value=f"\u200b\n🔗 [Voir le profil](https://www.root-me.org/{nom})\n\n"
                        f"👤 Pseudo : `{nom}`\n\n"
                        f"🏆 Score : **{score}** pts - {rank} - **#{position}**\n\u200b\n\u200b",
                    inline=False
                )
                
                challenges = rootme_data.get("validations", [])
                
                # Afficher les défis récents
                if challenges:
                    challenges_text = []
                    for c in challenges[:10]:
                        title = re.sub(r'&[^;]*;', '', c.get('titre', 'Challenge').strip())
                        challenge_url = re.sub(r'[\s-]+', '-', title)
                        challenges_text.append(f"- [{title}](https://www.root-me.org/{challenge_url}) <t:{int(datetime.datetime.strptime(c.get('date', datetime.datetime.now()), '%Y-%m-%d %H:%M:%S').timestamp())}:R>")
                    
                    embed.add_field(
                        name=f"🚩 __Challenges récents__ ({len(challenges)} validés)",
                        value="\u200b\n" + "\n".join(challenges_text) or "Aucun défi récent trouvé.",
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
                name="<:rootme:1366510489521356850> __Root-Me__",
                value=f"\u200b\nProfil non lié. Rendez vous dans le salon {interaction.guild.get_channel(WELCOME_CHANNEL.id).mention} pour lier votre compte.",
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
