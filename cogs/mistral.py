from collections import defaultdict

from discord.ext import commands
from discord import Message, NotFound

import re

from api.api import MistralAI


def divide_msg(content):
        parts = []
        while len(content) > 2000:
            split_index = content.rfind('.', 0, 2000)
            if split_index == -1:
                split_index = content.rfind(' ', 0, 2000)
            if split_index == -1:
                split_index = 2000
            parts.append(content[:split_index + 1])
            content = content[split_index + 1:]
        parts.append(content)
        
        return parts


class Mistral(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conversations = defaultdict(list)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        
        channel_id = message.channel.id
        ref = message.reference
        replied_message = None
        if ref and ref.message_id:
            try:
                replied_message = await message.channel.fetch_message(ref.message_id)
            except NotFound:
                pass

        msg = message.content.lower()
        if replied_message and replied_message.author == self.bot.user or 'deadbeef' in msg or f'<@{self.bot.user.id}>' in msg:
            new = {
                'role': 'user',
                'content': re.sub(rf'<@{self.bot.user.id}>|deadbeef', '', message.content, flags=re.IGNORECASE)
            }
            if channel_id in self.conversations:
                self.conversations[channel_id].append(new)
            else:
                self.conversations[channel_id] = [new]
            
            conversation = self.conversations[channel_id]
            
            if len(conversation) > 10:
                conversation = conversation[-10:]
            async with message.channel.typing():
                try:
                    answer = await MistralAI.chat_completion(messages=conversation, model='codestral-latest')
                    conversation.append({
                        'role': 'assistant',
                        'content': answer
                    })
                    for part in divide_msg(answer):
                        await message.reply(part)
                except Exception as e:
                    await message.reply(str(e))
            return

        await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(Mistral(bot))
