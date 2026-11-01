import discord
from discord.ext import commands
from discord import app_commands
import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# ВСТАВЬ СВОЙ ТОКЕН ИЗ DISCORD СЮДА
TOKEN = "ОТРЕДАКТИРОВАНО"
# ID канала для логов (создай в Discord канал #логи и скопируй его ID)
# Как включить режим разработчика: Настройки Discord -> Расширенные -> Режим разработчика (ВКЛ).
# Потом нажми правой кнопкой на канал -> Копировать ID.
LOG_CHANNEL_ID = 123456789012345678 # <--- ЗАМЕНИ НА ID СВОЕГО КАНАЛА ДЛЯ ЛОГОВ

# Создаем бота с нужными намерениями (Intents)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- СОБЫТИЯ ---
@bot.event
async def on_ready():
    print(f"Бот {bot.user} успешно запущен!")
    try:
        # Синхронизируем слеш-команды с сервером
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} слеш-команд.")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")

# --- ФУНКЦИЯ ДЛЯ ЛОГОВ ---
async def send_log(guild, text):
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="📝 Лог действия",
            description=text,
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        await log_channel.send(embed=embed)

# --- СЛЕШ-КОМАНДЫ ---

# 1. /hello
@bot.tree.command(name="hello", description="Приветствие от бота")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Привет, {interaction.user.mention}! Рад тебя видеть 👋")
    await send_log(interaction.guild, f"Пользователь {interaction.user.name} использовал /hello")

# 2. /ping
@bot.tree.command(name="ping", description="Проверка задержки бота")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Понг! Задержка: {latency} мс")

# 3. /server
@bot.tree.command(name="server", description="Информация о сервере")
async def server(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Информация о сервере: {guild.name}", color=discord.Color.green())
    embed.add_field(name="Владелец", value=guild.owner.mention if guild.owner else "Неизвестно")
    embed.add_field(name="Участников", value=guild.member_count)
    embed.add_field(name="Создан", value=guild.created_at.strftime("%d.%m.%Y"))
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await interaction.response.send_message(embed=embed)

# 4. /user
@bot.tree.command(name="user", description="Информация о пользователе")
async def user(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    embed = discord.Embed(title=f"Информация о {target.name}", color=discord.Color.purple())
    embed.add_field(name="ID", value=target.id)
    embed.add_field(name="Присоединился", value=target.joined_at.strftime("%d.%m.%Y"))
    embed.add_field(name="Аккаунт создан", value=target.created_at.strftime("%d.%m.%Y"))
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

# 5. /kick (только для модераторов)
@bot.tree.command(name="kick", description="Выгнать пользователя с сервера (только для модераторов)")
@app_commands.describe(member="Пользователь, которого нужно выгнать", reason="Причина кика")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Не указана"):
    # Проверка прав
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("⛔ У вас нет прав на кик участников!", ephemeral=True)
        return
    
    if member == interaction.user:
        await interaction.response.send_message("Вы не можете выгнать самого себя!", ephemeral=True)
        return

    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"✅ Пользователь {member.mention} был выгнан. Причина: {reason}")
        # Отправляем лог в канал
        await send_log(interaction.guild, f"🔨 Модератор {interaction.user.name} выгнал {member.name}. Причина: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("У бота нет прав на кик (проверьте иерархию ролей).", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Ошибка: {e}", ephemeral=True)

# --- ЗАПУСК ---
bot.run(TOKEN)