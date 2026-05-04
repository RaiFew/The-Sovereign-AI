import discord
import asyncio
import re
from discord.ext import commands, tasks
from github import Github
from dotenv import load_dotenv

from config.settings import DISCORD_TOKEN, GITHUB_TOKEN, GITHUB_REPO
from agents.agent_manager import AgentManager
from agents.knowledge_router import KnowledgeRouter
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
        print(f"Failed to initialize GitHub repo: {e}")

# Initialize Managers
agent_manager = AgentManager()
knowledge_router = KnowledgeRouter()

# ─── Helper: Parse topic/subject from issue ──────────────────

def parse_issue(issue_body: str, issue_title: str) -> tuple:
    """Extract topic and subject from GitHub Issue"""
    # Try parsing from title: [MANGA] Research: Solo Leveling
    title_match = re.match(r'\[(\w+)\]\s*Research:\s*(.+)', issue_title, re.IGNORECASE)
    if title_match:
        return title_match.group(1).lower(), title_match.group(2).strip()

    # Try parsing from body
    topic_match = re.search(r'\*?\*?Topic:\*?\*?\s*(\w+)', issue_body or '', re.IGNORECASE)
    subject_match = re.search(r'\*?\*?Subject:\*?\*?\s*(.+)', issue_body or '', re.IGNORECASE)

    topic = topic_match.group(1).strip() if topic_match else "general"
    subject = subject_match.group(1).strip() if subject_match else issue_title

    return topic.lower(), subject

# ─── Smart Pipeline Logic ─────────────────────────────────────

