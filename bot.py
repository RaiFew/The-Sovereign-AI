import discord
import asyncio
import re
import json
import requests
from discord.ext import commands
from github import Github
from dotenv import load_dotenv

from config.settings import DISCORD_TOKEN, GITHUB_TOKEN, GITHUB_REPO, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OLLAMA_BASE_URL
from agents.agent_manager import AgentManager
from agents.commander import Commander

load_dotenv()

# Initialize Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)

# Initialize GitHub
gh = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
repo = None
if gh and GITHUB_REPO:
    try:
        repo = gh.get_repo(GITHUB_REPO)
    except Exception as e:
        print(f"Failed to initialize GitHub repo: {e}")

# Initialize Core
agent_manager = AgentManager()
commander = Commander(agent_manager)

def parse_issue(issue_body: str, issue_title: str) -> tuple:
    """Extract topic and subject from GitHub Issue"""
    title_match = re.match(r'\[(\w+)\]\s*Research:\s*(.+)', issue_title, re.IGNORECASE)
    if title_match:
        return title_match.group(1).lower(), title_match.group(2).strip()

    topic_match = re.search(r'\*?\*?Topic:\*?\*?\s*(\w+)', issue_body or '', re.IGNORECASE)
    subject_match = re.search(r'\*?\*?Subject:\*?\*?\s*(.+)', issue_body or '', re.IGNORECASE)
    
    topic = topic_match.group(1).strip() if topic_match else "general"
    subject = subject_match.group(1).strip() if subject_match else issue_title
    return topic.lower(), subject

# ─── Commands ─────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('─' * 50)
    print('👑 Sovereign AI — COMMANDER MODE (Agent K) ONLINE')
    print('🧭 Model: OpenRouter (tencent/hy3-preview:free)')
    print('─' * 50)

@bot.command(name='help')
async def custom_help(ctx):
    embed = discord.Embed(
        title="🏛️ The Sovereign AI — Commander Guide",
        description="ระบบ Multi-Agent อัจฉริยะที่รันอยู่บน **Free Tier Only**",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="🛠️ ระบบใหม่ (V3)",
        value=(
            "• **Local First**: ตรวจไฟล์ในเครื่องก่อนส่ง Cloud เพื่อลด Token\n"
            "• **OpenRouter**: ใช้โมเดล tencent/hy3-preview:free\n"
            "• **Auto-Triage**: Agent K จะวางแผนงานตามผลการตรวจไฟล์อัตโนมัติ"
        ),
        inline=False
    )
    embed.add_field(
        name="🚀 Commands",
        value="`/research` สั่งงาน | `/run` เริ่มประมวลผล | `/queue` ดูคิว",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command(name='research')
async def research(ctx, topic: str, *, subject: str):
    if not repo: return
    try:
        title = f"[{topic.upper()}] Research: {subject}"
        body = f"**Topic:** {topic}\n**Subject:** {subject}\nUser: {ctx.author.name}"
        issue = repo.create_issue(title=title, body=body, labels=["task"])
        await ctx.send(f"✅ Issue #{issue.number} created. พิมพ์ `/run` เพื่อเริ่มประมวลผล")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command(name='run')
async def run(ctx):
    if not repo: return
    await ctx.send("🔄 **Commander K กำลังเริ่มประมวลผล...**")

    try:
        open_issues = list(repo.get_issues(state='open'))
        pending = [i for i in open_issues if 'processed' not in [l.name for l in i.labels]]

        if not pending:
            await ctx.send("📭 ไม่มีงานค้างในคิว")
            return

        issue = pending[-1]
        topic, subject = parse_issue(issue.body or '', issue.title)
        
        async def send_status(msg):
            await ctx.send(msg)

        # 👑 Start Orchestration via Agent K
        results = await asyncio.to_thread(
            commander.process_task, 
            issue.body or issue.title, 
            topic=topic,
            subject=subject,
            status_callback=lambda m: asyncio.run_coroutine_threadsafe(send_status(m), bot.loop)
        )

        final_report = results.get("H", "งานเสร็จสิ้น แต่ไม่พบสรุปจาก Agent H")
        await ctx.send(f"🎉 **Mission Complete!**\n━━━━━━━━━━━━━━━━━━━━\n{final_report[:1900]}")
        
        issue.add_to_labels("processed")
        issue.edit(state="closed")

    except Exception as e:
        await ctx.send(f"❌ Critical Error: {e}")

@bot.command(name='queue')
async def queue(ctx):
    if not repo: return
    open_issues = list(repo.get_issues(state='open'))
    pending = [i for i in open_issues if 'processed' not in [l.name for l in i.labels]]
    
    msg = "📋 **Task Queue:**\n" + "\n".join([f"• #{i.number} - {i.title}" for i in pending]) if pending else "📭 ว่างเปล่า"
    await ctx.send(msg)

@bot.command(name='ping')
async def ping(ctx):
    status = "🖥️ Local Agents (Ollama) ONLINE" if agent_manager.ollama_available else "☁️ Cloud Only (Ollama OFFLINE)"
    await ctx.send(f'🏓 Pong! Agent K is online.\nStatus: {status}')

@bot.command(name='test')
async def test(ctx):
    """Test all connections: Discord, OpenRouter, Ollama, GitHub"""
    msg = await ctx.send("🔧 **กำลังตรวจสอบการเชื่อมต่อ...**")
    results = ["✅ **Discord Bot**: ONLINE"]

    # Test OpenRouter API
    try:
        if not OPENROUTER_API_KEY:
            results.append("❌ **OpenRouter API**: API Key ไม่ได้ตั้งค่า")
        else:
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
            def check_openrouter():
                return requests.get(f"{OPENROUTER_BASE_URL}/models", headers=headers, timeout=10)
            response = await asyncio.to_thread(check_openrouter)
            if response.status_code == 200:
                results.append("✅ **OpenRouter API**: CONNECTED (tencent/hy3-preview:free)")
            else:
                results.append(f"❌ **OpenRouter API**: Error {response.status_code}")
    except Exception as e:
        results.append(f"❌ **OpenRouter API**: {str(e)[:100]}")

    # Test Ollama Local
    try:
        def check_ollama():
            return requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response = await asyncio.to_thread(check_ollama)
        if response.status_code == 200:
            models = response.json().get("models", [])
            gemma_available = any("gemma4" in m.get("name", "") for m in models)
            if gemma_available:
                results.append("✅ **Ollama Local**: CONNECTED (gemma4:26b ready)")
            else:
                results.append("⚠️ **Ollama Local**: CONNECTED but gemma4:26b not found (run: ollama pull gemma4:26b)")
        else:
            results.append(f"❌ **Ollama Local**: Error {response.status_code}")
    except Exception as e:
        results.append(f"❌ **Ollama Local**: OFFLINE - {str(e)[:100]}")

    # Test GitHub
    if not repo:
        results.append("❌ **GitHub**: ไม่ได้ตั้งค่า Token หรือ Repository")
    else:
        try:
            results.append(f"✅ **GitHub**: CONNECTED ({repo.full_name})")
        except Exception as e:
            results.append(f"❌ **GitHub**: {str(e)[:100]}")

    # Send results
    all_ok = all("✅" in r for r in results)
    color = discord.Color.green() if all_ok else discord.Color.orange()
    result_embed = discord.Embed(
        title="🔧 ผลการตรวจสอบการเชื่อมต่อ",
        description="\n\n".join(results),
        color=color
    )
    await msg.edit(content=None, embed=result_embed)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
