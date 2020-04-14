from discord import Embed
from discord.ext import commands

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def verification_embed(self, task_id, player_id, player_name, verifiers):
        task = self.bot.tasks[task_id]
        embed = Embed(
                title="Verify task completion",
                description='{} ({}): "{}"'.format(
                        task['name'],
                        task_id,
                        task['text']),
                color=self.bot.COLORS['verify'])
        for verifier in verifiers:
            embed.add_field(
                    name="Verified by:",
                    value=verifier,
                    inline=False
            )
        if player_id in task['ratings']:
            embed.set_footer(text="Rated {} for severity by {}".format(
                        task['ratings'][player_id],
                        player_name))
        else:
            embed.set_footer(text="Not yet rated by {}".format(
                    player_name))
        return embed

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, event):
        user = self.bot.get_user(event.user_id)
        if user.bot:
            return  # Ignore own reactions and other bot reactions
        if event.message_id not in self.bot.interfaces:
            return  # Ignore if this is not an interface message
        interface = self.bot.interfaces[event.message_id]
        if self.bot.interfaces[event.message_id]['type'] != 'verification':
            return  # Ignore if this is not a verification interface message
        # It is safe to remove the reaction at this point
        channel = self.bot.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)
        player = self.bot.get_player_data(interface['player_id'])
        await message.remove_reaction(event.emoji, user)
        if interface['player_id'] == user.id:
            # The player may click a number
            if event.emoji.name in self.bot.NUMBER_BUTTONS:
                task = self.bot.tasks[interface['task_id']]
                task['ratings'][user.id] = self.bot.NUMBER_BUTTONS[event.emoji.name]
                await message.clear_reactions()
                await message.add_reaction(self.bot.CHECK_MARK_BUTTONS)
        else:
            # The player may click the check mark
            if event.emoji.name == self.bot.CHECK_MARK_BUTTONS:
                if user.id not in player['tasks'][interface['task_id']]['verifiers']:
                    player['tasks'][interface['task_id']]['verifiers'].append(user.id)
        verifier_names = []
        for verifier_id in player['tasks'][interface['task_id']]['verifiers']:
            verifier = await self.bot.fetch_user(verifier_id)
            verifier_names.append(verifier.display_name)
        await message.edit(embed=self.verification_embed(
                interface['task_id'],
                interface['player_id'],
                self.bot.get_user(interface['player_id']).display_name,
                verifier_names))
        self.bot.save_data()

    @commands.command(usage='task_id')
    async def verify(self, ctx, task_id: int):
        """Request that other players verify the completion of a task."""
        user = ctx.author
        if ctx.channel.id != self.bot.game['verifyChannel']:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "You must verify task completion in the #verification channel."))
            return
        if task_id not in self.bot.tasks:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "Couldn't find a task with that ID."))
            return
        player = self.bot.get_player_data(user.id)
        if task_id not in player['tasks']:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "You haven't been assigned that task."))
            return
        if player['tasks'][task_id]['completed']:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.display_name,
                    "You have already completed that task."))
            return
        player['tasks'][task_id]['completed'] = True
        message = await ctx.channel.send(embed=self.verification_embed(
                task_id,
                user.id,
                user.display_name,
                []))
        self.bot.interfaces[message.id] = {
            'type': 'verification',
            'player_id': user.id,
            'task_id': task_id}
        await message.add_reaction(self.bot.CHECK_MARK_BUTTONS)
        for button in self.bot.NUMBER_BUTTONS.keys():
            await message.add_reaction(button)
        self.bot.save_data()

def setup(bot):
    bot.add_cog(Verify(bot))
