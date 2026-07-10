import os
import logging
import asyncio
import datetime
import pytz
from pypdf import PdfReader
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعدادات التسجيل ومراقبة الأخطاء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# جلب المتغيرات البيئية من ريلواي
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

# التحقق من وجود المتغيرات الأساسية
if not all([TOKEN, CHANNEL_ID, GROQ_KEY]):
    logger.error("خطأ: يرجى التأكد من ضبط جميع المتغيرات البيئية في Railway!")
    exit(1)

# تهيئة عميل Groq
groq_client = Groq(api_key=GROQ_KEY)
TIMEZONE = pytz.timezone('Asia/Riyadh') # توقيت مكة المكرمة

# ملف حفظ الصفحة الحالية للمجلة
PAGE_TRACKER_FILE = "current_page.txt"

def get_next_page_index():
    """قراءة رقم الصفحة التالية المراد نشرها"""
    if os.path.exists(PAGE_TRACKER_FILE):
        try:
            with open(PAGE_TRACKER_FILE, "r") as f:
                return int(f.read().strip())
        except ValueError:
            return 0
    return 0

def save_next_page_index(page_index):
    """حفظ رقم الصفحة التالية"""
    with open(PAGE_TRACKER_FILE, "w") as f:
        f.write(str(page_index))

def generate_ai_content(prompt: str) -> str:
    """توليد النصوص والردود باستخدام نموذج لاما عبر Groq"""
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت مساعد ذكي مخصص لبوت دعوي إيماني حماسي فصيح وبليغ جداً. تلتزم باللغة العربية الفصحى القوية وبثبات الأمة والدعاء للمجاهدين وثغور المسلمين وعقيدة الولاء والبراء."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"خطأ أثناء الاتصال بـ Groq API: {e}")
        return ""

def extract_and_fix_pdf_page() -> str:
    """استخراج نص الصفحة من المجلة وإصلاحها عبر الذكاء الاصطناعي"""
    pdf_path = "magazine.pdf"
    if not os.path.exists(pdf_path):
        logger.warning("ملف magazine.pdf غير موجود في المستودع.")
        return ""
    
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        current_page = get_next_page_index()
        
        if current_page >= total_pages:
            current_page = 0 # العودة للبداية إذا انتهت المجلة
            
        page = reader.pages[current_page]
        raw_text = page.extract_text()
        
        if not raw_text or len(raw_text.strip()) < 10:
            save_next_page_index(current_page + 1)
            return "نسخة دورية من المجلة (تعذر استخراج النص البرمجي من هذه الصفحة آلياً)."

        # إرسال النص المكسور لـ Groq لإصلاحه وتنسيقه
        prompt = f"قم بإعادة تجميع الكلمات المكسورة والتصحيح اللغوي والنحوي للنص التالي المستخرج من مجلة برمجية دعوية ليصبح منسقاً، بليغاً جداً، وفصيحاً. لا تقم بتلخيصه بل أعد صياغته بشكل صحيح وسليم:\n\n{raw_text}"
        fixed_text = generate_ai_content(prompt)
        
        # حفظ الصفحة التالية للمرة القادمة
        save_next_page_index(current_page + 1)
        return fixed_text
    except Exception as e:
        logger.error(f"خطأ أثناء معالجة الـ PDF: {e}")
        return ""

async def send_to_channel(context: ContextTypes.DEFAULT_TYPE, text: str):
    """إرسال المنشور إلى القناة المحددة"""
    if text:
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
        except Exception as e:
            # محاولة الإرسال كنص عادي إذا فشل تنسيق الماركداون بسبب الرموز
            try:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
            except Exception as ex:
                logger.error(f"فشل إرسال الرسالة للقناة: {ex}")

# --- مهام الجدولة الزمنية ---

