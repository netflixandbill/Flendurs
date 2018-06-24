import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks


class Pruner:
    """
    A cog to prune a server with 
    enough members to break the UI for doing it normally

    <3 Fortnite Pushing Discord's limits to be greater
    """

    __author__ = "mikeshardmind(Sinbad#0001)"
    __version__ = "0.0.1"

    def __init__(self, bot):
        self.bot = bot

    @checks.admin_or_permissions(manage_server=True)
    @commands.command(pass_context=True, no_pm=True)
    async def prune(self, ctx, days: int=14):
        """
        Prunes based on days, defaults to 14,
        will provide an estimate and confirmation
        """
        server_id = ctx.message.channel.server.id
        params = {'days': days}

        data = await self.bot.http.request(
            discord.http.Route(
                'GET', '/guilds/{guild_id}/prune',
                guild_id=server_id
            ),
            params=params
        )
        
        await self.bot.say(
            ("Discord shows an estimate of {} members pruned.\n"
            "to continue please respond with `Yes`").format(
                data['pruned']
            )
        )

        message = await self.bot.wait_for_message(
            channel=ctx.message.channel,
            author=ctx.message.author,
            timeout=45
        )

        if message is not None and message.content.lower() == 'yes':
            await self.bot.http.request(
                discord.http.Route(
                    'POST', '/guilds/{guild_id}/prune',
                    guild_id=server_id
                ), params=params
            )
            await self.bot.say("Prune running.")
        else:
            await self.bot.say("Ok, No pruning then.")


def setup(bot):
    bot.add_cog(Pruner(bot))
