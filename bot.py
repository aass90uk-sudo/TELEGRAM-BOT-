import os
import asyncio
from datetime import datetime, time
from pytz import timezone
from hijridate import Gregorian
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq
from pypdf import PdfReader

# الإعدادات البيئية
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROQ_KEY = os.getenv("GROQ_API_KEY")
LOCAL_TZ = timezone("Asia/Riyadh")

ai_client = Groq(api_key=GROQ_KEY)

def get_hijri_date():
    now_local = datetime.now(LOCAL_TZ)
    hijri = Gregorian(now_local.year, now_local.month, now_local.day).to_hijri()
    months = ["محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة", "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]
    return f"📅 {hijri.day} {months[hijri.month - 1]} {hijri.year} هـ"

# إدارة صفحات الـ PDF
def get_and_update_next_page():
    page_file = "current_page.txt"
    if os.path.exists(page_file):
        with open(page_file, "r") as f:
            try: current_page = int(f.read().strip())
            except: current_page = 0
    else:
        current_page = 0
    with open(page_file, "w") as f:
        f.write(str(current_page + 1))
    return current_page

# استخراج وإصلاح نصوص الـ PDF
def extract_and_fix_pdf_text(page_num):
    pdf_path = "magazine.pdf"
    if not os.path.exists(pdf_path):
        return "⚠️ تنبيه: يرجى رفع ملف المجلة باسم magazine.pdf إلى المستودع."
    try:
        reader = PdfReader(pdf_path)
        if page_num >= len(reader.pages):
            with open("current_page.txt", "w") as f: f.write("1")
            page_num = 0
        page = reader.pages[page_num]
        raw_text = page.extract_text()
        if not raw_text or len(raw_text.strip()) < 10:
            return "📖 صفحة تحتوي على صور أو تصاميم، تأملوا فيها يا رعاكم الله."
        
        system_prompt = (
            "أنت خبير تدقيق لغوي وشرعي إسلامي. أمامك نص مستخرج من صفحة مجلة إسلامية أندلسية. "
            "قم بإعادة تجميع الكلمات المكسورة وصياغتها بلغة فصيحة بليغة جداً ومتناسقة."
        )
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}],
            temperature=0.3
        )
        return completion.choices.message.content
    except Exception as e:
        print(f"خطأ في معالجة الـ PDF: {e}")
        return None

# توليد المحتوى عبر الذكاء الاصطناعي
def generate_ai_content(prompt_type):
    prompts = {
        "azkar_sabah": "اكتب منشوراً صباحياً قصيراً يحتوي على أحد أذكار الصباح وفضلها بنبرة إيمانية دافئة.",
        "stories_sabah": "اكتب قصة إسلامية وعبرة مأثورة ملهمة وقصيرة جداً، واختمها بـ (العبرة من القصة:).",
        "azkar_masa": "اكتب منشوراً مسائياً قصيراً ومؤثراً يحتوي على أحد أذكار المساء المأثورة وفضلها.",
        "stories_masa": "اكتب قصة ملهمة قصيرة جداً من التراث الجزائري القديم والصالحين في المغرب الأوسط والأندلس مليئة بالعبر والمواعظ."
    }
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompts[prompt_type]}],
            temperature=0.7
        )
        return completion.choices.message.content
    except:
        return None

def generate_jihad_content():
    prompt = (
        "اكتب منشوراً إسلامياً دعوياً قصيراً ومؤثراً جداً بالفصحى. "
        "يركز على: مواعظ إيمانية، أهمية الجهاد وعقيدة الولاء والبراء، ومراغمة الكفار في جزيرة العرب، والدعاء للمجاهدين في كل ثغور المسلمين."
    )
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return completion.choices.message.content
    except:
        return None

# دالات النشر التي تستدعيها الجدولة الرسمية
async def send_jihad_job(context: ContextTypes.DEFAULT_TYPE):
    text = generate_jihad_content()
    if text:
        full_message = f"{get_hijri_date()}\n\n{text}\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها."
        await context.bot.send_message(chat_id=CHANNEL_ID, text=full_message, parse_mode="Markdown")

async def send_azkar_sabah_job(context: ContextTypes.DEFAULT_TYPE):
    text = generate_ai_content("azkar_sabah")
    if text:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{get_hijri_date()}\n\n{text}\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها.", parse_mode="Markdown")

async def send_azkar_masa_job(context: ContextTypes.DEFAULT_TYPE):
    text = generate_ai_content("azkar_masa")
    if text:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{get_hijri_date()}\n\n{text}\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها.", parse_mode="Markdown")

async def send_story_sabah_job(context: ContextTypes.DEFAULT_TYPE):
    text = generate_ai_content("stories_sabah")
    if text:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{get_hijri_date()}\n\n{text}\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها.", parse_mode="Markdown")

async def send_story_masa_job(context: ContextTypes.DEFAULT_TYPE):
    text = generate_ai_content("stories_masa")
    if text:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{get_hijri_date()}\n\n{text}\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها.", parse_mode="Markdown")

async def send_magazine_sabah_job(context: ContextTypes.DEFAULT_TYPE):
    page_num = get_and_update_next_page()
    fixed_text = extract_and_fix_pdf_text(page_num)
    if fixed_text:
        caption_message = f"{get_hijri_date()}\n\n📖 **من صفحات مجلتكم (الصباحية من الـ PDF)**\n📄 **الصفحة: {page_num + 1}**\n\n{fixed_text}\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها."
        await context.bot.send_message(chat_id=CHANNEL_ID, text=caption_message, parse_mode="Markdown")

