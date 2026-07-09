import os
import asyncio
from datetime import datetime
from pytz import timezone
from hijri_converter import Gregorian
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

# استخراج وإصلاح نصوص الـ PDF المكسورة
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
            "قم بإعادة تجميع الكلمات المكسورة الناتجة عن السحب الآلي وصياغتها بلغة فصيحة بليغة جداً ومتناسقة."
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

# توليد القصص والمنشورات اليومية المجدولة عبر الذكاء الاصطناعي
def generate_ai_content(prompt_type):
    prompts = {
        "azkar_sabah": "اكتب منشوراً صباحياً قصيراً يحتوي على أحد أذكار الصباح وفضلها بنبرة إيمانية دافئة.",
        "stories_sabah": "اكتب قصة إسلامية وعبرة مأثورة ملهمة وقصيرة جداً، واختمها بـ (العبرة من القصة:).",
        "azkar_masa": "اكتب منشوراً مسائياً قصيراً ومؤثراً يحتوي على أحد أذكار المساء المأثورة وفضلها.",
        "stories_masa": "اكتب قصة ملهمة قصيرة جداً من التراث الجزائري (الدزيري) القديم والصالحين في المغرب الأوسط والأندلس مليئة بالعبر والمواعظ."
    }
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompts[prompt_type]}],
            temperature=0.7
        )
        return completion.choices.message.content
    except Exception as e:
        print(f"خطأ في توليد المحتوى الذكي: {e}")
        return None

# توليد المحتوى الجهادي الدوري كل 30 دقيقة
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
    except Exception as e:
        return None

# دالات النشر في القناة
async def send_daily_post(context: ContextTypes.DEFAULT_TYPE, prompt_type: str):
    text = generate_ai_content(prompt_type)
    if text:
        full_message = f"{get_hijri_date()}\n\n{text}\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها."
        await context.bot.send_message(chat_id=CHANNEL_ID, text=full_message, parse_mode="Markdown")

async def send_magazine_page(context: ContextTypes.DEFAULT_TYPE, period_name: str):
    page_num = get_and_update_next_page()
    fixed_text = extract_and_fix_pdf_text(page_num)
    if fixed_text:
        caption_message = f"{get_hijri_date()}\n\n📖 **من صفحات مجلتكم ({period_name})**\n📄 **الصفحة: {page_num + 1}**\n\n{fixed_text}\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها."
        await context.bot.send_message(chat_id=CHANNEL_ID, text=caption_message, parse_mode="Markdown")

# حلقة الجدولة الكلية والمنسقة بالدقيقة والـ 30 دقيقة
async def intensive_scheduler(context: ContextTypes.DEFAULT_TYPE):
    print("بدء حلقة الجدولة المدمجة الكبرى...")
    half_hour_counter = 0
    while True:
        now = datetime.now(LOCAL_TZ)
        current_time = now.strftime("%H:%M")

        # 1. المنشورات اليومية المجدولة بالدقيقة والساعة
        if current_time == "06:00":
            await send_daily_post(context, "azkar_sabah")
            await asyncio.sleep(60)
        elif current_time == "08:00":
            await send_magazine_page(context, "الصباحية من الـ PDF")
            await asyncio.sleep(60)
        elif current_time == "12:00":
            await send_daily_post(context, "stories_sabah")
            await asyncio.sleep(60)
        elif current_time == "17:00":
            await send_daily_post(context, "azkar_masa")
            await asyncio.sleep(60)
        elif current_time == "21:30":
            await send_magazine_page(context, "المسائية من الـ PDF")
            await asyncio.sleep(60)
        elif current_time == "22:30":
            await send_daily_post(context, "stories_masa")
            await asyncio.sleep(60)

        # 2. المنشور الحماسي الدوري المتكرر كل 30 دقيقة
        if half_hour_counter >= 1800:
            text = generate_jihad_content()
            if text:
                full_message = f"{get_hijri_date()}\n\n{text}\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها."
                try: await context.bot.send_message(chat_id=CHANNEL_ID, text=full_message, parse_mode="Markdown")
                except Exception as e: print(f"خطأ في النشر الدوري: {e}")
            half_hour_counter = 0

        await asyncio.sleep(10)
        half_hour_counter += 10

# دالة الرد الفقهي الإسلامي في التعليقات
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

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to_member))
    loop = asyncio.get_event_loop()
    loop.create_task(intensive_scheduler(application.initialize().__await__()))
    print("البوت الشامل والجامع لكل الميزات يعمل بنجاح...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
