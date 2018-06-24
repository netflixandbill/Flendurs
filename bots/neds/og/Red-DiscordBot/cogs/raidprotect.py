import discord
from discord.ext import commands
from .utils import checks
from cogs.utils.dataIO import dataIO
import os
import asyncio
from __main__ import settings

__author__ = "dimxxz - https://github.com/dimxxz/dimxxz-Cogs"
__original__ = "PlanetTeamSpeak / PTSCogs - https://github.com/PlanetTeamSpeakk/PTSCogs"
__version__ = '2.0'
__additional__ = "Parts forked from xorole.py written by Caleb Johnson <me@calebj.io> (calebj#7377)"

class XORoleException(Exception):
    pass

class RolesetAlreadyExists(XORoleException):
    pass

class RolesetNotFound(XORoleException):
    pass

class NoRolesetsFound(XORoleException):
    pass

class RoleNotFound(XORoleException):
    pass

class PermissionsError(XORoleException):
    pass

class RaidProtect:
    """Protect yourself from server raids."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/raidprotect/settings.json")

    def get_settings(self, server):
        sid = server.id
        return self.settings.get(sid, {})

    def get_rolesets(self, server):
        return self.get_settings(server).get('ROLESETS', {})

    def get_roleset(self, server, name, notfound_ok=False):
        current = self.get_rolesets(server)
        if name in current:
            return name, current[name]

        searchname = name.lower().strip()
        for k, v in current.items():
            if k.lower().strip() == searchname:
                return k, v

        if not notfound_ok:
            raise RolesetNotFound("Roleset '%s' does not exist." % name)

    def roleset_of_role(self, role, notfound_ok=False):
        rid = role.id
        for rsn, rsl in self.get_rolesets(role.server).items():
            if rid in rsl:
                return rsn
        if not notfound_ok:
            raise NoRolesetsFound("The '%s' role doesn't belong to any "
                                  "rolesets" % role.name)

    def get_roleset_memberships(self, member, roleset):
        rsn, rsl = self.get_roleset(member.server, roleset)

        rslset = set(rsl)
        current_roles = []

        for role in member.roles:
            if role.id in rslset:
                current_roles.append(role)

        return current_roles

    @staticmethod
    def find_role(server, query, notfound_ok=False):
        stripped = query.strip().lower()

        for role in server.roles:
            if role.name.strip().lower() == stripped:  # Ignore case and spaces
                return role
            elif role.id == stripped:  # also work with role IDs
                return role

        if not notfound_ok:
            raise RoleNotFound("Could not find role '%s'." % query)

    @classmethod
    def find_roles(cls, server, *queries):
        found = []
        notfound = []

        for q in queries:
            role = cls.find_role(server, q, notfound_ok=True)
            if role:
                found.append(role)
            else:
                notfound.append(q)

        return found, notfound


    async def _auto_give(self, member):
        server = member.server
        try:
            roleid = "raid"
            roles = server.roles
        except KeyError:
            return
        except AttributeError:
            print("This server has no roles... what even?\n")
            return
        role = discord.utils.get(roles, name=roleid)
        try:
            await self.bot.add_roles(member, role)
        except discord.Forbidden:
            if server.id in self.settings:
                await self._no_perms(server)


    @commands.group(pass_context=True)
    async def raidprotect(self, ctx):
        """Manage Raid-protect v2.0."""
        if not ctx.invoked_subcommand:
            await self.bot.send_cmd_help(ctx)
        if not ctx.message.server.id in self.settings:
            self.settings[ctx.message.server.id] = {'joined': 0, 'channel': None, 'members': 4, 'protected': False}
            self.save_settings()
            
    @raidprotect.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def setup(self, ctx):
        """Setup the channel and role for raid-protect v2.0"""
        server = ctx.message.server
        chrolename = "raid"
        try:
            role = self.find_role(server, chrolename)
            if role.name == chrolename:
                e = discord.Embed(title="Anti-Raid", description="Raid-protection is already set up. If you removed the"
                                                                 " channel and want to set Raid-protection up again, "
                                                                 "please remove the role **raid** in the Server Settings first!",
                                  colour=discord.Colour.red())
                await self.bot.say(embed=e)
                return
        except:
            covrole = await self.bot.create_role(server, name=chrolename)
            admin_role = discord.utils.get(server.roles, name=settings.get_server_admin(server))
            everyone_perms = discord.PermissionOverwrite(read_messages=False)
            insilenced_perms = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            mod_admin_perms = discord.PermissionOverwrite(read_messages=True, send_messages=True,
                                                          manage_channel=True)
            chn = await self.bot.create_channel(
                server, chrolename,
                (server.default_role, everyone_perms),
                (covrole, insilenced_perms),
                (admin_role, mod_admin_perms))

            for role in ctx.message.server.roles:
                if "raid" in role.name:
                    for channelx in ctx.message.server.channels:
                        if "raid" in channelx.name:
                            for c in ctx.message.server.channels:
                                if c.name != chn.name:
                                    try:
                                        await self.bot.edit_channel_permissions(c, covrole, everyone_perms)
                                    except discord.errors.Forbidden:
                                        pass
            e = discord.Embed(title="Anti-Raid", description="Raid-protection has been set up!",
                              colour=discord.Colour.red())
            await self.bot.send_message(chn, embed=e)

            await asyncio.sleep(1)
            for c in server.channels:
                if c.name != chn.name:
                    try:
                        await self.bot.edit_channel_permissions(c, covrole, everyone_perms)
                    except discord.errors.Forbidden:
                        pass
            e2 = discord.Embed(description="Raid-protection is now active! Contact a Staff Member for"
                                           " help or wait till you get verified!", colour=discord.Colour.red())
            await self.bot.send_message(chn, embed=e2)

            
    @raidprotect.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def toggle(self, ctx):
        """Toggle raid-protect v2.0. Now auto-creates role and channel on raids!"""
        if self.settings[ctx.message.server.id]['protected']:
            self.settings[ctx.message.server.id]['protected'] = False
            await self.bot.say("Your server is no longer protected, anyone that joins will be able to see all channels.")
        else:
            self.settings[ctx.message.server.id]['protected'] = True
            await self.bot.say("Your server is now protected, anyone that joins will only be able to see the set channel.")
        self.save_settings()
        
    @raidprotect.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def setmembers(self, ctx, members:int):
        """Sets after how many members join in 15 seconds the bot will protect the server.
        0 is unlimited, so that will turn it off. Default is 4."""
        self.settings[ctx.message.server.id]['members'] = members
        self.save_settings()
        await self.bot.say("Members set")
    
    @raidprotect.command(pass_context=True)
    async def members(self, ctx):
        """Shows how many users should join within 15 seconds before the bot should turn on raid protect.
        0 is unlimited."""
        await self.bot.say("I will turn on raid-protect when {} people join within 15 seconds.".format(self.settings[ctx.message.server.id]['members']))
    
    def save_settings(self):
        dataIO.save_json("data/raidprotect/settings.json", self.settings)
        
    async def on_member_join(self, member):
        if (member.server.id in self.settings) and not ("bots" in member.server.name.lower()):
            try:
                temp = self.settings[member.server.id]['joined']
            except KeyError:
                self.settings[member.server.id]['joined'] = 0
            try:
                self.settings[member.server.id]['joined'] += 1
                self.save_settings()
                if self.settings[member.server.id]['members'] != 0:
                    if (self.settings[member.server.id]['joined'] >= self.settings[member.server.id]['members']) and not (self.settings[member.server.id]['protected']):
                        self.settings[member.server.id]['protected'] = True
                        self.save_settings()
                        #for channel in member.server.channels:
                        #    if (channel.id == self.settings[member.server.id]['channel']) and (self.settings[member.server.id]['channel'] != None):
                        #        await self.bot.send_message(channel, "Raid protect has been turned on, more than {} people joined within 15 seconds.".format(self.settings[member.server.id]['members']))
                await asyncio.sleep(15)
                self.settings[member.server.id]['joined'] = 0
                self.save_settings()
            except KeyError:
                pass
            try:
                if self.settings[member.server.id]['protected']:
                    server = member.server
                    chrolename = "raid"
                    try:
                        role = self.find_role(server, chrolename)
                        if role.name == chrolename:
                            await self._auto_give(member)
                    except:
                        covrole = await self.bot.create_role(server, name=chrolename)
                        admin_role = discord.utils.get(server.roles, name=settings.get_server_admin(server))
                        everyone_perms = discord.PermissionOverwrite(read_messages=False)
                        insilenced_perms = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                        mod_admin_perms = discord.PermissionOverwrite(read_messages=True, send_messages=True,
                                                                      manage_channel=True)
                        chn = await self.bot.create_channel(
                            server, chrolename,
                            (server.default_role, everyone_perms),
                            (covrole, insilenced_perms),
                            (admin_role, mod_admin_perms))

                        for role in member.server.roles:
                            if "raid" in role.name:
                                for channelx in member.server.channels:
                                    if "raid" in channelx.name:
                                        for c in member.server.channels:
                                            if c.name != chn.name:
                                                try:
                                                    await self.bot.edit_channel_permissions(c, covrole, everyone_perms)
                                                except discord.errors.Forbidden:
                                                    pass
                        e = discord.Embed(title="Anti-Raid", description="Raid-protection has been set up!",
                                          colour=discord.Colour.red())
                        await self.bot.send_message(chn, embed=e)
                        await asyncio.sleep(1)
                        for c in member.server.channels:
                            if c.name != chn.name:
                                try:
                                    await self.bot.edit_channel_permissions(c, covrole, everyone_perms)
                                except discord.errors.Forbidden:
                                    pass
                        e2 = discord.Embed(description="Raid-protection is now active! Contact a Staff Member for"
                                                      " help or wait till you get verified!", colour=discord.Colour.red())
                        await self.bot.send_message(chn, embed=e2)
                        await self._auto_give(member)
            except KeyError:
                return


def check_folders():
    if not os.path.exists("data/raidprotect"):
        print("Creating data/raidprotect folder...")
        os.makedirs("data/raidprotect")
        
def check_files():
    if not os.path.exists("data/raidprotect/settings.json"):
        print("Creating data/raidprotect/settings.json file...")
        dataIO.save_json("data/raidprotect/settings.json", {})
        
def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(RaidProtect(bot))