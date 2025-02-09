from discord import Embed, Colour
from discord.ext import commands, tasks

import feedparser


class News(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = 1329861281427095582
        self.sent_entries = bot.config.get('feeds', [])
        self.feeds = [
            'https://www.cert.ssi.gouv.fr/feed/',
            'https://www.zataz.com/feed/',
            'https://www.clusif.fr/feed/'
        ]
        self.news_update.start()

    @tasks.loop(minutes=30)
    async def news_update(self):
        new_entries = []
        for feed_url in self.feeds:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue

            for entry in feed.entries:
                if entry.id not in self.sent_entries:
                    new_entries.append(entry)
                    self.sent_entries.add(entry.id)

        if new_entries:
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                for entry in new_entries:
                    embed = Embed(
                        title=entry.title,
                        description=entry.summary,
                        url=entry.link,
                        color=Colour.blue()
                    )
                    embed.set_footer(text=f"Source: {feedparser.parse(entry.link).feed.title}")
                    embed.set_author(name=entry.author if 'author' in entry else "Unknown Author")
                    embed.add_field(name="Published", value=entry.published if 'published' in entry else "Unknown Date", inline=False)
                    embed.add_field(name="Categories", value=", ".join(entry.tags) if 'tags' in entry else "No categories", inline=False)

                    await channel.send(embed=embed)

            # Update the configuration file with the new set of sent entries
            self.bot.config.set('feeds', list(self.sent_entries))

    @news_update.before_loop
    async def before_news_update(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(News(bot))
