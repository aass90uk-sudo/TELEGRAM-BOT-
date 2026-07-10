import os
import logging
import asyncio
import datetime
import pytz
from pypdf import PdfReader
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# إعدادات مراقبة السيرفر
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# جلب المتغيرات البيئية من ريلواي
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

# تهيئة عميل Groq والتوقيت كما هو في صورك
ai_client = Groq(api_key=GROQ_KEY)
LOCAL_TZ = pytz.timezone('Asia/Riyadh')

PAGE_TRACKER_FILE = "current_page.txt"

def get_and_update_next_page():
    current_page = 0
    if os.path.exists(PAGE_TRACKER_FILE):
        try:
            with open(PAGE_TRACKER_FILE, "r") as f:
                current_page = int(f.read().strip())
        except ValueError:
            current_page = 0
            
    with open(PAGE_TRACKER_FILE, "w") as f:
        f.write(str(current_page + 1))
    return current_page

def generate_ai_content(prompt_type: str) -> str:
    prompts = {
        "azkar_sabah": "اكتب منشوراً صباحياً فصيحاً ومؤثراً يحتوي على أحد أذكار الصباح، وفضلها بنبرة إيمانية دافئة.",
        "stories_sabah": "اكتب قصة إسلامية وعبرة مأثورة ملهمة ومختصرة جداً، واختمها بـ (العبرة من القصة: ).",
        "azkar_masa": "اكتب منشوراً مسائياً فصيحاً ومؤثراً يحتوي على أحد أذكار المساء، المأثورة وفضلها.",
        "stories_masa": "اكتب قصة ملهمة قصيرة جداً من التراث الجزائري (الديزي) القديم، والصالحين في المغرب الأوسط والأندلس مليئة بالعبر والمواعظ."
    }
    prompt = prompts.get(prompt_type, "اكتب مواعظ وتوجيهات إيمانية بليغة.")
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت خبير دعوي وتربوي إسلامي، لغتك فصيحة وبليغة جداً وتلتزم باللغة العربية الفصحى القوية."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return completion.choices.message.content.strip()
    except Exception as e:
        logger.error(f"خطأ في توليد المحتوى الذكي: {e}")
        return ""

def generate_jihad_content() -> str:
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت خبير دعوي وتربوي إسلامي بليغ جداً وفصيح."},
                {"role": "user", "content": "اكتب منشوراً إسلامياً دعوياً حماسياً يركز على عقيدة الولاء والبراء، أهمية الجهاد وثبات الأمة، ومراغمة الكفار في جزيرة العرب، مع الدعاء لأبطال وثغور المجاهدين."}
            ],
            temperature=0.7,
            max_tokens=800
        )
        return completion.choices.message.content.strip()
    except Exception as e:
        logger.error(f"خطأ في توليد المحتوى الدوري: {e}")
        return ""

def extract_and_fix_pdf_text(page_num: int) -> str:
    pdf_path = "magazine.pdf"
    if not os.path.exists(pdf_path):
        return ""
    try:
        reader = PdfReader(pdf_path)
        if page_num >= len(reader.pages):
            page_num = 0
            with open(PAGE_TRACKER_FILE, "w") as f:
                f.write("1")
        page = reader.pages[page_num]
        raw_text = page.extract_text()
        if not raw_text or len(raw_text.strip()) < 10:
            return ""
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت خبير لغوي متمكن، مهمتك إصلاح النصوص العربية المكسورة الناتجة عن استخراج النصوص من ملفات PDF الممسوحة ضوئياً، أعد صياغتها لتكون فصيحة ومترابطة دون تغيير المعنى الأصل وبدون تلخيص."},
                {"role": "user", "content": raw_text}
            ],
            temperature=0.5,
            max_tokens=1500
        )
        return completion.choices.message.content.strip()
    except Exception as e:
        logger.error(f"خطأ في معالجة الـ PDF: {e}")
        return ""

async def send_to_channel(context: ContextTypes.DEFAULT_TYPE, text: str):
    if not text:
        return
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
    except Exception:
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
        except Exception as e:
            logger.error(f"فشل الإرسال نهائياً للقناة: {e}")

async def send_daily_post(context: ContextTypes.DEFAULT_TYPE, prompt_type: str):
    text = generate_ai_content(prompt_type)
    if text:
        await send_to_channel(context, text)

async def send_magazine_page(context: ContextTypes.DEFAULT_TYPE, period_name: str):
    page_num = get_and_update_next_page()
    fixed_text = extract_and_fix_pdf_text(page_num)
    if fixed_text:
        caption_message = f"📖 **من صفحات مجلتكم الموقرة ({period_name})** 📖\nالمنشور رقم: {page_num + 1}\n\n{fixed_text}\n\n*صدقة جارية للأخت الأندلسية غفر الله لها*"
        await send_to_channel(context, caption_message)

