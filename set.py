from discord.ext import commands

class Set(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(hidden=True)
    @commands.guild_only()
    @commands.has_role("Administrator")
    async def set(self, ctx):
        if ctx.invoked_subcommand is None:
            print("Set super-command invoked.")

    @set.command()
    async def verificationchannel(self, ctx):
        self.bot.game['verifyChannel'] = ctx.channel.id
        await ctx.channel.send(embed=ctx.bot.confirm_embed(ctx.author.display_name, "Verification channel set."))
        self.bot.save_data()

    @set.command()
    async def beginterval(self, ctx, interval: int):
        self.bot.game['begInterval'] = interval
        await ctx.channel.send(embed=ctx.bot.confirm_embed(ctx.author.display_name, "Beg Interval set."))
        self.bot.save_data()

    @set.command()
    async def treatinterval(self, ctx, interval: int):
        self.bot.game['treatInterval'] = interval
        await ctx.channel.send(embed=ctx.bot.confirm_embed(ctx.author.display_name, "Treat Interval set."))
        self.bot.save_data()

    @set.command()
    async def tasktext(self, ctx, task_id: int, *, task_text):
        self.bot.tasks[task_id]['text'] = task_text
        self.bot.save_data()

def setup(bot):
    bot.add_cog(Set(bot))
