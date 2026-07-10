import os
import asyncio
from datetime import datetime, time as dtime
from pytz import timezone
from hijri_converter import Gregorian
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq
from pypdf import PdfReader

# الإعدادات البيئية
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROQ_KEY = os.getenv("GROQ_API_KEY")
LOCAL_TZ = timezone("Asia/Riyadh")

ai_client = Groq(api_key=GROQ_KEY)

# ─────────────────────────────────────────────
# أدوات مساعدة
# ─────────────────────────────────────────────

def get_hijri_date():
    now_local = datetime.now(LOCAL_TZ)
    hijri = Gregorian(now_local.year, now_local.month, now_local.day).to_hijri()
    months = ["محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة",
              "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]
    return f"📅 {hijri.day} {months[hijri.month - 1]} {hijri.year} هـ"

def footer():
    return "\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها."

# ─────────────────────────────────────────────
# إدارة صفحات الـ PDF (متزامن – يُستدعى عبر to_thread)
# ─────────────────────────────────────────────

def get_and_update_next_page():
    page_file = "current_page.txt"
    try:
        with open(page_file, "r") as f:
            current_page = int(f.read().strip())
    except Exception:
        current_page = 0
    with open(page_file, "w") as f:
        f.write(str(current_page + 1))
    return current_page

def _sync_extract_and_fix_pdf(page_num):
    pdf_path = "magazine.pdf"
    if not os.path.exists(pdf_path):
        return "⚠️ تنبيه: يرجى رفع ملف المجلة باسم magazine.pdf إلى المستودع."
    reader = PdfReader(pdf_path)
    if page_num >= len(reader.pages):
        with open("current_page.txt", "w") as f:
            f.write("1")
        page_num = 0
    raw_text = reader.pages[page_num].extract_text()
    if not raw_text or len(raw_text.strip()) < 10:
        return "📖 صفحة تحتوي على صور أو تصاميم، تأملوا فيها يا رعاكم الله."
    completion = ai_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content":
                "أنت خبير تدقيق لغوي وشرعي إسلامي. أمامك نص مستخرج من صفحة مجلة إسلامية أندلسية. "
                "قم بإعادة تجميع الكلمات المكسورة وصياغتها بلغة فصيحة بليغة جداً ومتناسقة."},
            {"role": "user", "content": raw_text}
        ],
        temperature=0.3
    )
    return completion.choices[0].message.content

async def extract_and_fix_pdf_text(page_num):
    return await asyncio.to_thread(_sync_extract_and_fix_pdf, page_num)

# ─────────────────────────────────────────────
# توليد المحتوى عبر الذكاء الاصطناعي (متزامن – يُستدعى عبر to_thread)
# ─────────────────────────────────────────────

PROMPTS = {
    "azkar_sabah":   "اكتب منشوراً صباحياً قصيراً يحتوي على أحد أذكار الصباح وفضلها بنبرة إيمانية دافئة.",
    "stories_sabah": "اكتب قصة إسلامية وعبرة مأثورة ملهمة وقصيرة جداً، واختمها بـ (العبرة من القصة:).",
    "azkar_masa":    "اكتب منشوراً مسائياً قصيراً ومؤثراً يحتوي على أحد أذكار المساء المأثورة وفضلها.",
    "stories_masa":  "اكتب قصة ملهمة قصيرة جداً من التراث الجزائري القديم والصالحين في المغرب الأوسط والأندلس مليئة بالعبر والمواعظ.",
    "jihad":
        "اكتب منشوراً إسلامياً دعوياً قصيراً ومؤثراً جداً بالفصحى. "
        "يركز على: مواعظ إيمانية، أهمية الجهاد وعقيدة الولاء والبراء، "
        "ومراغمة الكفار في جزيرة العرب، والدعاء للمجاهدين في كل ثغور المسلمين."
}

def _sync_generate(prompt_type):
    completion = ai_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": PROMPTS[prompt_type]}],
        temperature=0.7
    )
    return completion.choices[0].message.content

