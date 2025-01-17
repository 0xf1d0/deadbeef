from discord import Embed, Colour
from discord.ext import commands, tasks
import feedparser


class News(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = 1329861281427095582
        self.latest_entry = None
        self.news_update.start()

    @tasks.loop(seconds=10)
    async def news_update(self):
        feed = feedparser.parse('https://www.cert.ssi.gouv.fr/feed/')
        if not feed.entries:
            return

        latest = feed.entries[0]
        if self.latest_entry is None or latest.link != self.latest_entry:
            self.latest_entry = latest.link
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                embed = Embed(
                    title=latest.title,
                    description=latest.summary,
                    url=latest.link,
                    color=Colour.blue()
                )
                await channel.send(embed=embed)

    @news_update.before_loop
    async def before_news_update(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(News(bot))