import datetime
import re
import logging
from typing import Optional
from discord import app_commands, Interaction, Member, Embed, File, Color, Activity, ActivityType
from discord.ext import tasks
from discord.ext import commands
from sqlalchemy import select

from utils import ConfigManager, WELCOME_MESSAGE, WELCOME_CHANNEL, LOG_CHANNEL, CYBER_COLOR, CYBER, ROLE_MANAGER, ROLE_NOTABLE
from ui.auth import Authentication
from ui.announce import Announcement
from db import AsyncSessionLocal
from db.models import AuthenticatedUser, Professional

from api import RootMe

logger = logging.getLogger(__name__)


class Common(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_status.start()
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize welcome message on bot ready."""
        try:
            guild = self.bot.get_guild(CYBER.id)
            if not guild:
                logger.error(f"Guild {CYBER.id} not found")
                return
            
            welcome = guild.get_channel(WELCOME_CHANNEL.id)
            if not welcome:
                logger.error(f"Welcome channel {WELCOME_CHANNEL.id} not found")
                return
            
            welcome_message = await welcome.fetch_message(WELCOME_MESSAGE.id)
            await welcome_message.edit(
                content=ConfigManager.get('welcome_message'),
                view=Authentication()
            )
            logger.info("Welcome message initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize welcome message: {e}", exc_info=True)
        
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

        # Count non-bot members efficiently
        member_count = sum(1 for member in guild.members if not member.bot)
        
        embed = Embed(title=f'{guild.name}', description=f'Scannez ce QR Code pour rejoindre la communauté {guild.name}. 🚀', color=CYBER_COLOR)\
            .set_image(url='attachment://invite.png')\
            .set_footer(text=f'{guild.name} - {member_count} membres', icon_url=guild.icon.url)
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

    @app_commands.command(name="ping", description="Afficher la latence du bot.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ping(self, interaction: Interaction):
        """Check the bot's latency."""
        await interaction.response.send_message(f"🏓 Pong ! ({round(self.bot.latency * 1000)} ms)")
   
    @app_commands.command(description="Annoncer un message.")
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def announce(self, interaction: Interaction):
        modal = Announcement()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(description="Efface un nombre de messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: Interaction, limit: int):
        await interaction.response.send_message(f'{limit} messages ont été effacés.', ephemeral=True)
        await interaction.channel.purge(limit=limit)
    
    @app_commands.command(description="Rafraîchir le cache RootMe d'un utilisateur.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Le membre dont vous souhaitez rafraîchir le cache RootMe")
    async def refresh_rootme_cache(self, interaction: Interaction, member: Optional[Member] = None):
        """Refresh RootMe cache for a specific user."""
        target_user = member or interaction.user
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            from utils.rootme_cache import RootMeCacheManager
            
            # Force refresh the cache
            success = await RootMeCacheManager.refresh_user_cache(target_user.id)
            
            if success:
                await interaction.followup.send(
                    f"✅ Cache RootMe rafraîchi avec succès pour {target_user.mention}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Impossible de rafraîchir le cache RootMe pour {target_user.mention}",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erreur lors du rafraîchissement du cache: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(description="Afficher son profil ou celui d'un autre utilisateur.")
    @app_commands.describe(member="Le membre dont vous souhaitez voir le profil")
    async def profile(self, interaction: Interaction, member: Optional[Member] = None):
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
        
        # Récupérer les données utilisateur depuis la base de données
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == target_user.id)
            )
            user_data = result.scalar_one_or_none()
            
            informations = f"\u200b\n🕒 A rejoint : <t:{int(member_since.timestamp())}:R>"
            
            if user_data:
                if user_data.user_type == 'student':
                    informations += f"\n\n🎓 Etudiant authentifié <:upc_black:1367296895717736553>"
                    informations += f"\n📚 {user_data.grade_level} - {user_data.formation_type}"
                elif user_data.user_type == 'professional':
                    # Get professional's courses
                    result = await session.execute(
                        select(Professional).where(Professional.email == user_data.email)
                    )
                    pro = result.scalar_one_or_none()
                    
                    if pro:
                        channels = []
                        for cc in pro.course_channels:
                            if channel := interaction.guild.get_channel(cc.channel_id):
                                channels.append(channel.name)
                        
                        informations += f"\n\n🧑‍🏫 Professionnel authentifié <:upc_black:1367296895717736553>"
                        if channels:
                            courses_text = ', '.join(channels)
                            # Ensure embed field value stays <= 1024 chars
                            if len(courses_text) > 950:
                                # Truncate safely and indicate there are more
                                remaining = len(courses_text) - 950
                                courses_text = courses_text[:950].rstrip() + f"… (+{remaining} chars)"
                            informations += f"\n\n📚 Cours : {courses_text}"
            
            informations += "\n\u200b\n\u200b"

            embed.add_field(
                name="📊 __Informations__",
                value=informations
            )
            
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Gérer le profil LinkedIn
            if user_data and user_data.linkedin_url:
                embed.add_field(
                    name="💼 __LinkedIn__",
                    value=f"\u200b\n[Voir le profil]({user_data.linkedin_url})\n\u200b\n\u200b",
                )
            
            # Gérer le profil Root-Me avec cache
            if user_data and user_data.rootme_id:
                try:
                    from utils.rootme_cache import RootMeCacheManager
                    
                    # Récupérer les stats avec cache
                    stats = await RootMeCacheManager.get_user_stats(target_user.id)
                    
                    if stats:
                        # Ajouter les informations Root-Me à l'embed
                        cache_indicator = " (cached)" if stats.get('cached') else ""
                        embed.add_field(
                            name=f"<:rootme:1366510489521356850> __Root-Me__{cache_indicator}",
                            value=f"\u200b\n🔗 [Voir le profil](https://www.root-me.org/{stats['pseudo']})\n\n"
                                f"👤 Pseudo : `{stats['pseudo']}`\n\n"
                                f"🏆 Score : **{stats['score']:,}** pts - {stats['rank']} - **#{stats['position']}**\n\u200b\n\u200b",
                            inline=False
                        )
                        
                        # Pour les challenges récents, on doit encore faire un appel API
                        # mais seulement si on n'a pas de cache ou si on force le refresh
                        if not stats.get('cached') or stats.get('api_error'):
                            try:
                                RootMe.setup()
                                rootme_data = await RootMe.get_author(str(user_data.rootme_id))
                                challenges = rootme_data.get("validations", [])
                                
                                if challenges:
                                    lines = []
                                    current_len = len("\u200b\n")
                                    # Add up to 10 items but stop earlier if would exceed 1024
                                    for c in challenges[:10]:
                                        title = re.sub(r'&[^;]*;', '', c.get('titre', 'Challenge').strip())
                                        challenge_url = re.sub(r'[\s-]+', '-', title)
                                        # Safely parse date
                                        date_str = c.get('date', '')
                                        if date_str and isinstance(date_str, str):
                                            try:
                                                challenge_dt = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                                                timestamp = int(challenge_dt.timestamp())
                                            except (ValueError, TypeError):
                                                timestamp = int(datetime.datetime.now().timestamp())
                                        else:
                                            timestamp = int(datetime.datetime.now().timestamp())
                                        line = f"- [{title}](https://www.root-me.org/{challenge_url}) <t:{timestamp}:R>"
                                        if current_len + len(line) + 1 > 1000:  # keep margin for safety
                                            # Indicate there are more items not shown
                                            lines.append("…")
                                            break
                                        lines.append(line)
                                        current_len += len(line) + 1
                                    value_text = "\u200b\n" + ("\n".join(lines) if lines else "Aucun défi récent trouvé.")
                                    embed.add_field(
                                        name=f"🚩 __Challenges récents__ ({len(challenges)} validés)",
                                        value=value_text,
                                        inline=False
                                    )
                            except Exception as e:
                                embed.add_field(
                                    name="🚩 __Challenges récents__",
                                    value=f"Impossible de récupérer les challenges: {str(e)[:200]}...",
                                    inline=False
                                )
                        else:
                            # Si on a du cache, on affiche juste le nombre de challenges
                            embed.add_field(
                                name=f"🚩 __Challenges récents__ ({stats['challenge_count']} validés)",
                                value="\u200b\n",
                                inline=False
                            )
                    else:
                        embed.add_field(
                            name="<:rootme:1366510489521356850> __Root-Me__",
                            value=f"\u200b\nProfil non lié. Rendez vous dans le salon {interaction.guild.get_channel(WELCOME_CHANNEL.id).mention} pour lier votre compte.",
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
            # Count non-bot members efficiently
            member_count = sum(1 for member in guild.members if not member.bot)
            await self.bot.change_presence(
                activity=Activity(
                    type=ActivityType.watching,
                    name=f"{member_count} members"
                )
            )
    
    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Common(bot))
