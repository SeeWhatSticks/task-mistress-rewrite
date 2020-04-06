from random import choice
from datetime import datetime
import typing
from discord.ext import commands
from discord import Embed, Member

class Play(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def limits_embed(self, player_id, player_name):
        player = self.bot.get_player_data(player_id)
        embed = Embed(
            title='Set limits',
            description='Limits for {}'.format(player_name),
            color=0x6666ee)
        categories = self.bot.game['categories']
        for item in player['limits']:
            embed.add_field(
                name=categories[item]['symbol'],
                value=categories[item]['name']
            )
        return embed

    def assignment_embed(self, task_id, player_name):
        task = self.bot.tasks[task_id]
        embed = Embed(
            title='Task assigned to {}'.format(player_name),
            description='Task {}: "{}"'.format(task_id, task['text']),
            color=0x993399)
        categories = self.bot.game['categories']
        for item in task['categories']:
            embed.add_field(
                name=categories[item]['symbol'],
                value=categories[item]['name'],
                inline=True)
        return embed

    def get_options_for(self, player):
        return [k for (k, v) in self.bot.tasks.items()
                if not v['deleted']
                if k not in player['tasks']
                if not any(item in player['limits'] for item in v['categories'])]

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, event):
        user = self.bot.get_user(event.user_id)
        if user.bot:
            return  # Ignore own reactions and other bot reactions
        if event.message_id not in self.bot.interfaces:
            return  # Ignore if this is not an interface message
        interface = self.bot.interfaces[event.message_id]
        if interface['type'] != 'limits':
            return  # Ignore if this is not a limits interface message
        # It is safe to remove the reaction at this point
        channel = self.bot.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)
        await message.remove_reaction(event.emoji, user)
        if interface['player_id'] != user.id:
            return  # Ignore other player's reactions
        for key, value in self.bot.game['categories'].items():
            if event.emoji.name == value['symbol']:
                player = self.bot.get_player_data(user.id)
                if key in player['limits']:
                    player['limits'].remove(key)
                else:
                    player['limits'].append(key)
                await message.edit(embed=self.limits_embed(
                        user.id,
                        user.mention))

    @commands.command()
    async def available(self, ctx, b: bool):
        """Marks you as available for additional tasks."""
        user = ctx.author
        player = self.bot.get_player_data(user.id)
        if b is None:
            player['available'] = not player['available']
        else:
            player['available'] = b
        if player['available']:
            await ctx.channel.send(embed=self.bot.confirm_embed(
                    user.name,
                    "You have been marked as available."))
        else:
            await ctx.channel.send(embed=self.bot.confirm_embed(
                    user.name,
                    "You have been marked as unavailable."))

    @commands.command()
    async def beg(self, ctx):
        """Provides a task to the supplicant, if allowed."""
        user = ctx.author
        player = self.bot.get_player_data(user.id)
        if len(player['limits']) == 0:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.name,
                    "You don't have any limits set. Consider using the !limits command to set them."))
        if (player['lastBegTime'] is not None and
                datetime.now().timestamp() < player['lastBegTime'] + self.bot.game['begInterval']):
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.name,
                    "You haven't earned another task yet. You need to learn patience."))
            return
        options = self.get_options_for(player)
        if len(options) == 0:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.name,
                    "There are no valid tasks for you. Consider relaxing your limits."))
            return
        task_key = choice(options)
        player['tasks'][task_key] = {
            'completed': False,
            'verifiers': []
        }
        message = await ctx.channel.send(embed=self.assignment_embed(task_key, user.name))
        player['lastBegTime'] = message.created_at.timestamp()

    @commands.command()
    async def treat(self, ctx, target: Member, task_id: typing.Optional[int]):
        """Give a task to someone else."""
        user = ctx.author
        user_player = self.bot.get_player_data(user.id)
        target_player = self.bot.get_player_data(target.id)
        if not target_player['available']:
            await ctx.channel.send(embed=self.bot.error_embed(
                user.name,
                "That player is not available for additional tasks."))
            return
        if (user_player['lastTreatTime'] is not None and
                datetime.now().timestamp() < user_player['lastTreatTime'] + self.bot.game['treatInterval']):
            await ctx.channel.send(embed=self.bot.error_embed(
                user.name,
                "Not enough time has passed since you were last so gracious."))
            return
        if task_id is None:
            options = self.get_options_for(target_player)
            if len(options) == 0:
                await ctx.channel.send(embed=self.bot.error_embed(
                        user.name,
                        "There are no valid tasks for that player."))
                return
            task_id = choice(options)
        else:
            if task_id not in self.bot.tasks:
                await ctx.channel.send(embed=self.bot.error_embed(
                        user.name,
                        "There is no task by the specified ID."))
                return
            task = self.bot.tasks[task_id]
            if any(item in target_player['limits'] for item in task['categories']):
                await ctx.channel.send(embed=self.bot.error_embed(
                        user.name,
                        "The task you selected breaks that player's limits."))
        message = await ctx.channel.send(embed=self.assignment_embed(
                task_id,
                target.name))
        user_player['lastTreatTime'] = message.created_at.timestamp()

    @commands.command()
    async def limits(self, ctx):
        """Lists your limits and allows you to edit them."""
        user = ctx.author
        message = await ctx.channel.send(embed=self.limits_embed(
                user.id,
                user.mention))
        self.bot.interfaces[message.id] = {
            'type': 'limits',
            'player_id': user.id,
            'page': 0}
        await self.bot.add_category_reactions(message)

    @commands.command()
    async def list(self, ctx):
        """Lists incomplete tasks assigned to you."""
        user = ctx.author
        player = self.bot.get_player_data(user.id)
        player_tasks = {k: v for (k, v) in player['tasks'].items() if not v['completed']}
        embed = Embed(
                title='Task list',
                description='Showing {} tasks assigned to {}:'.format(len(player_tasks), user.name),
                color=0x6666ee)
        for key in player_tasks.keys():
            task = self.bot.tasks[key]
            embed.add_field(
                    name=str(key)+" "+", ".join([self.bot.game['categories'][x]['symbol'] for x in task['categories']]),
                    value=task['text'],
                    inline=True)
        await ctx.channel.send(embed=embed)

def setup(bot):
    bot.add_cog(Play(bot))