async def generate_content(prompt_type):
    return await asyncio.to_thread(_sync_generate, prompt_type)

def _sync_fiqh_reply(user_name, user_text):
    completion = ai_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content":
                "أنت مساعد إسلامي فقيه، ترد على أسئلة المسلمين بأدب وفق الكتاب والسنة بفهم سلف الأمة. "
                "يجب أن تبدأ ردك دائماً بعبارة حافلة مثل: 'نعم أخي الموحد البطل' أو 'نعم أختي الموحدة العفيفة'."},
            {"role": "user", "content": f"السائل: {user_name}، السؤال: {user_text}"}
        ],
        temperature=0.5
    )
    return completion.choices[0].message.content

# ─────────────────────────────────────────────
# دوال الإرسال للقناة
# ─────────────────────────────────────────────

async def send_daily_post(bot: Bot, prompt_type: str, label: str):
    try:
        print(f"📤 {label}...")
        text = await generate_content(prompt_type)
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"{get_hijri_date()}\n\n{text}{footer()}",
            parse_mode="Markdown"
        )
        print(f"✅ تم النشر: {label}")
    except Exception as e:
        print(f"❌ خطأ في النشر ({label}): {e}")

async def send_magazine_page(bot: Bot, period_name: str):
    try:
        print(f"📤 مجلة {period_name}...")
        page_num = get_and_update_next_page()
        fixed_text = await extract_and_fix_pdf_text(page_num)
        if fixed_text:
            msg = (
                f"{get_hijri_date()}\n\n"
                f"📖 **من صفحات مجلتكم ({period_name})**\n"
                f"📄 **الصفحة: {page_num + 1}**\n\n"
                f"{fixed_text}{footer()}"
            )
            await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown")
        print(f"✅ تم نشر مجلة {period_name}")
    except Exception as e:
        print(f"❌ خطأ في نشر المجلة ({period_name}): {e}")

# ─────────────────────────────────────────────
# وظائف JobQueue (callbacks)
# ─────────────────────────────────────────────

async def job_azkar_sabah(context: ContextTypes.DEFAULT_TYPE):
    await send_daily_post(context.bot, "azkar_sabah", "أذكار الصباح")

async def job_magazine_sabah(context: ContextTypes.DEFAULT_TYPE):
    await send_magazine_page(context.bot, "الصباحية من الـ PDF")

async def job_stories_sabah(context: ContextTypes.DEFAULT_TYPE):
    await send_daily_post(context.bot, "stories_sabah", "قصة الظهر")

async def job_azkar_masa(context: ContextTypes.DEFAULT_TYPE):
    await send_daily_post(context.bot, "azkar_masa", "أذكار المساء")

async def job_magazine_masa(context: ContextTypes.DEFAULT_TYPE):
    await send_magazine_page(context.bot, "المسائية من الـ PDF")

async def job_stories_masa(context: ContextTypes.DEFAULT_TYPE):
    await send_daily_post(context.bot, "stories_masa", "قصة الليل")

async def job_jihad_periodic(context: ContextTypes.DEFAULT_TYPE):
    await send_daily_post(context.bot, "jihad", "المنشور الدوري الجهادي")

# ─────────────────────────────────────────────
# الرسالة التعريفية عند الإقلاع
# ─────────────────────────────────────────────