async def handle_fixed_schedules(context: ContextTypes.DEFAULT_TYPE):
    """فحص التوقيت الحالي لتوكل مكة المكرمة ونشر المهام اليومية المحددة"""
    while True:
        now = datetime.datetime.now(TIMEZONE)
        current_time_str = now.strftime("%H:%M")
        
        # 06:00 صباحاً - أذكار الصباح
        if current_time_str == "06:00":
            content = generate_ai_content("اكتب منشوراً بليغاً ومؤثراً يحتوي على أذكار الصباح مع توجيه إيماني حماسي يحث على الثبات ونصرة الدين.")
            await send_to_channel(context, content)
            await asyncio.sleep(61)
            
        # 08:00 صباحاً - مجلة النسخة الصباحية
        elif current_time_str == "08:00":
            content = extract_and_fix_pdf_page()
            if content:
                await send_to_channel(context, f"📖 **مجلة القناة (النسخة الصباحية)** 📖\n\n{content}")
            await asyncio.sleep(61)
            
        # 12:00 ظهراً - قصة وعبرة ملهمة
        elif current_time_str == "12:00":
            content = generate_ai_content("ألّف قصة تاريخية أو تراثية قصيرة من حكايات الصالحين أو السلف تحمل عبرة ملهمة ومؤثرة للأمة اليوم.")
            await send_to_channel(context, content)
            await asyncio.sleep(61)
            
        # 05:00 مساءً - أذكار المساء
        elif current_time_str == "17:00":
            content = generate_ai_content("اكتب منشوراً بليغاً يحتوي على أذكار المساء مع دعاء وتوجيه إيماني حماسي للأمة والمجاهدين.")
            await send_to_channel(context, content)
            await asyncio.sleep(61)
            
        # 09:30 مساءً - مجلة النسخة المسائية
        elif current_time_str == "21:30":
            content = extract_and_fix_pdf_page()
            if content:
                await send_to_channel(context, f"📄 **مجلة القناة (النسخة المسائية)** 📄\n\n{content}")
            await asyncio.sleep(61)
            
        # 10:30 مساءً - تراث دزيري أندلسي
        elif current_time_str == "22:30":
            content = generate_ai_content("اكتب حكاية أو خاطرة تراثية من عبق المغرب الأوسط والأندلس وعن بطولات الصالحين هناك بأسلوب أدبي بليغ.")
            await send_to_channel(context, content)
            await asyncio.sleep(61)
            
        await asyncio.sleep(30) # الفحص كل 30 ثانية لدقة التوقيت

async def handle_recurring_posts(context: ContextTypes.DEFAULT_TYPE):
    """مهمة النشر الدوري التلقائي الحماسي كل 30 دقيقة"""
    # الانتظار قليلاً عند بداية إقلاع البوت منعاً للاصطدام بالرسائل الأخرى
    await asyncio.sleep(10)
    while True:
        content = generate_ai_content("اكتب منشوراً دعوياً جهادياً حماسياً يركز على عقيدة الولاء والبراء، أهمية الجهاد وثبات الأمة، ومراغمة الكفار في جزيرة العرب، مع الدعاء لأبطال وثغور المجاهدين.")
        if content:
            await send_to_channel(context, content)
        await asyncio.sleep(1800) # 1800 ثانية = 30 دقيقة

# --- الرد التفاعلي في المجموعات ---

async def handle_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد الفقهي التفاعلي في المجموعات والتعليقات"""
    # التأكد من أن الرسالة نصية وليست من القناة نفسها
    if not update.message or not update.message.text:
        return
        
    user_text = update.message.text
    user = update.message.from_user
    
    # تحديد صيغة النداء بناءً على نوع المتفاعل (إذا أمكن تحديد الجنس، وإلا فالافتراض مذكر)
    # يمكنك تخصيص هذا الجزء، هنا سنعتمد صيغة مرنة تعتمد على طلبك
    title_call = "أخي الموحد البطل"
    
    prompt = f"بصفتك باحثاً فقهياً بليغاً، رد على هذا السؤال أو التعليق مستنداً للكتاب والسنة بأسلوب فصيح. ابدأ الرد مباشرة بمخاطبة السائل بعبارة: (نعم {title_call}) ثم أكمل الإجابة الدقيقة:\nالسؤال: {user_text}"
    
    reply_content = generate_ai_content(prompt)
    if reply_content:
        await update.message.reply_text(reply_content)

async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الترحيب الحماسي بالأعضاء الجدد"""
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        prompt = f"اكتب رسالة ترحيبية حماسية ومختصرة ومؤثرة جداً ترحب بـ العضو الجديد الذي انضم للمجموعة، تدعوه فيها للثبات على الحق ونصرة الدين."
        welcome_text = generate_ai_content(prompt)
        if welcome_text:
            await update.message.reply_text(welcome_text)

# --- إقلاع وتشغيل البوت ---

async def on_startup(app: Application):
    """تشغيل المهام المجدولة في الخلفية عند بدء البوت"""
    asyncio.create_task(handle_fixed_schedules(app.context))
    asyncio.create_task(handle_recurring_posts(app.context))
    logger.info("تم إطلاق المهام المجدولة والدورية بنجاح.")

def main():
    """دالة التشغيل الرئيسية للبوت"""
    # بناء التطبيق وتمرير التوكن
    application = Application.builder().token(TOKEN).build()

    # تسجيل مستمعي الرسائل والأحداث
    # 1. الترحيب بالأعضاء الجدد
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))
    
    # 2. الرد على الرسائل والتعليقات (تستثني الأوامر والرسائل الخاصة بالقنوات)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_group_messages))

    # ضبط دالة تفعيل المهام التلقائية عند تشغيل التطبيق
    application.job_queue.run_once(lambda ctx: None, when=0) # مجرد تفعيل للـ JobQueue إن لزم
    
    # حيلة بسيطة لـ python-telegram-bot لتشغيل دوال الخلفية عبر asyncio دون الاعتماد الكلي على JobQueue المعقد برمجياً في التوقيت
    loop = asyncio.get_event_loop()
    loop.create_task(on_startup(application))

    # بدء استقبال البيانات وتثبيت البوت في وضع العمل المستمر
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
                        
