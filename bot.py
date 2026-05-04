import discord
import asyncio
from discord.ext import commands, tasks
from github import Github
from dotenv import load_dotenv

from config.settings import DISCORD_TOKEN, GITHUB_TOKEN, GITHUB_REPO
from agents.agent_manager import AgentManager
from agents.prompts import PROMPTS

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

# Initialize Agent Manager
agent_manager = AgentManager()

# Track which channel to report back to
report_channel_id = None

# ─── Pipeline Logic ───────────────────────────────────────────

async def run_pipeline(task_description: str, status_callback=None) -> dict:
    """
    Executes the full agent pipeline sequentially.
    status_callback: async function to send progress updates
    """
    results = {}
    steps = [
        # Agent A: แค่อ่าน Obsidian files → LOCAL ได้
        ("A", "🔍 Agent A (Gatekeeper): อ่าน Lessons Learned [LOCAL]...", True),
        # Agent B: วางแผนซับซ้อน Tree of Thoughts → CLOUD
        ("B", "📋 Agent B (Strategist): วางแผนวิจัย [CLOUD]...", False),
        # Agent C: ค้นหาข้อมูลจากแหล่งข้อมูลโลก → CLOUD
        ("C", "🌐 Agent C (Hunter): ค้นหาข้อมูล [CLOUD]...", False),
        # Agent J: ตัดขยะ ลด Token → LOCAL (ตาม PDF)
        ("J", "🗜️ Agent J (Compressor): บีบอัดข้อมูล [LOCAL]...", True),
        # Agent D: แปลภาษา+เรียบเรียง → CLOUD (ต้องการความแม่นยำ)
        ("D", "🧵 Agent D (Weaver): แปลและเรียบเรียง [CLOUD]...", False),
        # Agent E: Red Teaming จับผิด → CLOUD (ต้องวิเคราะห์เชิงลึก)
        ("E", "⚔️ Agent E (Opponent): ตรวจจับจุดอ่อน [CLOUD]...", False),
        # Agent F: ตรวจ QA → LOCAL (ตาม PDF)
        ("F", "✅ Agent F (Auditor): ตรวจ QA [LOCAL]...", True),
        # Agent G: เขียน Obsidian + Mermaid → CLOUD (ต้องสร้าง content)
        ("G", "🏗️ Agent G (Architect): เขียนลง Obsidian [CLOUD]...", False),
        # Agent H: สรุปผลส่ง Discord → CLOUD (ต้องเรียบเรียงสวย)
        ("H", "📨 Agent H (Secretary): สรุปผล [CLOUD]...", False),
        # Agent I: อ่าน Log + วิเคราะห์ → LOCAL ได้
        ("I", "📊 Agent I (Optimizer): บันทึก Log [LOCAL]...", True),
    ]

    # Build prompts for each step
    def get_prompt(agent_key):
        if agent_key == "A":
            return task_description
        elif agent_key == "B":
            return f"Task: {task_description}\n\nConstraints from Gatekeeper:\n{results.get('A', '')}"
        elif agent_key == "C":
            return f"Research Plan:\n{results.get('B', '')}"
        elif agent_key == "J":
            return f"Raw Data:\n{results.get('C', '')}"
        elif agent_key == "D":
            return f"Compressed Data:\n{results.get('J', '')}"
        elif agent_key == "E":
            return f"Draft to review:\n{results.get('D', '')}"
        elif agent_key == "F":
            return f"Draft:\n{results.get('D', '')}\n\nCritique:\n{results.get('E', '')}\n\nPlease finalize and ensure formatting."
        elif agent_key == "G":
            return f"Final QA'd Content:\n{results.get('F', '')}"
        elif agent_key == "H":
            return f"Task: {task_description}\nPipeline results ready. Final output:\n{results.get('G', '')}"
        elif agent_key == "I":
            return "Analyze this pipeline run and output logs."
        return ""

    for agent_key, status_msg, is_local in steps:
        if status_callback:
            await status_callback(status_msg)

        prompt = get_prompt(agent_key)
        # Run agent in a thread to not block the bot event loop
        result = await asyncio.to_thread(
            agent_manager.execute_agent,
            agent_key, prompt, is_local, PROMPTS[agent_key]
        )
        results[agent_key] = result

    return results

