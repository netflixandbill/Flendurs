from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import dataIO
# noinspection PyUnresolvedReferences
from __main__ import send_cmd_help
import discord
import asyncio


class ModLog:
    def __init__(self, bot):
        self.bot = bot
        try:
            self.db = dataIO.load_json('data/mod_log.json')
        except FileNotFoundError:
            self.db = {}
        self.loop = self.bot.loop.create_task(self.mod_loop())

    def __unload(self):
        self.loop.cancel()

    def _save(self):
        dataIO.save_json('data/mod_log.json', self.db)

    async def _new_case(self, server, user, action):
        if self.db[server.id]['channel'] is not None:
            channel_id = self.db[server.id]['channel']
            case_num = str(len(self.db[server.id]['cases']) + 1)
            template = '**{0}** | Case {1}\n' \
                       '**User:** {2}\n' \
                       '**Reason:** Responsible moderator, please do `[p]reason {1} <reason>`' \
                       .format(action, case_num, user)
            message = await self.bot.send_message(server.get_channel(channel_id), template)
            self.db[server.id]['cases'][case_num] = {
                'action': action,
                'user_id': user.id,
                'reason': None,
                'moderator_id': None,
                'case_message_id': message.id
            }
            self._save()

    async def _update_case(self, server, case_num, reason, moderator):
        if case_num not in self.db[server.id]['cases']:
            raise IndexError('Not a valid case number')
        case = self.db[server.id]['cases'][case_num]
        channel = self.bot.get_channel(self.db[server.id]['channel'])
        user = await self.bot.get_user_info(case['user_id'])
        message = await self.bot.get_message(channel, case['case_message_id'])
        template = '**{0}** | Case {1}\n' \
                   '**User:** {2}\n' \
                   '**Reason:** {3}\n' \
                   '**Responsible Moderator:** {4}' \
                   .format(case['action'], case_num, user, reason, moderator)
        new_message = await self.bot.edit_message(message, template)
        self.db[server.id]['cases'][case_num] = {
            'action': case['action'],
            'user_id': case['user_id'],
            'reason': reason,
            'moderator_id': moderator.id,
            'case_message_id': new_message.id
        }
        self._save()

    async def mod_loop(self):
        while True:
            changes = False  # determines if there were changes

            for server in self.bot.servers:
                if server.id not in self.db:
                    self.db[server.id] = {}
                    changes = True
                if 'channel' not in self.db[server.id]:
                    self.db[server.id]['channel'] = None
                    changes = True
                if 'cases' not in self.db[server.id]:
                    self.db[server.id]['cases'] = {}
                    changes = True

            if changes:
                self._save()

            await asyncio.sleep(5)

    @checks.admin_or_permissions(manage_server=True)
    @commands.group(pass_context=True, name='ml', invoke_without_command=True)
    async def ml_cmd(self, ctx):
        """Mod log command"""
        await send_cmd_help(ctx)

    @checks.admin_or_permissions(manage_server=True)
    @ml_cmd.command(pass_context=True)
    async def register(self, ctx, mod_log_channel: discord.Channel):
        """Registers the moderation log channel."""
        self.db[ctx.message.server.id]['channel'] = mod_log_channel.id
        self._save()
        await self.bot.say('Server registered.')

    @checks.admin_or_permissions(manage_server=True)
    @ml_cmd.command(pass_context=True)
    async def unregister(self, ctx):
        """Unregisters the server."""
        self.db[ctx.message.server.id]['channel'] = None
        self._save()
        await self.bot.say('Server unregistered.')

    @checks.mod_or_permissions(ban_members=True)
    @commands.command(pass_context=True, name='reason')
    async def reason_cmd(self, ctx, case_num: int, *, reason: str):
        server = ctx.message.server
        moderator = ctx.message.author
        case_num = str(case_num)
        if case_num not in self.db[server.id]['cases']:
            await self.bot.say('That\'s not a valid case number.')
            return
        await self._update_case(server, case_num, reason, moderator)
        await self.bot.say('Case updated')

    async def on_member_ban(self, member):
        await self._new_case(member.server, member, 'Ban')

    async def on_member_unban(self, server, user):
        await self._new_case(server, user, 'Unban')


def setup(bot):
    bot.add_cog(ModLog(bot))
