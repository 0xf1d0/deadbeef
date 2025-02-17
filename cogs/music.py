import functools, os, asyncio, __main__

from discord import Interaction, app_commands
from discord.ext import commands, tasks

from utils import YTDLSource, restrict_channel


def ensure_voice(f):
    @functools.wraps(f)
    async def wrapper(self, ctx: Interaction, *args, **kwargs):
        vc = ctx.guild.voice_client
        if vc is None:
            voice = ctx.user.voice
            if voice:
                await voice.channel.connect()
                self.vc = ctx.guild.voice_client
            else:
                return await ctx.response.send_message("Tu dois être dans un salon vocal pour utiliser cette commande.")
        return await f(self, ctx, *args, **kwargs)
    return wrapper


class Music(commands.Cog):
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.vc = None
        self.check_voice_channel.start()
        self.queue = []

    @app_commands.command(description="Joue une vidéo depuis ton site préféré.")
    @app_commands.describe(query='La vidéo à jouer.', timestamp='Le moment de la vidéo où commencer à jouer.')
    @restrict_channel(1291397502842703955)
    @ensure_voice
    async def play(self, ctx: Interaction, query: str, timestamp: int = 0):
        async with ctx.channel.typing():
            await ctx.response.defer()
            self.queue.append((query, timestamp))
            if not self.vc.is_playing():
                await self.play_next(ctx)
            else:
                await ctx.followup.send(f"{query} a été ajouté à la file d'attente.")
    
    @app_commands.command(description='Sauter la vidéo actuelle.')
    @restrict_channel(1291397502842703955)
    @ensure_voice
    async def skip(self, ctx: Interaction):
        if self.vc and self.vc.is_playing():
            self.vc.stop()
            await ctx.response.send_message("La vidéo a été sautée.")
        else:
            await ctx.response.send_message("Je ne suis pas en train de jouer de musique.")
    
    @app_commands.command(description='Arrêter la lecture de la vidéo.')
    @restrict_channel(1291397502842703955)
    async def stop(self, ctx: Interaction):
        if self.vc:
            if ctx.user.voice:
                await self.vc.disconnect()
                await ctx.response.send_message("La lecture a été arrêtée.")
            else:
                await ctx.response.send_message("Tu dois être dans un salon vocal pour utiliser cette commande.")
        else:
            await ctx.response.send_message("Je ne suis pas connecté à un salon vocal.")

    async def play_next(self, ctx: Interaction):
        if self.queue:
            query, timestamp = self.queue.pop(0)
            try:
                player, filename = await YTDLSource.from_url(query, loop=self.bot.loop, timestamp=timestamp)
                self.vc.play(player, after=lambda e: self.bot.loop.create_task(self.cleanup(ctx, e, filename)))
                await ctx.followup.send(f"Lecture de {player.title}.")
            except Exception as e:
                await ctx.followup.send(f"Erreur lors de la lecture de la vidéo: {e}")

    async def cleanup(self, ctx: Interaction, error, path: str):
        if error:
            print(f'Player error: {error}')
        if path:
            try:
                await asyncio.sleep(1)
                dirname = os.path.dirname(__main__.__file__)
                os.remove(os.path.join(dirname, path))
            except OSError as e:
                print(f'Error deleting file: {e}')
        await self.play_next(ctx)

    @tasks.loop(minutes=1)
    async def check_voice_channel(self):
        if self.vc and self.vc.is_connected():
            if len(self.vc.channel.members) == 1:
                await asyncio.sleep(300)
                if len(self.vc.channel.members) == 1:
                    await self.vc.disconnect()

    @check_voice_channel.before_loop
    async def before_check_voice_channel(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
