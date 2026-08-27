import os
import asyncio
from datetime import datetime, time as dtime
from pytz import timezone
from hijri_converter import Gregorian
from google import genai
from google.genai import types
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# الإعدادات البيئية
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
LOCAL_TZ = timezone("Asia/Riyadh")

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
# توليد المحتوى عبر Gemini (متزامن – يُستدعى عبر to_thread)
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

def _gemini_chat(prompt_text, system_instruction=None):
    if not GEMINI_KEY:
        raise RuntimeError("المتغير GEMINI_API_KEY غير مضبوط.")

    try:
        client = genai.Client(api_key=GEMINI_KEY)
        config = types.GenerateContentConfig(
            temperature=0.8,
            max_output_tokens=1200,
        )
        if system_instruction:
            config.system_instruction = system_instruction
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt_text,
            config=config,
        )
        text = (response.text or "").strip()
    except Exception as error:
        raise RuntimeError(f"فشل Gemini: {error}") from error

    if not text:
        raise RuntimeError("أعاد Gemini نصاً فارغاً.")
    return text

def _sync_generate(prompt_text):
    return _gemini_chat(prompt_text)

async def generate_content(prompt_type):
    return await asyncio.to_thread(_sync_generate, PROMPTS[prompt_type])

def _sync_fiqh_reply(user_name, user_text):
    system_instruction = (
        "أنت عالم ديني ربّاني وكاتب إيماني بليغ، ترد على أسئلة المسلمين بأدب وفق الكتاب والسنة بفهم سلف الأمة. "
        "يجب أن تبدأ ردك دائماً بعبارة حافلة مثل: 'نعم أخي الموحد البطل' أو 'نعم أختي الموحدة العفيفة'."
        "اكتب تعليقاً مفصلاً وشاملاً، على أن يتراوح طوله بين 1024 إلى 1100 حرف ولا يقل عن ذلك."    
    )
    full_prompt = f"{system_instruction}\n\nالسائل: {user_name}، السؤال: {user_text}"
    return _gemini_chat(full_prompt)

# ─────────────────────────────────────────────
# دوال الإرسال للقناة
# ─────────────────────────────────────────────

async def send_daily_post(bot: Bot, prompt_type: str, label: str):
    try:
        print(f"📤 {label}...")
        text = await generate_content(prompt_type)
        post_text = f"{get_hijri_date()}\n\n{text}{footer()}"
        try:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=post_text,
                parse_mode="Markdown",
            )
        except BadRequest as error:
            print(f"⚠️ تعذر تنسيق منشور {label} بـ Markdown، سيتم إرساله كنص عادي: {error}")
            await bot.send_message(chat_id=CHANNEL_ID, text=post_text)
        print(f"✅ تم النشر: {label}")
    except Exception as e:
        print(f"❌ خطأ في النشر ({label}): {e}")

# ─────────────────────────────────────────────
# وظائف JobQueue (callbacks)
# ─────────────────────────────────────────────

async def job_azkar_sabah(context: ContextTypes.DEFAULT_TYPE):
    await send_daily_post(context.bot, "azkar_sabah", "أذكار الصباح")

async def job_stories_sabah(context: ContextTypes.DEFAULT_TYPE):
    await send_daily_post(context.bot, "stories_sabah", "قصة الظهر")

async def job_azkar_masa(context: ContextTypes.DEFAULT_TYPE):
    await send_daily_post(context.bot, "azkar_masa", "أذكار المساء")

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
        "📜 **12:00 ظهراً:** قصة صباحية وعبرة ملهمة.\n"
        "🌙 **05:00 مساءً:** أذكار المساء لحفظكم وتحصينكم.\n"
        "🌌 **10:30 مساءً:** قصة مسائية وتراث دزيري أندلسي.\n\n"
        "⚡ **المحتوى الدوري المتجدد:**\n"
        "🔄 **كل 3 ساعات بدون توقف:** مواعظ إيمانية مكثفة، منشورات عن عقيدة الولاء والبراء، "
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
    message = update.effective_message
    if not message or not message.text or not message.from_user or message.from_user.is_bot:
        return
    print(f"📩 رسالة مجموعة واردة من chat_id={message.chat_id} message_id={message.message_id}")
    user_text = message.text
    user_name = message.from_user.first_name
    try:
        reply = await asyncio.to_thread(_sync_fiqh_reply, user_name, user_text)
        try:
            await message.reply_text(text=reply, parse_mode="Markdown")
        except BadRequest as error:
            print(f"⚠️ تعذر تنسيق الرد بـ Markdown، سيتم إرساله كنص عادي: {error}")
            await message.reply_text(text=reply)
    except Exception as e:
        print(f"خطأ في الرد على التعليق: {e}")

# ─────────────────────────────────────────────
# ما بعد التهيئة: تسجيل الوظائف وإرسال الرسالة
# ─────────────────────────────────────────────

async def post_init(application: Application):
    bot = application.bot
    jq = application.job_queue

    try:
        bot_info = await bot.get_me()
        channel = await bot.get_chat(CHANNEL_ID)
        channel_member = await bot.get_chat_member(channel.id, bot_info.id)
        print(
            f"✅ Telegram متصل: @{bot_info.username} | "
            f"القناة: {channel.title or channel.id} | "
            f"حالة البوت: {channel_member.status}"
        )
    except Exception as error:
        print(f"⚠️ تعذر التحقق من اتصال Telegram أو صلاحيات القناة: {error}")

    # الوظائف اليومية الثابتة (توقيت مكة = Asia/Riyadh)
    tz = LOCAL_TZ
    jq.run_daily(job_azkar_sabah,   time=dtime(6,  0,  tzinfo=tz), name="azkar_sabah")
    jq.run_daily(job_stories_sabah, time=dtime(12, 0,  tzinfo=tz), name="stories_sabah")
    jq.run_daily(job_azkar_masa,    time=dtime(17, 0,  tzinfo=tz), name="azkar_masa")
    jq.run_daily(job_stories_masa,  time=dtime(22, 30, tzinfo=tz), name="stories_masa")

    # النشر الدوري كل 3 ساعات
    jq.run_repeating(job_jihad_periodic, interval=10800, first=60, name="jihad_periodic")

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
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
            reply_to_member,
        )
    )
    print("✅ البوت يستمع للرسائل...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
                          
