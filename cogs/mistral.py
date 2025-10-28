from collections import defaultdict

from discord.ext import commands
from discord import Message, NotFound

import re

from api import MistralAI


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
        # Conversations are tracked per user to give each user their own context
        # Values are lists of {role, content}
        self.conversations = defaultdict(list)
        # Keep a rolling window of messages to bound context size
        self.MAX_HISTORY_MESSAGES = 20  # ~10 exchanges
        # Hard reset threshold if a thread grows unusually long
        self.RESET_THRESHOLD = 60  # messages

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        
        channel_id = message.channel.id
        user_id = message.author.id
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
            # Append to this user's conversation
            self.conversations[user_id].append(new)
            conversation = self.conversations[user_id]
            
            # Trim to rolling window
            if len(conversation) > self.MAX_HISTORY_MESSAGES:
                conversation = conversation[-self.MAX_HISTORY_MESSAGES:]
                self.conversations[user_id] = conversation

            # Hard reset if threshold exceeded (safety)
            if len(conversation) >= self.RESET_THRESHOLD:
                self.conversations[user_id] = conversation[-self.MAX_HISTORY_MESSAGES:]
                try:
                    await message.channel.send("♻️ Conversation context was getting long; I trimmed it to keep responses sharp.")
                except Exception:
                    pass
            async with message.channel.typing():
                try:
                    # Pass messages in JSON body for POST request
                    answer = await MistralAI.chat_completion(
                        json={
                            'messages': conversation,
                            'model': 'devstral-small-2507'
                        }
                    )
                    conversation.append({
                        'role': 'assistant',
                        'content': answer
                    })
                    # Persist trimmed history
                    if len(conversation) > self.MAX_HISTORY_MESSAGES:
                        self.conversations[user_id] = conversation[-self.MAX_HISTORY_MESSAGES:]
                        conversation = self.conversations[user_id]
                    else:
                        self.conversations[user_id] = conversation

                    for part in divide_msg(answer):
                        await message.reply(part)
                except Exception as e:
                    await message.reply(str(e))
            return

        await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(Mistral(bot))
