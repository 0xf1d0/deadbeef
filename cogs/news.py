from discord import Embed, Color
from discord.ext import commands, tasks
from discord import app_commands, Interaction
from datetime import datetime
from sqlalchemy import select
import feedparser
import re

from db import AsyncSessionLocal, init_db
from db.models import NewsChannel, SentNewsEntry
from ui.news import NewsManagementView
from utils.utils import ROLE_NOTABLE, ROLE_MANAGER


def clean_html(raw_html: str) -> str:
    """Remove HTML tags from a string."""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()


def format_date(date_str: str) -> str:
    """Format the publication date nicely."""
    try:
        date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        return date.strftime('%d/%m/%Y à %H:%M')
    except:
        return date_str


def parse_color(color_str: str) -> Color:
    """Parse color string to Discord Color."""
    if not color_str:
        return Color.default()
    
    try:
        # Remove # if present
        color_str = color_str.strip()
        if color_str.startswith('#'):
            color_str = color_str[1:]
        
        # Convert hex to int
        color_int = int(color_str, 16)
        return Color(color_int)
    except:
        return Color.default()


def create_news_embed(entry: dict, feed_name: str, feed_color: str) -> Embed:
    """Create a rich embed for the news entry."""
    # Clean and truncate description
    description = clean_html(entry.get('description', entry.get('summary', '')))
    if len(description) > 1000:
        description = description[:997] + '...'
    
    # Parse color
    color = parse_color(feed_color)
    
    # Create embed
    embed = Embed(
        title=entry.get('title', 'Sans titre'),
        url=entry.get('link', ''),
        description=description,
        color=color
    )
    
    # Add metadata fields
    embed.add_field(
        name="Source",
        value=f":shield: {feed_name}",
        inline=True
    )
    
    # Try different date fields
    pub_date = entry.get('published', entry.get('pubDate', entry.get('updated', '')))
    if pub_date:
        embed.add_field(
            name="Date de publication",
            value=f":calendar: {format_date(pub_date)}",
            inline=True
        )
    
    if 'author' in entry and entry.get('author'):
        embed.add_field(
            name="Auteur",
            value=f":pencil: {entry.get('author')}",
            inline=True
        )
    
    # Handle categories/tags
    categories = entry.get('tags', [])
    if categories:
        cat_names = [tag.get('term', str(tag)) for tag in categories[:5]]
        if cat_names:
            embed.add_field(
                name="Catégories",
                value=f":label: {', '.join(cat_names)}",
                inline=False
            )
    
    # Add footer with entry ID for tracking
    entry_id = entry.get('id', entry.get('guid', entry.get('link', 'Unknown')))
    embed.set_footer(text=f"ID: {entry_id[:50]}")
    
    return embed


class News(commands.Cog):
    """Cog for managing RSS/Atom news feeds."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.news_update.start()
    
    async def cog_load(self):
        """Initialize database when cog loads."""
        await init_db()
    
    def cog_unload(self):
        """Stop the update task when cog unloads."""
        self.news_update.cancel()
    
    @app_commands.command(
        name="manage_news",
        description="Manage news feeds and channels (Admin/Manager only)."
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def manage_news(self, interaction: Interaction):
        """Open news management panel."""
        view = NewsManagementView()
        embed = Embed(
            title="📰 News Management",
            description="Configure and manage RSS/Atom news feeds for this channel.",
            color=Color.blue()
        )
        embed.add_field(
            name="Available Actions",
            value="• **Setup Channel** - Configure this channel for news feeds\n"
                  "• **Add Feed** - Add a new RSS/Atom feed\n"
                  "• **Manage Feeds** - Edit, toggle, or delete existing feeds\n"
                  "• **View Status** - See channel and feed statistics\n"
                  "• **Delete Channel** - Remove news configuration from this channel",
            inline=False
        )
        embed.add_field(
            name="Popular Feeds",
            value="• CERT-FR: `https://www.cert.ssi.gouv.fr/feed/`\n"
                  "• ZATAZ: `https://www.zataz.com/feed/`\n"
                  "• CLUSIF: `https://www.clusif.fr/feed/`\n"
                  "• Bleeping Computer: `https://www.bleepingcomputer.com/feed/`\n"
                  "• The Hacker News: `https://feeds.feedburner.com/TheHackersNews`",
            inline=False
        )
        embed.set_footer(text="News feeds check for updates every 30 minutes")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @tasks.loop(minutes=30)
    async def news_update(self):
        """Fetch and post new entries from all configured feeds."""
        async with AsyncSessionLocal() as session:
            # Get all active news channels
            result = await session.execute(
                select(NewsChannel).where(NewsChannel.is_active == True)
            )
            news_channels = result.scalars().all()
            
            for news_channel in news_channels:
                channel = self.bot.get_channel(news_channel.channel_id)
                if not channel:
                    continue
                
                # Process each active feed for this channel
                for feed_config in news_channel.feeds:
                    if not feed_config.is_active:
                        continue
                    
                    try:
                        # Fetch feed
                        feed = feedparser.parse(feed_config.url)
                        
                        if not feed.entries:
                            continue
                        
                        # Check for new entries
                        new_entries = []
                        for entry in feed.entries:
                            # Get entry ID (try multiple fields)
                            entry_id = entry.get('id', entry.get('guid', entry.get('link', '')))
                            
                            if not entry_id:
                                continue
                            
                            # Check if already sent
                            result = await session.execute(
                                select(SentNewsEntry).where(
                                    SentNewsEntry.feed_id == feed_config.id,
                                    SentNewsEntry.entry_id == entry_id
                                )
                            )
                            existing = result.scalar_one_or_none()
                            
                            if not existing:
                                new_entries.append((entry, entry_id))
                        
                        # Send new entries
                        for entry, entry_id in new_entries:
                            try:
                                embed = create_news_embed(
                                    entry,
                                    feed_config.name,
                                    feed_config.color
                                )
                                await channel.send(embed=embed)
                                
                                # Record as sent
                                sent_entry = SentNewsEntry(
                                    feed_id=feed_config.id,
                                    entry_id=entry_id,
                                    sent_at=datetime.now()
                                )
                                session.add(sent_entry)
                            
                            except Exception as e:
                                print(f"Error sending news entry: {e}")
                        
                        # Commit after each feed
                        await session.commit()
                    
                    except Exception as e:
                        print(f"Error processing feed {feed_config.name}: {e}")
    
    @news_update.before_loop
    async def before_news_update(self):
        """Wait until the bot is ready before starting the update task."""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(News(bot))
