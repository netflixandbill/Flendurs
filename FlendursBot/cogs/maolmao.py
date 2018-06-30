import discord
from __main__ import settings


class Maolmao:
    def __init__(self, bot):
        self.bot = bot
        self.image = 'data/maolmao/crikayy.png'
        self.owner = '<!{}>'.format(settings.owner)

    async def listener(self, message):
        channel = message.channel
        if message.author.id != self.bot.user.id:
            if message.content.lower().startswith('ayyy') or message.content.lower().startswith('aayy'):
                try:
                    await self.bot.send_file(channel, self.image)
                except discord.Forbidden:
                    await self.bot.send_message(message.channel, 'lmao')


def setup(bot):
    n = Maolmao(bot)
    bot.add_listener(n.listener, "on_message")
    bot.add_cog(n)
