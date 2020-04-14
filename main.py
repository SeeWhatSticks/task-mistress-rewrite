from datetime import datetime
import json
from types import MethodType
from discord import Embed
from discord.ext import commands

bot = commands.Bot(command_prefix='!')
bot.load_extension('play')
bot.load_extension('verify')
bot.load_extension('create')
bot.load_extension('set')

bot.CHECK_MARK_BUTTONS = "✅"
bot.NUMBER_BUTTONS = {
    "1️⃣": 1,
    "2️⃣": 2,
    "3️⃣": 3,
    "4️⃣": 4,
    "5️⃣": 5
}
bot.BKWD_ARROW = "◀️"
bot.FRWD_ARROW = "▶️"
bot.COLORS = {
    'default': 0x3300cc,
    'set': 0x003399,
    'verify': 0xff3399,
    'confirm': 0x33ff33,
    'error': 0xff3333
}

with open('data/game.json', 'r', encoding='utf8') as file:
    bot.game = json.load(file)

with open('data/tasks.json', 'r', encoding='utf8') as file:
    bot.tasks = json.load(file)
    bot.tasks = {int(k): v for (k, v) in bot.tasks.items()}
    for task in bot.tasks.values():
        task['ratings'] = {int(k): v for (k, v) in task['ratings'].items()}

with open('data/players.json', 'r', encoding='utf8') as file:
    bot.players = json.load(file)
    bot.players = {int(k): v for (k, v) in bot.players.items()}
    for player in bot.players.values():
        player['tasks'] = {int(k): v for (k, v) in player['tasks'].items()}

with open('data/interfaces.json', 'r', encoding='utf8') as file:
    bot.interfaces = json.load(file)
    bot.interfaces = {int(k): v for (k, v) in bot.interfaces.items()}

def get_player_data(self, user_id):
    if user_id not in self.players:
        bot.players[user_id] = {
            'available': False,
            'tasks': {},
            'lastBegTime': None,
            'lastTreatTime': None,
            'limits': []
        }
        for key in self.game['categories'].keys():
            bot.players[user_id]['limits'].append(key)
    return bot.players[user_id]
bot.get_player_data = MethodType(get_player_data, bot)

async def add_category_reactions(self, message):
    await message.clear_reactions()
    await message.add_reaction(self.BKWD_ARROW)
    page = self.interfaces[message.id]['page']
    for value in self.game['categories'].values():
        if value['page'] == page:
            await message.add_reaction(value['symbol'])
    await message.add_reaction(self.FRWD_ARROW)
bot.add_category_reactions = MethodType(add_category_reactions, bot)

def confirm_embed(name, confirm_string):
    return Embed(
            title='Confirmation for {}'.format(name),
            description=confirm_string,
            color=bot.COLORS['confirm'])
bot.confirm_embed = confirm_embed

def error_embed(name, error_string):
    return Embed(
            title='Error for {}'.format(name),
            description=error_string,
            color=bot.COLORS['error'])
bot.error_embed = error_embed

def calculate_severity(task):
    return round(sum([v for v in task['ratings'].values()]) / len(task['ratings']))
bot.calculate_severity = calculate_severity

def calculate_score(player):
    print(player['tasks'].values())
    completed_tasks = [k for (k, v) in player['tasks'].items() if v['completed']]
    return sum([calculate_severity(bot.tasks[v]) for v in completed_tasks])

def save_data(self):
    with open('data/game.json', 'w+') as file:
        file.write(json.dumps(self.game, indent=4))
    with open('data/tasks.json', 'w+') as file:
        file.write(json.dumps(self.tasks, indent=4))
    with open('data/players.json', 'w+') as file:
        file.write(json.dumps(self.players, indent=4))
    with open('data/interfaces.json', 'w+') as file:
        file.write(json.dumps(self.interfaces, indent=4))
bot.save_data = MethodType(save_data, bot)

@bot.event
async def on_command_error(ctx, error):
    await ctx.channel.send(embed=ctx.bot.error_embed(
            ctx.author.display_name,
            str(error)))

@bot.event
async def on_ready():
    print('We have logged in as {}'.format(bot.user))

@bot.event
async def on_raw_reaction_add(event):
    user = bot.get_user(event.user_id)
    if user.bot:
        return  # Ignore own reactions and other bot reactions
    if event.message_id not in bot.interfaces:
        return  # Ignore if this is not an interface message
    interface = bot.interfaces[event.message_id]
    if 'page' not in interface:
        return  # Ignore interfaces that don't have pages
    channel = bot.get_channel(event.channel_id)
    message = await channel.fetch_message(event.message_id)
    if event.emoji.name == bot.FRWD_ARROW:
        interface['page'] = interface['page'] + 1
        if interface['page'] > bot.game['lastCategoryPage']:
            interface['page'] = 0
        await bot.add_category_reactions(message)
        return
    elif event.emoji.name == bot.BKWD_ARROW:
        interface['page'] = interface['page'] - 1
        if interface['page'] < 0:
            interface['page'] = bot.game['lastCategoryPage']
        await bot.add_category_reactions(message)
        return

@bot.command(hidden=True)
@commands.has_role("Administrator")
async def begin(ctx):
    user = ctx.author
    season_number = bot.game['seasonNumber']
    if season_number is None:
        bot.game['seasonNumber'] = 1
    else:
        bot.game['seasonNumber'] = season_number + 1
        player_scores = {k: calculate_score(v) for (k, v) in bot.players.items()}
        top = max(player_scores.values())
        winners = {}
        for k, v in player_scores.items():
            if v == top:
                winners[k] = await bot.fetch_user(k)
        bot.game['pastWinners'][season_number] = {
            'winners': [v.id for v in winners.values()],
            'score': top
        }
        embed = Embed(
                title="Winners",
                description='Winners for season {}'.format(season_number),
                color=bot.COLORS['default'])
        embed.add_field(
                name='With {} points'.format(top),
                value=", ".join([winner.mention for winner in winners.values()]),
                inline=False)
        await ctx.channel.send(embed=embed)
    await ctx.channel.send(embed=confirm_embed(
            user.display_name,
            "Scores and tasks have been reset, a new game has started!"))
    bot.game['seasonBegin'] = datetime.now().timestamp()
    # Reset player data
    for key in bot.players:
        player = bot.players[key]
        player['tasks'] = {}
        player['lastBegTime'] = None
        player['lastTreatTime'] = None
    bot.interfaces = {k: v for (k, v) in bot.interfaces.items() if v['type'] is not 'verification'}
    ctx.bot.save_data()

@bot.command(hidden=True)
@commands.has_role("Administrator")
async def end(ctx):
    bot.save_data()
    await bot.close()

# Get the Discord token from local a plaintext file
with open('token.txt', 'r') as file:
    # This line causes the client to connect to the server
    bot.run(file.read())
