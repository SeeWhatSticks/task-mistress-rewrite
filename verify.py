from discord import Embed
from discord.ext import commands

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def verification_embed(self, task_id, player_id, player_name, verifiers):
        task = self.bot.tasks[task_id]
        embed = Embed(
            title="Verify task completion",
            description='Task {}: "{}" completed by {}'.format(
                task_id,
                self.bot.tasks[task_id]['text'],
                player_name),
            color=0x99ee99)
        if player_id in task['ratings']:
            embed.add_field(
                name="Rated by {}".format(player_name),
                value=task['ratings'][player_id],
                inline=False)
        if len(verifiers) is not 0:
            embed.add_field(
                name="Verified by:",
                value=", ".join(verifiers),
                inline=False
            )
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
        else:
            # The player may click the check mark
            if event.emoji.name == self.bot.CHECK_MARK_BUTTONS:
                if user.id not in player['tasks'][interface['task_id']]['verifiers']:
                    player['tasks'][interface['task_id']]['verifiers'].append(user.id)
        verifier_names = []
        for verifier_id in player['tasks'][interface['task_id']]['verifiers']:
            verifier = await self.bot.fetch_user(verifier_id)
            verifier_names.append(verifier.name)
        await message.edit(embed=self.verification_embed(
                interface['task_id'],
                interface['player_id'],
                self.bot.get_user(interface['player_id']).name,
                verifier_names))

    @commands.command()
    async def verify(self, ctx, task_id: int):
        """Request that other players verify the completion of a task."""
        user = ctx.author
        if ctx.channel.id != self.bot.game['verifyChannel']:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.name,
                    "You must verify task completion in the #verification channel."))
            return
        if task_id not in self.bot.tasks:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.name,
                    "Couldn't find a task with that ID."))
            return
        player = self.bot.get_player_data(user.id)
        if task_id not in player['tasks']:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.name,
                    "You haven't been assigned that task."))
            return
        if player['tasks'][task_id]['completed']:
            await ctx.channel.send(embed=self.bot.error_embed(
                    user.name,
                    "You have already completed that task."))
            return
        player['tasks'][task_id]['completed'] = True
        message = await ctx.channel.send(embed=self.verification_embed(
                task_id,
                user.id,
                user.name,
                []))
        self.bot.interfaces[message.id] = {
            'type': 'verification',
            'player_id': user.id,
            'task_id': task_id}
        await message.add_reaction(self.bot.CHECK_MARK_BUTTONS)
        for medal in self.bot.NUMBER_BUTTONS.keys():
            await message.add_reaction(medal)

def setup(bot):
    bot.add_cog(Verify(bot))
