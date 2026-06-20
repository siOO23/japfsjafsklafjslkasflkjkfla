import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise SystemExit("❌ Токен не найден! Добавь DISCORD_TOKEN в файл .env")

# Настройка прав
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Хранилище активных тикетов
active_tickets = {}

@bot.event
async def on_ready():
    print('='*50)
    print(f'[OK] Бот {bot.user.name} запущен!')
    print(f'[ID] {bot.user.id}')
    print(f'[Servers] {len(bot.guilds)}')
    print('='*50)
    print('Commands: !ticket, !close, !add, !remove, !tickets')
    print('='*50)

@bot.command()
async def ticket(ctx, *, reason="Обращение в поддержку"):
    """Создать тикет"""
    
    # Проверяем, есть ли уже открытый тикет у пользователя
    for channel in ctx.guild.text_channels:
        if channel.topic and str(ctx.author.id) in channel.topic:
            await ctx.send(f'[X] {ctx.author.mention}, у вас уже есть открытый тикет: {channel.mention}')
            return
    
    # Создаем название канала
    ticket_number = len([c for c in ctx.guild.text_channels if c.name.startswith('ticket-')]) + 1
    channel_name = f'ticket-{ticket_number}'
    
    # Создаем канал
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    }
    
    try:
        channel = await ctx.guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            topic=f"Тикет от {ctx.author} (ID: {ctx.author.id}) | Причина: {reason}"
        )
        
        # Сохраняем в активные тикеты
        active_tickets[channel.id] = {
            'author': ctx.author.id,
            'channel': channel.id,
            'reason': reason
        }
        
        # Отправляем сообщение в канал
        embed = discord.Embed(
            title="🎫 Новый тикет",
            description=f"**Создатель:** {ctx.author.mention}\n**Причина:** {reason}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📌 Инструкция",
            value="• Напишите ваше обращение\n"
                  "• Используйте `!close` чтобы закрыть тикет\n"
                  "• Используйте `!add @участник` чтобы добавить участника\n"
                  "• Используйте `!remove @участник` чтобы удалить участника",
            inline=False
        )
        embed.set_footer(text=f"Тикет #{ticket_number}")
        
        await channel.send(embed=embed)
        await ctx.send(f'[OK] {ctx.author.mention}, тикет создан: {channel.mention}')
        
    except Exception as e:
        await ctx.send(f'[X] Ошибка при создании тикета: {e}')

@bot.command()
async def close(ctx):
    """Закрыть тикет"""
    
    if not ctx.channel.name.startswith('ticket-'):
        await ctx.send('[X] Эта команда работает только в канале тикета!')
        return
    
    if ctx.channel.id in active_tickets:
        ticket_data = active_tickets[ctx.channel.id]
        if ctx.author.id != ticket_data['author'] and not ctx.author.guild_permissions.administrator:
            await ctx.send('[X] Только создатель тикета или администратор могут закрыть его!')
            return
    
    await ctx.send('[WAIT] Тикет будет закрыт через 5 секунд...')
    await asyncio.sleep(5)
    
    try:
        if ctx.channel.id in active_tickets:
            del active_tickets[ctx.channel.id]
        await ctx.channel.delete()
    except Exception as e:
        await ctx.send(f'[X] Ошибка при закрытии тикета: {e}')

@bot.command()
async def add(ctx, member: discord.Member):
    """Добавить участника в тикет"""
    
    if not ctx.channel.name.startswith('ticket-'):
        await ctx.send('[X] Эта команда работает только в канале тикета!')
        return
    
    if ctx.channel.id in active_tickets:
        ticket_data = active_tickets[ctx.channel.id]
        if ctx.author.id != ticket_data['author'] and not ctx.author.guild_permissions.administrator:
            await ctx.send('[X] Только создатель тикета или администратор могут добавлять участников!')
            return
    
    await ctx.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
    await ctx.send(f'[OK] {member.mention} добавлен в тикет!')

@bot.command()
async def remove(ctx, member: discord.Member):
    """Удалить участника из тикета"""
    
    if not ctx.channel.name.startswith('ticket-'):
        await ctx.send('[X] Эта команда работает только в канале тикета!')
        return
    
    if ctx.channel.id in active_tickets:
        ticket_data = active_tickets[ctx.channel.id]
        if ctx.author.id != ticket_data['author'] and not ctx.author.guild_permissions.administrator:
            await ctx.send('[X] Только создатель тикета или администратор могут удалять участников!')
            return
    
    await ctx.channel.set_permissions(member, view_channel=False)
    await ctx.send(f'[OK] {member.mention} удален из тикета!')

@bot.command()
async def tickets(ctx):
    """Показать список активных тикетов (админ)"""
    
    if not ctx.author.guild_permissions.administrator:
        await ctx.send('[X] Только администраторы могут использовать эту команду!')
        return
    
    if not active_tickets:
        await ctx.send('[INFO] Активных тикетов нет.')
        return
    
    embed = discord.Embed(
        title="📋 Активные тикеты",
        color=discord.Color.blue()
    )
    
    for ticket_id, data in active_tickets.items():
        channel = ctx.guild.get_channel(ticket_id)
        if channel:
            user = ctx.guild.get_member(data['author'])
            embed.add_field(
                name=f"#{channel.name}",
                value=f"**Создатель:** {user.mention if user else 'Неизвестно'}\n**Причина:** {data['reason']}",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('[X] У вас нет прав для использования этой команды!')
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send('[X] Участник не найден!')
    else:
        await ctx.send(f'[X] Ошибка: {error}')

if __name__ == '__main__':
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'[X] Ошибка: {e}')