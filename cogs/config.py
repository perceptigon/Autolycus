import discord
from discord.ext import commands
from discord.commands import Option, SlashCommandGroup
import re
import os
from main import mongo, logger

api_key = os.getenv("api_key")

class Config(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    def str_to_id_list(self, str_var):
        try:
            str_var = re.sub("[^0-9]", " ", str_var)
            str_var = str_var.strip().replace(" ", ",")
            index = 0
            while True:
                try:
                    if str_var[index] == str_var[index+1] and not str_var[index].isdigit():
                        str_var = str_var[:index] + str_var[index+1:]
                        index -= 1
                    index += 1
                except Exception as e: 
                    break
            return str_var.split(","), str_var
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e

    config_group = SlashCommandGroup("config", "Configure commands that need configuration")

    @config_group.command(
        name="counters",
        description="Configure the counters command"
    )
    @commands.has_permissions(manage_guild=True)
    async def config_counters(
        self,
        ctx: discord.ApplicationContext,
        alliance_ids: Option(str, "The alliance id(s) to include in the counters command") = []
    ):      
        try:  
            if alliance_ids != []:
                id_list, id_str = self.str_to_id_list(alliance_ids)
            else:
                id_list = []
                id_str = "None"
            mongo.guild_configs.find_one_and_update({"guild_id": ctx.guild.id}, {"$set": {"counters_alliance_ids": id_list}}, upsert=True)
            await ctx.respond(f"Alliance id(s) for `/counters` set to `{id_str}`")
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e

    async def get_alliances(ctx: discord.AutocompleteContext):
        """Returns a list of alliances that begin with the characters entered so far."""
        alliances = list(mongo.alliances.find({}))
        return [f"{aa['name']} ({aa['id']})" for aa in alliances if (ctx.value.lower()) in aa['id'] or (ctx.value.lower()) in aa['name'].lower() or (ctx.value.lower()) in aa['acronym'].lower()]
    
    async def get_target_alliances(ctx: discord.AutocompleteContext):
        """Returns a list of alliances that begin with the characters entered so far."""
        config = mongo.guild_configs.find_one({"guild_id": ctx.interaction.guild_id})
        if config is None:
            return []
        else:
            try:
                ids = config['targets_alliance_ids']
            except:
                return []
        alliances = list(mongo.alliances.find({"id": {"$in": ids}}))
        return [f"{aa['name']} ({aa['id']})" for aa in alliances if (ctx.value.lower()) in aa['id'] or (ctx.value.lower()) in aa['name'].lower() or (ctx.value.lower()) in aa['acronym'].lower()]
    
    @config_group.command(
        name="targets",
        description="Configure the targets command"
    )
    @commands.has_permissions(manage_guild=True)
    async def config_targets(
        self,
        ctx: discord.ApplicationContext,
        add_alliance: Option(str, "An enemy alliance to add to the targets command", autocomplete=get_alliances) = None,
        remove_alliance: Option(str, "An enemy alliance to remove from the targets command", autocomplete=get_target_alliances) = None,
        set_alliances: Option(str, "Overwrite existing alliances with a list of alliance ids") = [],
        view_alliances: Option(bool, "Whether or not you want to see the currently targeted alliances") = False
    ):        
        try:
            await ctx.defer()
            
            if add_alliance:
                alliance_id = None
                for aa in mongo.alliances.find({}):
                    if add_alliance == f"{aa['name']} ({aa['id']})":
                        alliance_id = aa['id']
                        break
                    elif add_alliance == aa['id']:
                        alliance_id = aa['id']
                        break
                    elif add_alliance == aa['name']:
                        alliance_id = aa['id']
                        break
                    elif add_alliance == aa['acronym']:
                        alliance_id = aa['id']
                        break
                                    
                if alliance_id is None:
                    await ctx.respond(f"I could not find a match to `{add_alliance}` in the database!")
                    return
                
                config = mongo.guild_configs.find_one({"guild_id": ctx.guild.id})
                try:
                    if alliance_id in config['targets_alliance_ids']:
                        await ctx.respond(f"An alliance with the id of `{alliance_id}` is already in the list of targeted alliances!")
                        return
                except:
                    pass

                mongo.guild_configs.find_one_and_update({"guild_id": ctx.guild.id}, {"$push": {"targets_alliance_ids": alliance_id}}, upsert=True)
                await ctx.respond(f"Added `{aa['name']} ({aa['id']})` to the `/targets` command")
            
            if remove_alliance:
                alliance_id = None
                config = mongo.guild_configs.find_one({"guild_id": ctx.guild.id})
                if config is None:
                    await ctx.respond(f"I could not find a match to `{remove_alliance}` amongst the targeted alliances!")
                    return
                else:
                    try:
                        ids = config['targets_alliance_ids']
                    except:
                        await ctx.respond(f"I could not find a match to `{remove_alliance}` amongst the targeted alliances!")
                        return
                alliances = list(mongo.alliances.find({"id": {"$in": ids}}))
                for aa in alliances:
                    if remove_alliance == f"{aa['name']} ({aa['id']})":
                        alliance_id = aa['id']
                        break
                    elif remove_alliance == aa['id']:
                        alliance_id = aa['id']
                        break
                    elif remove_alliance == aa['name']:
                        alliance_id = aa['id']
                        break
                    elif remove_alliance == aa['acronym']:
                        alliance_id = aa['id']
                        break
                                    
                if alliance_id is None:
                    await ctx.respond(f"I could not find a match to `{remove_alliance}` amongst the targeted alliances!")
                    return

                mongo.guild_configs.find_one_and_update({"guild_id": ctx.guild.id}, {"$pull": {"targets_alliance_ids": alliance_id}}, upsert=True)
                await ctx.respond(f"Removed `{aa['name']} ({aa['id']})` from the `/targets` command")
            
            if set_alliances != []:
                id_list, id_str = self.str_to_id_list(set_alliances)
                mongo.guild_configs.find_one_and_update({"guild_id": ctx.guild.id}, {"$set": {"targets_alliance_ids": id_list}}, upsert=True)
                await ctx.respond(f"Alliance id(s) for `/targets` set to `{id_str}`")
            elif not add_alliance and not remove_alliance and not view_alliances:
                id_list = []
                id_str = "None"
                mongo.guild_configs.find_one_and_update({"guild_id": ctx.guild.id}, {"$set": {"targets_alliance_ids": id_list}}, upsert=True)
                await ctx.respond(f"Alliance id(s) for `/targets` set to `{id_str}`")
            
            if view_alliances:
                config = mongo.guild_configs.find_one({"guild_id": ctx.guild.id})
                if config is None:
                    ids = None
                else:
                    try:
                        ids = config['targets_alliance_ids']
                    except:
                        ids = None
                alliances = list(mongo.alliances.find({"id": {"$in": ids}}))
                alliance_list = []
                for aa in alliances:
                    alliance_list.append(f"`{aa['name']} ({aa['id']})`")
                if len(alliance_list) == 0:
                    await ctx.respond(f"No alliances are currently targeted!")
                    return
                await ctx.respond(f"Alliance(s) for `/targets` are set to {', '.join(alliance_list)}")

        except Exception as e:
            logger.error(e, exc_info=True)
            raise e
            
def setup(bot):
    bot.add_cog(Config(bot))