async def send_welcome_intro(bot: Bot):
    intro_text = (
        "📣 **مرحباً بكم في قناة رَيْحَانَةُ المَغْرِبِ الأَوْسَطِ الأَنْدَلُسِيَّة** 📣\n\n"
        "يسرنا أن نعلن لكم عن تفعيل **نظام الذكاء الاصطناعي الإسلامي** لإدارة ونشر محتوى القناة تلقائياً على مدار 24 ساعة بجدول منظم كالتالي:\n\n"
        "⏰ **المحتوى اليومي الثابت:**\n"
        "☀️ **06:00 صباحاً:** أذكار الصباح المأثورة وبث الطمأنينة.\n"
        "📖 **08:00 صباحاً:** مجلة القناة (النسخة الصباحية) من الـ PDF.\n"
        "📜 **12:00 ظهراً:** قصة صباحية وعبرة ملهمة.\n"
        "🌙 **05:00 مساءً:** أذكار المساء لحفظكم وتحصينكم.\n"
        "📄 **09:30 مساءً:** مجلة القناة (النسخة المسائية) من الـ PDF.\n"
        "🌌 **10:30 مساءً:** قصة مسائية وتراث دزيري أندلسي.\n\n"
        "⚡ **المحتوى الدوري المتجدد:**\n"
        "🔄 **كل نصف ساعة بدون توقف:** مواعظ إيمانية مكثفة، منشورات عن عقيدة الولاء والبراء، "
        "ومراغمة الكفار، ودعاء مستمر للمجاهدين الأبطال في كل بقاع الأرض وثغور المسلمين.\n\n"
        "💬 **ميزة التفاعل الفوري:**\n"
        "يمكنكم طرح أسئلتكم الشرعية في التعليقات وسيقوم البوت بالرد الفقهي الفوري!\n\n"
        "نسأل الله الثبات والنصر والقبول 🤲🌱"
        f"{footer()}"
    )
    try:
        sent = await bot.send_message(chat_id=CHANNEL_ID, text=intro_text, parse_mode="Markdown")
        await bot.pin_chat_message(chat_id=CHANNEL_ID, message_id=sent.message_id)
        print("✅ تم إرسال وتثبيت الرسالة التعريفية!")
    except Exception as e:
        print(f"خطأ في الرسالة التعريفية: {e}")

# ─────────────────────────────────────────────
# الرد الفقهي على التعليقات
# ─────────────────────────────────────────────

async def reply_to_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or update.message.from_user.is_bot:
        return
    user_text = update.message.text
    user_name = update.message.from_user.first_name
    try:
        reply = await asyncio.to_thread(_sync_fiqh_reply, user_name, user_text)
        await update.message.reply_text(text=reply, parse_mode="Markdown")
    except Exception as e:
        print(f"خطأ في الرد على التعليق: {e}")

# ─────────────────────────────────────────────
# ما بعد التهيئة: تسجيل الوظائف وإرسال الرسالة
# ─────────────────────────────────────────────

async def post_init(application: Application):
    bot = application.bot
    jq = application.job_queue

    # الوظائف اليومية الثابتة (توقيت مكة = Asia/Riyadh)
    tz = LOCAL_TZ
    jq.run_daily(job_azkar_sabah,   time=dtime(6,  0,  tzinfo=tz), name="azkar_sabah")
    jq.run_daily(job_magazine_sabah,time=dtime(8,  0,  tzinfo=tz), name="magazine_sabah")
    jq.run_daily(job_stories_sabah, time=dtime(12, 0,  tzinfo=tz), name="stories_sabah")
    jq.run_daily(job_azkar_masa,    time=dtime(17, 0,  tzinfo=tz), name="azkar_masa")
    jq.run_daily(job_magazine_masa, time=dtime(21, 30, tzinfo=tz), name="magazine_masa")
    jq.run_daily(job_stories_masa,  time=dtime(22, 30, tzinfo=tz), name="stories_masa")

    # النشر الدوري كل 30 دقيقة
    jq.run_repeating(job_jihad_periodic, interval=1800, first=60, name="jihad_periodic")

    print("✅ تم تسجيل جميع الوظائف في JobQueue.")

    # إرسال الرسالة التعريفية فوراً
    await send_welcome_intro(bot)
    print("✅ البوت جاهز ويعمل.")

# ─────────────────────────────────────────────
# نقطة الانطلاق
# ─────────────────────────────────────────────

def main():
    print("🚀 بدء تشغيل البوت...")
    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to_member))
    print("✅ البوت يستمع للرسائل...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