async def run_smart_pipeline(task_description: str, topic: str, subject: str,
                              status_callback=None) -> dict:
    """
    Smart Router Pipeline:
    1. Check existing knowledge (KnowledgeRouter)
    2. Route to SKIP / DELTA / FULL
    3. Execute only the agents needed
    """
    results = {}
    route_info = knowledge_router.search_existing_knowledge(topic, subject)
    route = route_info["route"]
    lessons = knowledge_router.read_lessons_learned()

    if status_callback:
        await status_callback(f"🧭 Smart Router: ตรวจพบ Route = **{route}**")

    # ──────────────────────────────────────────────────
    # SCENARIO A: SKIP — Data exists & sufficient
    # Short-circuit: A → H → I (skip B-G entirely)
    # ──────────────────────────────────────────────────
    if route == "SKIP":
        if status_callback:
            await status_callback("⚡ SKIP MODE — เจอข้อมูลในคลังแล้ว! ข้ามไปสรุปผลเลย")

        results["_route"] = "SKIP"
        results["_existing_content"] = route_info["content"]

        # Agent A — just confirm the routing
        if status_callback:
            await status_callback("🔍 Agent A (Gatekeeper): ยืนยัน Route SKIP [LOCAL]...")
        prompt_a = (
            f"Task: {task_description}\n\n"
            f"Lessons Learned:\n{lessons}\n\n"
            f"EXISTING DATA FOUND at: {route_info['file_path']}\n"
            f"Content preview:\n{route_info['content'][:2000]}\n\n"
            f"This data is sufficient. Output: ROUTE: SKIP and a brief summary."
        )
        results["A"] = await asyncio.to_thread(
            agent_manager.execute_agent, "A", prompt_a, True, PROMPTS["A"]
        )

        # Agent H — summarize existing content for Discord
        if status_callback:
            await status_callback("📨 Agent H (Secretary): สรุปข้อมูลจากคลัง [CLOUD]...")
        prompt_h = (
            f"Task: {task_description}\n"
            f"ROUTE USED: SKIP (ข้อมูลมีอยู่แล้วในคลัง ไม่ต้องวิจัยใหม่)\n"
            f"File: {route_info['file_path']}\n\n"
            f"Existing content:\n{route_info['content'][:3000]}\n\n"
            f"Summarize this for the user via Discord."
        )
        results["H"] = await asyncio.to_thread(
            agent_manager.execute_agent, "H", prompt_h, False, PROMPTS["H"]
        )

        # Agent I — log the skip
        if status_callback:
            await status_callback("📊 Agent I (Optimizer): บันทึก Log [LOCAL]...")
        prompt_i = (
            f"Pipeline used ROUTE: SKIP. No cloud agents B-G were called.\n"
            f"Topic: {topic}, Subject: {subject}\n"
            f"Estimated tokens saved: ~80% vs full pipeline.\n"
            f"Log this performance."
        )
        results["I"] = await asyncio.to_thread(
            agent_manager.execute_agent, "I", prompt_i, True, PROMPTS["I"]
        )

        return results

    # ──────────────────────────────────────────────────
    # SCENARIO B: DELTA — Data exists but needs update
    # Run: A → B → C → J → D(delta) → E → F → G(incremental) → H → I
    # ──────────────────────────────────────────────────
    elif route == "DELTA":
        if status_callback:
            await status_callback("🔄 DELTA MODE — อัปเดตข้อมูลเดิม เฉพาะส่วนที่ขาด")

        results["_route"] = "DELTA"
        results["_existing_content"] = route_info["content"]
        baseline = route_info["content"]

        steps_delta = [
            ("A", f"Task: {task_description}\nLessons:\n{lessons}\n\nBASELINE exists:\n{baseline[:2000]}\nOutput: ROUTE: DELTA + constraints.",
             "🔍 Agent A (Gatekeeper): Router + Constraints [LOCAL]...", True),

            ("B", None,  # built after A
             "📋 Agent B (Strategist): วางแผนเฉพาะส่วนที่ขาด [CLOUD]...", False),

            ("C", None,
             "🌐 Agent C (Hunter): ค้นหาเฉพาะข้อมูลใหม่ [CLOUD]...", False),

            ("J", None,
             "🗜️ Agent J (Compressor): บีบอัดข้อมูลใหม่ [LOCAL]...", True),

            ("D", None,
             "🧵 Agent D (Weaver): Delta-Merge ข้อมูลเก่า+ใหม่ [CLOUD]...", False),

            ("E", None,
             "⚔️ Agent E (Opponent): ตรวจจับจุดอ่อน [CLOUD]...", False),

            ("F", None,
             "✅ Agent F (Auditor): ตรวจ QA [LOCAL]...", True),

            ("G", None,
             "🏗️ Agent G (Architect): Incremental Write ลง Obsidian [CLOUD]...", False),

            ("H", None,
             "📨 Agent H (Secretary): สรุปผล [CLOUD]...", False),

            ("I", None,
             "📊 Agent I (Optimizer): บันทึก Log [LOCAL]...", True),
        ]

        for agent_key, static_prompt, status_msg, is_local in steps_delta:
            if status_callback:
                await status_callback(f"  ▸ {status_msg}")

            # Build dynamic prompts
            if static_prompt:
                prompt = static_prompt
            elif agent_key == "B":
                prompt = (
                    f"Task: {task_description}\n\nConstraints from Gatekeeper:\n{results.get('A', '')}\n\n"
                    f"BASELINE (existing knowledge — DO NOT re-research this):\n{baseline[:2000]}\n\n"
                    f"Plan research for ONLY the gaps. What's missing or outdated?"
                )
            elif agent_key == "C":
                prompt = f"Research Plan (gap-focused):\n{results.get('B', '')}"
            elif agent_key == "J":
                prompt = f"Raw Data:\n{results.get('C', '')}"
            elif agent_key == "D":
                prompt = (
                    f"MODE: DELTA-MERGE\n\n"
                    f"BASELINE (existing content):\n{baseline[:2000]}\n\n"
                    f"NEW DATA (from research):\n{results.get('J', '')}\n\n"
                    f"Merge new insights into existing structure. Do NOT duplicate."
                )
            elif agent_key == "E":
                prompt = f"Draft to review:\n{results.get('D', '')}"
            elif agent_key == "F":
                prompt = f"Draft:\n{results.get('D', '')}\n\nCritique:\n{results.get('E', '')}\n\nFinalize and ensure formatting + sovereign_metadata."
            elif agent_key == "G":
                prompt = (
                    f"MODE: INCREMENTAL UPDATE\n"
                    f"Existing file: {route_info['file_path']}\n\n"
                    f"Final QA'd Content:\n{results.get('F', '')}\n\n"
                    f"Update the file incrementally. Bump version in sovereign_metadata."
                )
            elif agent_key == "H":
                prompt = f"Task: {task_description}\nROUTE USED: DELTA\nFinal output:\n{results.get('G', '')}"
            elif agent_key == "I":
                prompt = f"Pipeline used ROUTE: DELTA. Baseline existed but was updated.\nTopic: {topic}, Subject: {subject}\nLog performance."

            result = await asyncio.to_thread(
                agent_manager.execute_agent, agent_key, prompt, is_local, PROMPTS[agent_key]
            )
            results[agent_key] = result

        return results

    # ──────────────────────────────────────────────────
    # SCENARIO C: FULL — New topic, no existing data
    # Run: A → B → C → J → D → E → F → G → H → I
    # ──────────────────────────────────────────────────
    else:
        if status_callback:
            await status_callback("🚀 FULL MODE — หัวข้อใหม่ วิจัยเต็มรูปแบบ!")

        results["_route"] = "FULL"

        steps_full = [
            ("A", f"Task: {task_description}\nLessons:\n{lessons}\nNo existing data found. Output: ROUTE: FULL + constraints.",
             "🔍 Agent A (Gatekeeper): Constraints [LOCAL]...", True),
            ("B", None, "📋 Agent B (Strategist): วางแผนวิจัย [CLOUD]...", False),
            ("C", None, "🌐 Agent C (Hunter): ค้นหาข้อมูล [CLOUD]...", False),
            ("J", None, "🗜️ Agent J (Compressor): บีบอัดข้อมูล [LOCAL]...", True),
            ("D", None, "🧵 Agent D (Weaver): แปลและเรียบเรียง [CLOUD]...", False),
            ("E", None, "⚔️ Agent E (Opponent): ตรวจจับจุดอ่อน [CLOUD]...", False),
            ("F", None, "✅ Agent F (Auditor): ตรวจ QA [LOCAL]...", True),
            ("G", None, "🏗️ Agent G (Architect): เขียนลง Obsidian [CLOUD]...", False),
            ("H", None, "📨 Agent H (Secretary): สรุปผล [CLOUD]...", False),
            ("I", None, "📊 Agent I (Optimizer): บันทึก Log [LOCAL]...", True),
        ]

        for agent_key, static_prompt, status_msg, is_local in steps_full:
            if status_callback:
                await status_callback(f"  ▸ {status_msg}")

            if static_prompt:
                prompt = static_prompt
            elif agent_key == "B":
                prompt = f"Task: {task_description}\n\nConstraints from Gatekeeper:\n{results.get('A', '')}"
            elif agent_key == "C":
                prompt = f"Research Plan:\n{results.get('B', '')}"
            elif agent_key == "J":
                prompt = f"Raw Data:\n{results.get('C', '')}"
            elif agent_key == "D":
                prompt = f"MODE: FULL (New research)\n\nCompressed Data:\n{results.get('J', '')}"
            elif agent_key == "E":
                prompt = f"Draft to review:\n{results.get('D', '')}"
            elif agent_key == "F":
                prompt = f"Draft:\n{results.get('D', '')}\n\nCritique:\n{results.get('E', '')}\n\nFinalize + ensure sovereign_metadata JSON block."
            elif agent_key == "G":
                prompt = (
                    f"MODE: NEW FILE\n"
                    f"Topic: {topic}, Subject: {subject}\n"
                    f"Target folder: 01_Research/{topic.capitalize()}/\n\n"
                    f"Final QA'd Content:\n{results.get('F', '')}"
                )
            elif agent_key == "H":
                prompt = f"Task: {task_description}\nROUTE USED: FULL (วิจัยใหม่ทั้งหมด)\nFinal output:\n{results.get('G', '')}"
            elif agent_key == "I":
                prompt = f"Pipeline used ROUTE: FULL. New research from scratch.\nTopic: {topic}, Subject: {subject}\nLog performance."

            result = await asyncio.to_thread(
                agent_manager.execute_agent, agent_key, prompt, is_local, PROMPTS[agent_key]
            )
            results[agent_key] = result

        return results

