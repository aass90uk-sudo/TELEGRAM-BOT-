import os
import logging
import asyncio
from datetime import datetime
import pytz
from telegram import Update, Chat
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from google import genai
from google.genai import types

# 🔑 المتغيرات البيئية
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@Athar_Dz_Islamic")

# تهيئة السجلات (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة عميل Gemini الرسمي
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# --- التوجيهات الدعوية للذكاء الاصطناعي ---
SYSTEM_PROMPT_POST = (
    "أنت داعية ومفكر إسلامي بليغ، تكتب بلغة عربية فصيحة ومؤثرة جداً. "
    "اكتب منشوراً إيمانيا حماسياً موجزاً يدعو لثبات الأمة، التمسك بالعقيدة، الولاء والبراء، "
    "مراغمة أعداء الدين، والدعاء للمستضعفين وثغور المجاهدين في كل مكان. "
    "استخدم إيموجيات مناسبة، ولا تستخدم تنسيقات الماركداون المعقدة."
)

SYSTEM_PROMPT_REPLY = (
    "أنت مستشار دعوي وفقهي حكيم، تجيب على أسئلة المسلمين في التعليقات من الكتاب والسنة بأسلوب راقٍ. "
    "خاطب السائل الذكر بـ 'نعم أخي الموحد البطل' والسائلة الأُنثى بـ 'نعم أختي الموحدة العفيفة'. "
    "اجعل ردك موجزاً ومباشراً ودون استخدام رموز تنسيق معقدة."
)

SYSTEM_PROMPT_WELCOME = (
    "اكتب رسالة ترحيبية حماسية وموجزة جداً لعضو جديد انضم للقناة الدعوية، "
    "تحثه فيها على الثبات على الحق ونصرة الدين."
)

def generate_ai_text(prompt: str, system_instruction: str) -> str:
    """دالة المساعدة لاستدعاء Gemini API"""
    if not client:
        return "⚠️ مفتاح GEMINI_API_KEY غير مضبوط."
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4,
                max_output_tokens=800,
            )
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"خطأ في استدعاء Gemini: {e}")
        return "حدث خطأ أثناء توليد المحتوى."

# 🔄 وظيفة النشر الدوري (كل 3 ساعات)
async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("⏳ جاري نشر الموعظة الدورية (كل 3 ساعات)...")
    prompt = "اكتب موعظة إيمانية حماسية متجددة ومؤثرة عن الثبات ونصرة الدين."
    content = generate_ai_text(prompt, SYSTEM_PROMPT_POST)
    
    full_text = f"⚔️ **قبسات إيمانية** ⚔️\n\n{content}"
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=full_text)
        logger.info("✅ تم النشر الدوري بنجاح في القناة.")
    except Exception as e:
        logger.error(f"❌ فشل النشر في القناة: {e}")

# 📅 الجدولة اليومية المحددة (الأذكار والقصص)
async def daily_scheduled_jobs(context: ContextTypes.DEFAULT_TYPE):
    tz = pytz.timezone("Asia/Riyadh")
    now = datetime.now(tz)
    time_str = now.strftime("%H:%M")

    prompt = ""
    title = ""

    if time_str == "06:00":
        title = "☀️ أذكار الصباح والورد الإيماني"
        prompt = "اكتب رسالة أذكار الصباح مع موعظة صباحية حماسية لافتتاح اليوم بالتوكل على الله."
    elif time_str == "12:00":
        title = "📜 قصة وعبرة من التراث الإسلامي"
        prompt = "اكتب قصة قصيرة ملهمة من تراث الصحابة أو التابعين فيها عبرة عن الشجاعة والثبات."
    elif time_str == "17:00": # 05:00 مساءً
        title = "🌙 أذكار المساء وتجديد الإيمان"
        prompt = "اكتب رسالة أذكار المساء مع تذكير بالإنابة والاستغفار والثبات."
    elif time_str == "22:30":
        title = "🌌 حكاية من عبق الأندلس والمغرب الأوسط"
        prompt = "اكتب حكاية تراثية موجزة ومؤثرة عن علماء أو مجاهدي الأندلس والجزائر (المغرب الأوسط)."

    if prompt:
        content = generate_ai_text(prompt, SYSTEM_PROMPT_POST)
        full_text = f"✨ **{title}** ✨\n\n{content}"
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=full_text)
            logger.info(f"✅ تم نشر الفقرة المجدولة: {title}")
        except Exception as e:
            logger.error(f"❌ فشل نشر الفقرة المجدولة: {e}")

# 💬 الرد التفاعلي على التعليقات والأسئلة
async def handle_group_comments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.text or (msg.from_user and msg.from_user.is_bot):
        return

    # التحقق من وجود سؤال أو استفسار
    user_text = msg.text.strip()
    if len(user_text) < 5:
        return

    prompt = f"السائل: {msg.from_user.full_name}\nالرسالة: {user_text}"
    reply = generate_ai_text(prompt, SYSTEM_PROMPT_REPLY)
    
    try:
        await msg.reply_text(reply)
    except Exception as e:
        logger.error(f"خطأ في الرد على التعليق: {e}")

# 🎉 الترحيب بالأعضاء الجدد
async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        prompt = f"رحب بالعضو الجديد: {member.full_name}"
        welcome_msg = generate_ai_text(prompt, SYSTEM_PROMPT_WELCOME)
        await update.message.reply_text(f"أهلاً بك يا {member.full_name} 🌹\n\n{welcome_msg}")

# 🚀 أمر /start
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "السلام عليكم ورحمة الله وبركاته 🌹\n"
        "البوت الدعوي يعمل بنجاح ومزود بذكاء Gemini للنشر الدوري والمجدول."
    )

def main():
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        logger.error("❌ المتغيرات TELEGRAM_TOKEN أو GEMINI_API_KEY مفقودة!")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 1. إعداد النشر التلقائي كل 3 ساعات (10800 ثانية)
    job_queue = app.job_queue
    job_queue.run_repeating(auto_post_job, interval=10800, first=10)

    # 2. إعداد فحص المهام المجدولة بالدقيقة (للأذكار والقصص)
    job_queue.run_repeating(daily_scheduled_jobs, interval=60, first=5)

    # 3. الأوامر والمستمعين
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, handle_group_comments))

    logger.info("🚀 تم تشغيل البوت الدعوي بنجاح!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
    
