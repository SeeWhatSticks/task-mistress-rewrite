from discord.ext import commands

class Set(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(hidden=True)
    @commands.has_role("Administrator")
    async def set(self, ctx):
        if ctx.invoked_subcommand is None:
            print("Set super-command invoked.")

    @set.command()
    async def verifychannel(self, ctx):
        self.bot.game['verifyChannel'] = ctx.channel.id

    @set.command()
    async def botspamchannel(self, ctx):
        self.bot.game['botspamChannel'] = ctx.channel.id

    @set.command()
    async def beginterval(self, ctx, interval: int):
        self.bot.game['begInterval'] = interval

    @set.command()
    async def treatinterval(self, ctx, interval: int):
        self.bot.game['treatInterval'] = interval

    @set.command()
    async def tasktext(self, ctx, task_id: int, *, task_text):
        self.bot.tasks[task_id]['text'] = task_text

def setup(bot):
    bot.add_cog(Set(bot))
