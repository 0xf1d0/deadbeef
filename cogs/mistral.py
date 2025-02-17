from collections import defaultdict

from discord.ext import commands
from discord import Message, NotFound

import aiohttp, re


async def send_long_reply(message, content):
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
    
    for part in parts:
        await message.reply(part)


class Mistral(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conversations = defaultdict(dict)

    async def answer(self, message: Message, conversation):
        async with message.channel.typing():
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.mistral.ai/v1/chat/completions',
                    headers={
                        "Authorization": f"Bearer {self.bot.config.get('mistral_key')}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "codestral-latest",
                        "messages": conversation
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        r = data['choices'][0]['message']['content']
                        r = re.sub(r'<\@\&?\d+>|@everyone|@here', 'X', r)
                        
                        conversation.append({
                            'role': 'assistant',
                            'content': r
                        })
                        await send_long_reply(message, r)
                    elif response.status == 422:
                        await message.reply(data['detail'][-1]['msg'])
                    else:
                        await message.reply("Sorry, I couldn't generate a response at this time.")

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
                        'content': re.sub(r'<\@1291395104023773225>|deadbeef', '', message.content)
                    })
                    
                    if len(conversation) > 10:
                        conversation = conversation[-10:]
                    
                    await self.answer(message, conversation)
                    return
            except NotFound:
                pass

        # New Conversation
        msg = message.content.lower()
        if 'deadbeef' in msg or f'<@{self.bot.user.id}>' in msg:
            conversation = [{
                'role': 'user',
                'content': re.sub(r'<\@1291395104023773225>|deadbeef', '', msg)
            }]
            self.conversations[channel_id] = conversation
            await self.answer(message, conversation)

        await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(Mistral(bot))