# ─── Bot Events ───────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('─' * 40)
    print('Commands available:')
    print('  /ping           - ทดสอบบอท')
    print('  /research <topic> <subject> - สั่งวิจัย')
    print('  /run            - ดึง Issue จาก GitHub แล้วรัน Pipeline')
    print('  /queue          - ดูสถานะคิวงาน')
    print('─' * 40)
    if not repo:
        print("⚠️ WARNING: GitHub credentials not configured. /research and /run won't work.")

# ─── Commands ─────────────────────────────────────────────────

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('🏓 Pong! Sovereign AI Bot is active.')

@bot.command(name='research')
async def research(ctx, topic: str, *, subject: str):
    """
    สั่งงานวิจัย — สร้าง GitHub Issue เข้าคิว
    Usage: /research manga Solo Leveling
           /research coding Next.js Server Actions
           /research trading XAU/USD Analysis
    """
    if not repo:
        await ctx.send("❌ GitHub repository is not configured in .env!")
        return

    try:
        title = f"[{topic.upper()}] Research: {subject}"
        body = (
            f"**User requested research via Discord.**\n"
            f"- **Topic:** {topic}\n"
            f"- **Subject:** {subject}\n"
            f"- **Initiated by:** {ctx.author.name}\n"
            f"- **Channel:** #{ctx.channel.name}"
        )

        issue = repo.create_issue(title=title, body=body, labels=["task"])

        await ctx.send(
            f"✅ **สั่งงานสำเร็จ!** สร้างคิวงานบน GitHub เรียบร้อยแล้ว\n"
            f"📌 Issue #{issue.number} — `{title}`\n"
            f"▸ ใช้ `/run` เพื่อเริ่มประมวลผล Pipeline ทันที\n"
            f"▸ ใช้ `/queue` เพื่อดูสถานะคิว"
        )
    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาดในการสร้าง Issue: {e}")

@bot.command(name='run')
async def run(ctx):
    """
    ดึง Issue ที่ยังไม่ได้ประมวลผลจาก GitHub แล้วรัน Agent Pipeline ทันที
    Usage: /run
    """
    if not repo:
        await ctx.send("❌ GitHub repository is not configured!")
        return

    await ctx.send("🔄 กำลังตรวจสอบคิวงานจาก GitHub...")

    try:
        open_issues = list(repo.get_issues(state='open'))
        pending = [i for i in open_issues if 'processed' not in [l.name for l in i.labels]]

        if not pending:
            await ctx.send("📭 ไม่มีงานค้างในคิว ใช้ `/research` เพื่อสร้างงานใหม่")
            return

        # Process the oldest pending issue first
        issue = pending[-1]  # oldest first (GitHub returns newest first)

        await ctx.send(
            f"⚡ **เริ่มประมวลผล Pipeline!**\n"
            f"📌 Issue #{issue.number} — {issue.title}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        # Status callback to send progress to Discord
        async def send_status(msg):
            await ctx.send(f"  ▸ {msg}")

        # Run the pipeline
        task_description = issue.body or issue.title
        results = await run_pipeline(task_description, status_callback=send_status)

        # Send Secretary output (Agent H) as the final result
        secretary_output = results.get('H', 'ไม่มีผลลัพธ์จาก Agent H')

        # Discord has 2000 char limit, split if needed
        final_msg = (
            f"\n🎉 **Pipeline เสร็จสิ้น!** Issue #{issue.number}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📨 **Agent H (Secretary) รายงาน:**\n"
            f"{secretary_output[:1500]}"
        )
        await ctx.send(final_msg)

        # Mark as processed on GitHub
        try:
            issue.add_to_labels("processed")
            issue.create_comment(f"✅ Pipeline processed via Discord.\n\n**Secretary Output:**\n{secretary_output[:3000]}")
            issue.edit(state="closed")
        except Exception as e:
            await ctx.send(f"⚠️ ประมวลผลสำเร็จ แต่ไม่สามารถอัปเดต GitHub Issue ได้: {e}")

    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาดระหว่างรัน Pipeline: {e}")

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
        open_issues = list(repo.get_issues(state='open'))
        closed_issues = list(repo.get_issues(state='closed', sort='updated', direction='desc'))[:5]

        msg = "📋 **Sovereign AI — Task Queue Status**\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

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

# ─── Entry Point ──────────────────────────────────────────────

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN is missing in .env")
    else:
        bot.run(DISCORD_TOKEN)
