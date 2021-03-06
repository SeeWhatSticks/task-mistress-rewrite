from random import randrange
from discord.ext import commands
from discord import Embed

class Create(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def categories_embed(self, task_id, player_name):
        task = self.bot.tasks[task_id]
        embed = Embed(
            title='Set categories',
            description='Categories for {} ({}): "{}" by {}'.format(
                    task['name'],
                    task_id,
                    task['text'],
                    player_name),
            color=self.bot.COLORS['set'])
        categories = self.bot.game['categories']
        for item in task['categories']:
            embed.add_field(
                    name=categories[item]['symbol'],
                    value=categories[item]['name'],
                    inline=True)
        return embed

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, event):
        user = self.bot.get_user(event.user_id)
        if user.bot:
            return  # Ignore own reactions and other bot reactions
        if event.message_id not in self.bot.interfaces:
            return  # Ignore if this is not an interface message
        interface = self.bot.interfaces[event.message_id]
        if interface['type'] != 'categories':
            return  # Ignore if this is not a categories interface message
        # It is safe to remove the reaction at this point
        channel = self.bot.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)
        await message.remove_reaction(event.emoji, user)
        if interface['player_id'] != user.id:
            return  # Ignore other player's reactions
        for key, value in self.bot.game['categories'].items():
            if event.emoji.name == value['symbol']:
                task = self.bot.tasks[interface['task_id']]
                if key in task['categories']:
                    task['categories'].remove(key)
                else:
                    task['categories'].append(key)
                await message.edit(embed=self.categories_embed(
                        interface['task_id'],
                        user.mention))
        self.bot.save_data()

    @commands.group()
    @commands.guild_only()
    async def create(self, ctx):
        """Lists any tasks you have created."""
        if ctx.invoked_subcommand is None:
            player_tasks = {k: v for (k, v) in self.bot.tasks.items() if v['creator'] == ctx.author.id}
            embed = Embed(
                    title='Task list',
                    description='Showing {} tasks written by {}:'.format(len(player_tasks), ctx.author.name),
                    color=self.bot.COLORS['default'])
            for key in player_tasks.keys():
                task = self.bot.tasks[key]
                embed.add_field(
                        name="{} ({}) {}".format(
                                task['name'],
                                str(key),
                                "".join([self.bot.game['categories'][x]['symbol'] for x in task['categories']])),
                        value=task['text'],
                        inline=False)
            await ctx.channel.send(embed=embed)
        self.bot.save_data()

    @create.command(usage='task_text...')
    async def new(self, ctx, *, task_text):
        """Allows you to create a new task."""
        user = ctx.author
        task_id = 0
        while task_id in self.bot.tasks:
            task_id += 1
        self.bot.tasks[task_id] = {
            'creator': user.id,
            'name': "New Task",
            'categories': [],
            'text': task_text,
            'ratings': {},
            'deleted': False
        }
        message = await ctx.channel.send(embed=self.categories_embed(task_id, user.mention))
        self.bot.interfaces[message.id] = {
            'type': 'categories',
            'player_id': user.id,
            'task_id': task_id,
            'page': 0}
        await self.bot.add_category_reactions(message)
        self.bot.save_data()

    @create.command(usage='task_id task_name...')
    async def name(self, ctx, task_id: int, *, name):
        """Change the name of a task you wrote."""
        user = ctx.author
        try:
            task = self.bot.tasks[task_id]
        except KeyError:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "No task found with that ID."))
            return
        if task['creator'] != user.id:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "That is not your task."))
        if task['deleted']:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "That task has been deleted."))
        task['name'] = name
        await ctx.channel.send(embed=self.bot.confirm_embed(
                user.display_name,
                "Task renamed successfully."))
        self.bot.save_data()

    @create.command(aliases=['cat'], usage='task_id')
    async def categories(self, ctx, task_id: int):
        """Change categories for a task you wrote."""
        user = ctx.author
        try:
            task = self.bot.tasks[task_id]
        except KeyError:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "No task found with that ID."))
            return
        if task['creator'] != user.id:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "That is not your task."))
        if task['deleted']:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "That task has been deleted."))
        message = await ctx.channel.send(embed=self.categories_embed(task_id, user.mention))
        self.bot.interfaces[message.id] = {
            'type': 'categories',
            'player_id': user.id,
            'task_id': task_id,
            'page': 0}
        await self.bot.add_category_reactions(message)
        self.bot.save_data()

    @create.command(aliases=['del'], usage='task_id')
    async def delete(self, ctx, task_id: int):
        """Delete a task you wrote."""
        user = ctx.author
        try:
            task = self.bot.tasks[task_id]
        except KeyError:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "No task found with that ID."))
            return
        if task['creator'] != user.id:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "That is not your task."))
        if task['deleted']:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "That task has been deleted."))
        task['deleted'] = True
        await ctx.channel.send(embed=self.bot.confirm_embed(
                user.display_name,
                "The task was deleted."))
        self.bot.save_data()

def setup(bot):
    bot.add_cog(Create(bot))