# ─── Bot Events ───────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('─' * 50)
    print('🧭 Smart Router Protocol ENABLED')
    print('Commands available:')
    print('  /ping                         - ทดสอบบอท')
    print('  /research <topic> <subject>   - สั่งวิจัย')
    print('  /run                          - รัน Pipeline')
    print('  /queue                        - ดูสถานะคิว')
    print('─' * 50)
    if not repo:
        print("⚠️ WARNING: GitHub credentials not configured.")

# ─── Commands ─────────────────────────────────────────────────

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('🏓 Pong! Sovereign AI Bot is active.\n🧭 Smart Router Protocol: **ENABLED**')

@bot.command(name='research')
async def research(ctx, topic: str, *, subject: str):
    """
    สั่งงานวิจัย — สร้าง GitHub Issue เข้าคิว
    Usage: /research manga Solo Leveling
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

        # Quick preview of Smart Router decision
        route_info = knowledge_router.search_existing_knowledge(topic, subject)
        route_preview = {
            "SKIP": "⚡ เจอข้อมูลในคลังแล้ว — จะข้ามวิจัยใหม่",
            "DELTA": "🔄 เจอข้อมูลเดิม — จะอัปเดตเฉพาะส่วนที่ขาด",
            "FULL": "🚀 หัวข้อใหม่ — จะวิจัยเต็มรูปแบบ"
        }

        await ctx.send(
            f"✅ **สั่งงานสำเร็จ!** Issue #{issue.number}\n"
            f"📌 `{title}`\n"
            f"🧭 Smart Router Preview: {route_preview.get(route_info['route'], 'FULL')}\n"
            f"▸ ใช้ `/run` เพื่อเริ่มประมวลผล"
        )
    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")

@bot.command(name='run')
async def run(ctx):
    """ดึง Issue แล้วรัน Smart Pipeline"""
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

        issue = pending[-1]  # oldest first
        topic, subject = parse_issue(issue.body or '', issue.title)

        await ctx.send(
            f"⚡ **เริ่มประมวลผล Smart Pipeline!**\n"
            f"📌 Issue #{issue.number} — {issue.title}\n"
            f"📂 Topic: `{topic}` | Subject: `{subject}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        async def send_status(msg):
            await ctx.send(msg)

        # Run Smart Pipeline
        task_description = issue.body or issue.title
        results = await run_smart_pipeline(task_description, topic, subject, status_callback=send_status)

        # Get route used and secretary output
        route_used = results.get("_route", "FULL")
        secretary_output = results.get('H', 'ไม่มีผลลัพธ์จาก Agent H')

        route_emoji = {"SKIP": "⚡", "DELTA": "🔄", "FULL": "🚀"}.get(route_used, "🚀")

        final_msg = (
            f"\n🎉 **Pipeline เสร็จสิ้น!** Issue #{issue.number}\n"
            f"{route_emoji} Route ที่ใช้: **{route_used}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📨 **Agent H (Secretary) รายงาน:**\n"
            f"{secretary_output[:1500]}"
        )
        await ctx.send(final_msg)

        # Mark as processed on GitHub
        try:
            issue.add_to_labels("processed")
            issue.create_comment(
                f"✅ Pipeline processed via Discord.\n"
                f"Route: {route_used}\n\n"
                f"**Secretary Output:**\n{secretary_output[:3000]}"
            )
            issue.edit(state="closed")
        except Exception as e:
            await ctx.send(f"⚠️ ประมวลผลสำเร็จ แต่ไม่สามารถอัปเดต GitHub Issue ได้: {e}")

    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาดระหว่างรัน Pipeline: {e}")

@bot.command(name='queue')
async def queue(ctx):
    """แสดงสถานะคิวงานทั้งหมดจาก GitHub Issues"""
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
                topic, subject = parse_issue(issue.body or '', issue.title)
                route_info = knowledge_router.search_existing_knowledge(topic, subject)
                route_tag = {"SKIP": "⚡SKIP", "DELTA": "🔄DELTA", "FULL": "🚀FULL"}.get(route_info["route"], "FULL")
                msg += f"  `{i}.` #{issue.number} — {issue.title} [{route_tag}]\n"
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
