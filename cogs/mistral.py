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
        self.conversations = defaultdict(dict)
        self.mistral = MistralAI()

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        
        channel_id = message.channel.id
        if message.reference and message.reference.message_id:
            try:
                replied_message = await message.channel.fetch_message(message.reference.message_id)

                if replied_message.author == self.bot.user:
                    conversation = self.conversations[channel_id]
                    conversation.append({
                        'role': 'user',
                        'content': re.sub(r'<@1291395104023773225>|deadbeef', '', message.content)
                    })
                    
                    if len(conversation) > 10:
                        conversation = conversation[-10:]
                    async with message.channel.typing():
                        try:
                            async with self.mistral:
                                answer = await self.mistral.ask(messages=conversation, model='codestral-latest')
                                conversation.append({
                                    'role': 'assistant',
                                    'content': answer
                                })
                                for part in divide_msg(answer):
                                    await message.reply(part)
                        except Exception as e:
                            await message.reply(str(e))
                    return
            except NotFound:
                pass

        # New Conversation
        msg = message.content.lower()
        if 'deadbeef' in msg or f'<@{self.bot.user.id}>' in msg or channel_id not in self.conversations:
            conversation = [{
                'role': 'user',
                'content': re.sub(r'<@1291395104023773225>|deadbeef', '', msg)
            }]
            self.conversations[channel_id] = conversation
            
            async with message.channel.typing():
                try:
                    async with self.mistral:
                        answer = await self.mistral.ask(messages=conversation, model='codestral-latest')
                        conversation.append({
                            'role': 'assistant',
                            'content': answer
                        })
                        for part in divide_msg(answer):
                            await message.reply(part)
                except Exception as e:
                    await message.reply(str(e))

        await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(Mistral(bot))
