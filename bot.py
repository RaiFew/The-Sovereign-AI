import discord
from discord.ext import commands
from github import Github
from dotenv import load_dotenv

from config.settings import DISCORD_TOKEN, GITHUB_TOKEN, GITHUB_REPO

load_dotenv()

# Initialize Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Initialize GitHub
gh = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
repo = None
if gh and GITHUB_REPO:
    try:
        repo = gh.get_repo(GITHUB_REPO)
    except Exception as e:
        print(f"Failed to initialize GitHub repo: {e} (Please check your GITHUB_REPO and GITHUB_TOKEN in .env)")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Discord Bot is ready to receive commands and post to GitHub Issues.')
    if not repo:
        print("WARNING: GitHub credentials are not configured properly. Issues will not be created.")

@bot.command(name='research')
async def research(ctx, topic: str, *, subject: str):
    """
    Command to start a research task.
    Usage: /research manga [ชื่อเรื่อง]
           /research coding [topic]
    """
    if not repo:
        await ctx.send("GitHub repository is not configured in .env!")
        return

    try:
        # Create a GitHub Issue
        title = f"[{topic.upper()}] Research: {subject}"
        body = f"User requested research via Discord.\nTopic: {topic}\nSubject: {subject}\n\nInitiated by: {ctx.author.name}"
        
        issue = repo.create_issue(
            title=title,
            body=body,
            labels=["task"]
        )
        
        await ctx.send(f"✅ สั่งงานสำเร็จ! สร้างคิวงานบน GitHub เรียบร้อยแล้ว (Issue #{issue.number})\n**Topic:** {topic}\n**Subject:** {subject}")
    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาดในการสร้าง Issue บน GitHub: {e}")

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong! Sovereign AI Bot is active.')

@bot.command(name='queue')
async def queue(ctx):
    """
    แสดงสถานะคิวงานทั้งหมดจาก GitHub Issues
    Usage: /queue
    """
    if not repo:
        await ctx.send("❌ GitHub repository is not configured in .env!")
        return

    try:
        # Fetch open issues (pending/in-progress)
        open_issues = list(repo.get_issues(state='open'))
        # Fetch recently closed issues (completed) — last 5
        closed_issues = list(repo.get_issues(state='closed', sort='updated', direction='desc'))[:5]

        # Build status message
        msg = "📋 **Sovereign AI — Task Queue Status**\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Pending tasks (open, no 'processed' label)
        pending = [i for i in open_issues if 'processed' not in [l.name for l in i.labels]]
        processing = [i for i in open_issues if 'processed' in [l.name for l in i.labels]]

        msg += f"🟡 **Pending** ({len(pending)} tasks)\n"
        if pending:
            for i, issue in enumerate(pending, 1):
                msg += f"  `{i}.` #{issue.number} — {issue.title}\n"
        else:
            msg += "  _ไม่มีงานค้าง_\n"

        msg += f"\n🔵 **Processing** ({len(processing)} tasks)\n"
        if processing:
            for i, issue in enumerate(processing, 1):
                msg += f"  `{i}.` #{issue.number} — {issue.title}\n"
        else:
            msg += "  _ไม่มีงานกำลังประมวลผล_\n"

        msg += f"\n✅ **Completed (ล่าสุด 5 รายการ)**\n"
        if closed_issues:
            for i, issue in enumerate(closed_issues, 1):
                msg += f"  `{i}.` #{issue.number} — {issue.title}\n"
        else:
            msg += "  _ยังไม่มีงานที่เสร็จ_\n"

        msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN is missing in .env")
    else:
        bot.run(DISCORD_TOKEN)