# --- دالة الترحيب والتثبيت كما هي في صورك تماماً ---
async def send_welcome_intro(context: ContextTypes.DEFAULT_TYPE):
    intro_text = (
        "✨ **مرحباً بكم في قناة ريحانة المغرب الأوسط الأندلسية** ✨\n\n"
        "يسرنا أن نعلن لكم عن تفعيل نظام الذكاء الاصطناعي الإسلامي لإدارة ونشر محتوى القناة تلقائياً على مدار 24 ساعة بجدول منظم كالآتي:\n\n"
        "📊 **المحتوى اليومي الثابت:**\n"
        "🌅 06:00 صباحاً: أذكار الصباح وبث الطمأنينة.\n"
        "📖 08:00 صباحاً: مجلة القناة (النسخة الصباحية) المستخرجة آلياً من الـ PDF.\n"
        "📜 12:00 ظهراً: قصة صباحية وعبرة بليغة.\n"
        "🌆 05:00 مساءً: أذكار المساء وتحصين المسلم.\n"
        "📄 21:30 مساءً: مجلة القناة (النسخة المسائية) ومتابعة المقالات.\n"
        "🌌 22:30 مساءً: قصة مسائية وتراث دزيري أندلسي من سير الصالحين.\n\n"
        "⚔️ **المحتوى الدوري المتجدد:**\n"
        "كل نصف ساعة بدون توقف: مواعظ إيمانية مكثفة، منشورات عن عقيدة الولاء والبراء، ومراغمة الكفار، والدعاء المستمر للمجاهدين في الثغور.\n\n"
        "💬 **ميزة التفاعل الفوري:**\n"
        "يمكنكم التعليق وطرح الأسئلة الفقهية في المجموعة المرتبطة ليرد عليكم البوت فوراً بالدليل الشرعي.\n\n"
        "*صدقة جارية للأخت الأندلسية غفر الله لها ولوالديها*"
    )
    try:
        sent_message = await context.bot.send_message(chat_id=CHANNEL_ID, text=intro_text, parse_mode="Markdown")
        await context.bot.pin_chat_message(chat_id=CHANNEL_ID, message_id=sent_message.message_id)
        print("(تم إرسال وتثبيت الرسالة التعريفية فوراً عند الإقلاع)")
    except Exception as e:
        print(f"(e) خطأ أثناء إرسال الرسالة التعريفية: {e}")

# --- إصلاح حلقة الجدولة المدمجة الخاصة بك لتنشر بدقة وثبات ---
async def intensive_scheduler(context: ContextTypes.DEFAULT_TYPE):
    print("(... بدء حلقة الجدولة المدمجة الكبرى ...)")
    print("(... بدء حلقة الجدولة والمراقبة الزمنية ...)")
    
    half_hour_counter = 0
    
    while True:
        try:
            now = datetime.datetime.now(LOCAL_TZ)
            current_time = now.strftime("%H:%M")
            
            # المنشورات اليومية المجدولة المذكورة في صورك
            if current_time == "06:00":
                await send_daily_post(context, "azkar_sabah")
                await asyncio.sleep(60) # تجميد ثوانٍ لمنع تكرار الإرسال في نفس الدقيقة
                
            elif current_time == "08:00":
                await send_magazine_page(context, "النسخة الصباحية")
                await asyncio.sleep(60)
                
            elif current_time == "12:00":
                await send_daily_post(context, "stories_sabah")
                await asyncio.sleep(60)
                
            elif current_time == "17:00":
                await send_daily_post(context, "azkar_masa")
                await asyncio.sleep(60)
                
            elif current_time == "21:30":
                await send_magazine_page(context, "النسخة المسائية")
                await asyncio.sleep(60)
                
            elif current_time == "22:30":
                await send_daily_post(context, "stories_masa")
                await asyncio.sleep(60)

            # المنشور الحماسي الدوري المتكرر كل 30 دقيقة (1800 ثانية)
            if half_hour_counter >= 1800:
                text = generate_jihad_content()
                if text:
                    await send_to_channel(context, text)
                half_hour_counter = 0 # تصفير العداد ليعمل النصف ساعة القادمة
                
        except Exception as e:
            print(f"(e) خطأ في حلقة الجدولة: {e}")
            
        await asyncio.sleep(10) # فحص الوقت كل 10 ثوانٍ لضمان الدقة العالية والاستقرار
        half_hour_counter += 10

# --- دالة الرد الفقهي الإسلامي في التعليقات ---
async def reply_to_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or update.message.from_user.is_bot:
        return
    user_text = update.message.text
    user_name = update.message.from_user.first_name
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"أنت باحث فقهي بليغ متمكن. ابدأ الرد مباشرة بمخاطبة السائل بعبارة تناسب اسمه {user_name} مثل (نعم أخي الموحد البطل) أو (نعم أختي الموحدة العفيفة) ثم قدم إجابة بليغة مستندة للكتاب والسنة بالفصحى وبدون ماركداون معقد."},
                {"role": "user", "content": user_text}
            ],
            temperature=0.6,
            max_tokens=1000
        )
        reply = completion.choices.message.content.strip()
        if reply:
            await update.message.reply_text(reply)
    except Exception as e:
        print(f"(e) خطأ في الرد: {e}")

async def on_startup(app: Application):
    """إرسال الرسالة الترحيبية وتثبيتها وتشغيل الجدولة تلقائياً فور إقلاع البوت"""