async def send_magazine_masa_job(context: ContextTypes.DEFAULT_TYPE):
    page_num = get_and_update_next_page()
    fixed_text = extract_and_fix_pdf_text(page_num)
    if fixed_text:
        caption_message = f"{get_hijri_date()}\n\n📖 **من صفحات مجلتكم (المسائية من الـ PDF)**\n📄 **الصفحة: {page_num + 1}**\n\n{fixed_text}\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها."
        await context.bot.send_message(chat_id=CHANNEL_ID, text=caption_message, parse_mode="Markdown")

# 📣 الرسالة التعريفية الفورية عند التشغيل
async def on_startup(application: Application):
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
        "🔄 **كل نصف ساعة بدون توقف:** مواعظ إيمانية مكثفة، منشورات عن عقيدة الولاء والبراء، ومراغمة الكفار، ودعاء مستمر للمجاهدين الأبطال في كل بقاع الأرض وثغور المسلمين.\n\n"
        "💬 **ميزة التفاعل الفوري:**\n"
        "يمكنكم الآن الضغط على زر (التعليقات) أسفل أي منشور وطرح أسئلتكم الشرعية والعلمية، وسيقوم البوت بالرد الفقهي الفوري والمباشر عليكم!\n\n"
        "نسأل الله الثبات والنصر والقبول 🤲🌱\n"
        "🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها."
    )
    try:
        sent_message = await application.bot.send_message(chat_id=CHANNEL_ID, text=intro_text, parse_mode="Markdown")
        await application.bot.pin_chat_message(chat_id=CHANNEL_ID, message_id=sent_message.message_id)
    except Exception as e:
        print(f"خطأ في الرسالة التعريفية: {e}")

# دالة الرد الفقهي في التعليقات
async def reply_to_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or update.message.from_user.is_bot: return
    user_text, user_name = update.message.text, update.message.from_user.first_name
    system_instruction = (
        "أنت مساعد إسلامي فقيه، ترد على أسئلة المسلمين بأدب وفق الكتاب والسنة بفهم سلف الأمة. "
        "يجب أن تبدأ ردك دائماً بعبارة حافلة مثل: 'نعم أخي الموحد البطل' أو 'نعم أختي الموحدة العفيفة'."
    )
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": f"السائل: {user_name}، السؤال: {user_text}"}],
            temperature=0.5
        )
        await update.message.reply_text(text=completion.choices.message.content, parse_mode="Markdown")
    except Exception as e: print(f"خطأ في الرد: {e}")
# دالة الترحيب التلقائي بالأعضاء الجدد في المجموعة
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        # التأكد من أن العضو المنضم ليس البوت نفسه
        if not member.is_bot:
            welcome_text = (
                f"🌱 **مرحباً بك أخي الموحد البطل {member.first_name} في مجموعة النقاشات** 🌱\n\n"
                "سعدنا بانضمامك إلينا. يمكنك طرح أسئلتك واستفساراتك الشرعية هنا، "
                "وسيجيبك نظام الذكاء الاصطناعي الفقهي فوراً إن شاء الله.\n\n"
                "🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها."
            )
            await update.message.reply_text(text=welcome_text, parse_mode="Markdown")
            
def main():
    # بناء التطبيق مع تفعيل الجدولة الرسمية المستقرة
    application = Application.builder().token(TOKEN).build()
    
    # ربط دالة الإقلاع الفوري للرسالة المثبتة
    application.post_init = on_startup
    
    # معالج تعليقات الأعضاء والرد الفقهي الآلي
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to_member))
    
    # معالج انضمام الأعضاء الجدد للمجموعة
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    # 📅 جدولة المهام الرسمية بدون أي تعارض برمي
    job_queue = application.job_queue
    
    # 1. المنشور الدوري (كل 30 دقيقة = 1800 ثانية) يتم بعد ثانية واحدة من التشغيل للتجربة
    job_queue.run_repeating(send_jihad_job, interval=1800, first=1)
    
    # 2. المواعيد اليومية الثابتة والمضبوطة حسب توقيت المنطقة الزمنية المحلية
    job_queue.run_daily(send_azkar_sabah_job, time=time(6, 0, tzinfo=LOCAL_TZ))
    job_queue.run_daily(send_magazine_sabah_job, time=time(8, 0, tzinfo=LOCAL_TZ))
    job_queue.run_daily(send_story_sabah_job, time=time(12, 0, tzinfo=LOCAL_TZ))
    job_queue.run_daily(send_azkar_masa_job, time=time(17, 0, tzinfo=LOCAL_TZ))
    job_queue.run_daily(send_magazine_masa_job, time=time(21, 30, tzinfo=LOCAL_TZ))
    job_queue.run_daily(send_story_masa_job, time=time(22, 30, tzinfo=LOCAL_TZ))

    # ⚡ تشغيل البوت بشكل مستمر ودائم دون توقف
    application.run_polling()

if __name__ == "__main__":
    main()

    # ⚡ تشغيل البوت بشكل مستمر ودائم دون توقف
    application.run_polling()

if __name__ == "__main__":
    main()

    
    # 1. المنشور الدوري (كل 30 دقيقة = 1800 ثانية)
    job_queue.run_repeating(send_jihad_job, interval=1800, first=10)
    
    # 2. المواعيد اليومية الثابتة والمضبوطة حسب توقيت المنطقة الزمنية المحلية
    job_queue.run_daily(send_azkar_sabah_job, time=time(6, 0, tzinfo=LOCAL_TZ))
    job_queue.run_daily(send_magazine_sabah_job, time=time(8, 0, tzinfo=LOCAL_TZ))
    job_queue.run_daily(send_story_sabah_job, time=time(12, 0, tzinfo=LOCAL_TZ))
    job_queue.run_daily(send_azkar_masa_job, time=time(17, 0, tzinfo=LOCAL_TZ))
        
