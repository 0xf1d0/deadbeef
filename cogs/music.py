import functools, os, asyncio, __main__

from discord import Interaction, app_commands
from discord.ext import commands, tasks
from discord.app_commands.errors import CommandInvokeError

from utils import YTDLSource
from cogs.admin import restrict_channel


def ensure_voice(f):
    """
    @brief Decorator to ensure the bot is connected to a voice channel.
    This decorator checks if the bot is connected to a voice channel in the guild where the command is invoked.
    If the bot is not connected, it attempts to connect to the voice channel of the user who invoked the command.
    If the user is not in a voice channel, it sends a message indicating that the user must be in a voice channel to use the command.
    @param f The function to be decorated.
    @return The decorated function.
    """

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
    """
    @brief A Discord bot cog for managing music playback.
    This class provides commands to play, skip, and stop music in a voice channel.
    It also manages a queue of songs to be played and ensures the bot disconnects
    from the voice channel if no one else is present.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        @brief Initializes the Music cog.
        @param bot The instance of the bot.
        Initializes the Music cog with the given bot instance. Sets up the voice
        channel checker, initializes the voice client to None, and prepares an
        empty queue for music tracks.
        """

        self.bot = bot
        self.vc = None
        self.check_voice_channel.start()
        self.queue = []

    @app_commands.command(description="Joue une vidéo depuis ton site préféré.")
    @app_commands.describe(query='La vidéo à jouer.', timestamp='Le moment de la vidéo où commencer à jouer.')
    @restrict_channel(1291397502842703955)
    @ensure_voice
    async def play(self, ctx: Interaction, query: str, timestamp: int = 0):
        """
        @brief Plays a music track or adds it to the queue if another track is currently playing.
        @param ctx The interaction context.
        @param query The search query or URL of the music track.
        @param timestamp The starting timestamp of the track in seconds (default is 0).
        @return None
        """

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
        """
        @brief Skips the currently playing music track.
        @param ctx The interaction context.
        This function stops the currently playing music track if there is one,
        and sends a message indicating that the video has been skipped. If no
        music is playing, it sends a message indicating that no music is being played.
        """

        if self.vc and self.vc.is_playing():
            self.vc.stop()
            await ctx.response.send_message("La vidéo a été sautée.")
        else:
            await ctx.response.send_message("Je ne suis pas en train de jouer de musique.")
    
    
    @app_commands.command(description='Arrêter la lecture de la vidéo.')
    @restrict_channel(1291397502842703955)
    async def stop(self, ctx: Interaction):
        """
        @brief Stops the music playback and disconnects the bot from the voice channel.
        This command stops the music playback if the bot is connected to a voice channel and the user issuing the command is in a voice channel. 
        It sends a message indicating the result of the operation.
        @param ctx The interaction context containing information about the command invocation.
        @return None
        """

        if self.vc:
            if ctx.user.voice:
                await self.vc.disconnect()
                await ctx.response.send_message("La lecture a été arrêtée.")
            else:
                await ctx.response.send_message("Tu dois être dans un salon vocal pour utiliser cette commande.")
        else:
            await ctx.response.send_message("Je ne suis pas connecté à un salon vocal.")

    async def play_next(self, ctx: Interaction):
        """
        @brief Plays the next song in the queue.
        This asynchronous method checks if there are any songs in the queue. If there are, it pops the first song from the queue,
        attempts to create a player for the song using YTDLSource, and plays the song in the voice channel. If an error occurs
        during playback, it sends an error message to the context's follow-up.
        @param ctx The interaction context in which the command was invoked.
        @exception CommandInvokeError If an error occurs during the playback of the video.
        @note This method is intended to be used as part of a music bot cog for Discord.
        """
        
        if self.queue:
            query, timestamp = self.queue.pop(0)
            try:
                player, filename = await YTDLSource.from_url(query, loop=self.bot.loop, timestamp=timestamp)

                self.vc.play(player, after=lambda e: self.bot.loop.create_task(self.cleanup(ctx, e, filename)))
                await ctx.followup.send(f"Lecture de {player.title}.")
            except CommandInvokeError as e:
                await ctx.followup.send(f"Erreur lors de la lecture de la vidéo: {e}")

    async def cleanup(self, ctx: Interaction, error, path: str):
        """
        @brief Cleans up resources after a music track has finished playing.
        This function handles errors that occur during playback and removes the specified file from the filesystem.
        It also triggers the playback of the next track in the queue.
        @param ctx The interaction context.
        @param error The error that occurred during playback, if any.
        @param path The path to the file that needs to be deleted.
        """

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
        """
        @brief Checks the voice channel for inactivity and disconnects the bot if it is alone.
        This asynchronous function checks if the bot is connected to a voice channel and if it is the only member in the channel.
        If the bot is alone in the voice channel, it waits for 5 minutes and checks again. If the bot is still alone after the wait,
        it disconnects from the voice channel.
        @return None
        """

        if self.vc and self.vc.is_connected():
            if len(self.vc.channel.members) == 1:
                await asyncio.sleep(300)  # Wait for 5 minutes
                if len(self.vc.channel.members) == 1:  # Check again if only the bot is in the channel
                    await self.vc.disconnect()

    @check_voice_channel.before_loop
    async def before_check_voice_channel(self):
        """
        @brief Waits until the bot is ready before performing any voice channel checks.
        This asynchronous method ensures that the bot is fully initialized and ready 
        before proceeding with any operations related to voice channels.
        @return None
        """

        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    """
    @brief Asynchronous function to set up the Music cog.
    This function adds the Music cog to the provided bot instance.
    @param bot The instance of the bot to which the Music cog will be added.
    """

    await bot.add_cog(Music(bot))
