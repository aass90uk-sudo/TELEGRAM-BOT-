import os
import fitz  # مكتبة PyMuPDF لقراءة الـ PDF واستخراج الصور والنصوص
import asyncio
import schedule
import time
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# 🔑 جلب المفاتيح والتوكينات من متغيرات البيئة (Environment Variables)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "ضع_توكن_البوت_هنا_إن_لم_تستخدم_متغيرات_البيئة")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "ضع_مفتاح_GROQ_هنا_إن_لم_تستخدم_متغيرات_البيئة")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel_username")  # معرف القناة

# مسار ملف المجلة المرفوع
PDF_FILE_PATH = "magazine.pdf" 

# تهيئة عميل Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# متغير لحفظ رقم الصفحة الحالية التي وصل إليها البوت في النشر المجدول
CURRENT_PAGE = 0 

def extract_page_as_image_and_text(page_num: int):
    """استخراج الصفحة كصورة عالية الدقة + استخراج النص الموجود بداخلها"""
    if not os.path.exists(PDF_FILE_PATH):
        print(f"❌ خطأ: لم يتم العثور على ملف المجلة {PDF_FILE_PATH}")
        return None, None

    doc = fitz.open(PDF_FILE_PATH)
    
    # حماية من تجاوز عدد الصفحات (إعادة الدورة عند انتهاء صفحات المجلة)
    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        return None, None
        
    actual_page_num = page_num % total_pages
    page = doc.load_page(actual_page_num)
    
    # 1. استخراج النص الموجود بالصفحة
    extracted_text = page.get_text("text").strip()

    # 2. تحويل الصفحة إلى صورة PNG عالية الجودة (DPI 150)
    pix = page.get_pixmap(dpi=150) 
    image_bytes = pix.tobytes("png")

    doc.close()
    return image_bytes, extracted_text

def format_text_with_groq(raw_text: str, time_of_day: str) -> str:
    """تنسيق وتجميل النص المستخرج من الصفحة بواسطة الذكاء الاصطناعي"""
    if not raw_text:
        return f"📖 **صفحة {time_of_day}**"

    prompt = (
        f"قم بتنسيق وترتيب النص التالي المستخرج من مجلة دعوية ليكون منشوراً راقياً ومقروءاً في تليجرام لـ 'صفحة {time_of_day}'. "
        "حافظ على الآيات والأحاديث والنصوص كما هي تماماً ودون تغيير في المعنى، وأضف بعض الترتيب والرموز التعبيرية المناسبة:\n\n"
        f"{raw_text}"
    )
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ خطأ في تنسيق النص عبر Groq: {e}")
        return raw_text

# 📡 دالة النشر المجدول
async def send_scheduled_page(app, time_of_day: str):
    global CURRENT_PAGE
    print(f"⏳ جاري تحضير ونشر صفحة {time_of_day} (الصفحة رقم {CURRENT_PAGE + 1})...")

    image_bytes, raw_text = extract_page_as_image_and_text(CURRENT_PAGE)

    if image_bytes is None:
        print("❌ تعذر قراءة الصفحة، يرجى التأكد من وجود ملف magazine.pdf")
        return

    # تنسيق النص المستخرج
    formatted_caption = format_text_with_groq(raw_text, time_of_day)

    # اقتصاص النص إذا كان يتجاوز حد تليجرام للتعليقات على الصور (1024 حرف)
    if len(formatted_caption) > 1000:
        formatted_caption = formatted_caption[:980] + "...\n\n*(تتمة الصفحة في المجلة)*"

    try:
        # إرسال صورة الصفحة مع النص المستخرج كتعليق مرفق
        await app.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=image_bytes,
            caption=f"🌅 **صفحة {time_of_day}**\n\n{formatted_caption}",
            parse_mode="Markdown"
        )
        print(f"✅ تم نشر صفحة {time_of_day} بنجاح!")
        
        # الانتقال للصفحة التالية للبث القادم
        CURRENT_PAGE += 1

    except Exception as e:
        print(f"❌ فشل إرسال المنشور إلى القناة: {e}")

# ⏰ حلقة الجدولة الزمنية
def run_scheduler(loop, app):
    # مواعيد النشر اليومية (يمكنك تعديل الأوقات حسب رغبتك)
    schedule.every().day.at("07:00").do(
        lambda: asyncio.run_coroutine_threadsafe(send_scheduled_page(app, "الصباح"), loop)
    )
    schedule.every().day.at("19:00").do(
        lambda: asyncio.run_coroutine_threadsafe(send_scheduled_page(app, "المساء"), loop)
    )

    while True:
        schedule.run_pending()
        time.sleep(30)

# 🚀 أمر البداية للمستخدمين /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك! 🌙\n"
        "البوت يعمل حالياً على نشر صفحات المجلة تلقائياً وبشكل مجدول إلى القناة."
    )

# ⚙️ تشغيل التطبيق
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # تشغيل الجدولة في الخلفية
    loop = asyncio.get_event_loop_policy().get_event_loop()
    threading.Thread(target=run_scheduler, args=(loop, app), daemon=True).start()

    print("🚀 بوت bot.py يعمل بنجاح ويقرأ المجلة!")
    app.run_polling()
    
