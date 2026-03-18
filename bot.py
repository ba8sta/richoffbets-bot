import os
import re
import unicodedata
import discord
from discord.ext import commands
from dotenv import load_dotenv
from difflib import SequenceMatcher

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
JOIN_LOG_CHANNEL_ID = int(os.getenv("JOIN_LOG_CHANNEL_ID", "0"))
IMPERSONATOR_ALERT_CHANNEL_ID = int(os.getenv("IMPERSONATOR_ALERT_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

WELCOME_DM = """🔥 Welcome to RICHoffBETS 🔥

You're officially in 🤝💸

📌 Start here:
- welcome
- rules
- how-to-join-vip
- free-picks

🚨 Important:
I do NOT have a Telegram.
I only have ONE Discord account.
If anyone messages you pretending to be me or staff, it is fake.

💰 If you want VIP access, check how-to-join-vip.
Big plays, free picks, and nukes get posted throughout the server.

Good luck and let's cash 🐐🔥
"""

# Names you want protected
PROTECTED_NAMES = [
    "blaize",
    "richoffbets",
    "vipgoats",
]

# Extra suspicious words often used by impersonators
SUSPICIOUS_WORDS = [
    "support",
    "admin",
    "mod",
    "moderator",
    "staff",
    "official",
    "owner",
]

def normalize_name(text: str) -> str:
    """Lowercase, remove accents/special unicode, and strip non-alphanumerics."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", "", text)
    return text

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def check_impersonation(name: str) -> tuple[bool, str]:
    """
    Returns (is_suspicious, reason)
    """
    raw_lower = name.lower()
    cleaned = normalize_name(name)

    for protected in PROTECTED_NAMES:
        protected_clean = normalize_name(protected)

        # Exact cleaned match
        if cleaned == protected_clean:
            return True, f"Exact match to protected name: {protected}"

        # Very close similarity
        if similarity(cleaned, protected_clean) >= 0.88:
            return True, f"Very similar to protected name: {protected}"

        # Protected name included + suspicious staff-like wording
        if protected_clean in cleaned:
            for word in SUSPICIOUS_WORDS:
                if word in raw_lower:
                    return True, f"Protected name + suspicious word: {protected} + {word}"

    return False, ""

async def send_impersonator_alert(member: discord.Member, reason: str):
    if not IMPERSONATOR_ALERT_CHANNEL_ID:
        return

    channel = bot.get_channel(IMPERSONATOR_ALERT_CHANNEL_ID)
    if not channel:
        return

    embed = discord.Embed(
        title="🚨 Impersonator Detected",
        color=discord.Color.red()
    )
    embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
    embed.add_field(name="Display Name", value=member.display_name, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)

    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Slash sync failed: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    # Anti-impersonation check first
    suspicious, reason = check_impersonation(member.display_name)
    if suspicious:
        await send_impersonator_alert(member, reason)
        try:
            await member.kick(reason=f"Impersonation detected: {reason}")
            return
        except Exception as e:
            print(f"Failed to kick suspicious member {member}: {e}")

    # Welcome DM
    dm_sent = True
    try:
        await member.send(WELCOME_DM)
    except Exception:
        dm_sent = False

    # Join log
    if JOIN_LOG_CHANNEL_ID:
        channel = bot.get_channel(JOIN_LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="New Member Joined", color=discord.Color.green())
            embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
            embed.add_field(name="DM Sent", value="Yes" if dm_sent else "No", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.display_name == after.display_name:
        return

    suspicious, reason = check_impersonation(after.display_name)
    if suspicious:
        await send_impersonator_alert(after, f"{reason} (after nickname change)")
        try:
            await after.kick(reason=f"Impersonation detected after nickname change: {reason}")
        except Exception as e:
            print(f"Failed to kick suspicious member after update {after}: {e}")

bot.run(TOKEN)