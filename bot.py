import os
import asyncio
import schedule
import time
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google import genai
from google.genai import types

# 🔑 جلب المفاتيح والتوكينات من متغيرات البيئة
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "ضع_توكن_البوت_هنا")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ضع_مفتاح_GEMINI_هنا")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel_username")  # معرف القناة

# تهيئة عميل Gemini باستخدام المكتبة الرسمية الحديثة google-genai
client = genai.Client(api_key=GEMINI_API_KEY)

# قائمة مواضيع أنثروبولوجية من منظور إسلامي
TOPICS = [
    "الأنثروبولوجيا اللغوية وتعليم الأسماء لآدم عليه السلام",
    "عمران المجتمعات والبناء الاجتماعي عند ابن خلدون",
    "مفهوم الفطرة كأساس بنائي في السلوك الإنساني",
    "علم الإنسان الثقافي ومفهوم التعارف بين الشعوب والأمم",
    "القرابة وصلة الرحم وأثرها في تماسك المجتمع",
    "الطقوس الشعائرية وأثر العبادات في الضبط والتماسك الاجتماعي",
    "الحضارات القديمة والسنن الإلهية في قيامها وسقوطها",
    "أنثروبولوجيا الأخلاق والقيم الإنسانية الفطرية",
    "التكيف البشري وعمارة الأرض كواجب استخلافي"
]
topic_index = 0

def generate_post_with_gemini(topic: str, time_of_day: str) -> str:
    """توليد منشور أنثروبولوجي بإطار إسلامي باستخدام نموذج Gemini"""
    system_instruction = (
        "تصرّف كعالم أنثروبولوجيا (علم الإنسان) ومفكر إسلامي خبير، متحدث باللغة العربية الفصحى. "
        "اكتب منشوراً مشوقاً ومختصراً جداً ينظر إلى الأنثروبولوجيا والمجتمعات البشريّة من منظور إسلامي أصيل "
        "مستنداً إلى مفهوم التكريم الإلهي للإنسان، الفطرة، ومقاصد الشريعة والعمران البشري. "
        "قسّم المقال إلى نقاط واضحة باستخدام الإيموجي. "
        "تنبيه صارم: تجنب النظريات المادية المنافية للعقيدة الإسلامية، ولا تستخدم رموز الماركداون المربعة أو المعقدة لتجنب أخطاء الإرسال."
    )
    
    prompt = f"اكتب منشوراً أنثروبولوجياً بأسلوب ومفاهيم إسلامية لنشرة '{time_of_day}' عن الموضوع التالي: {topic}"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.5,
                max_output_tokens=800,
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ خطأ في توليد المحتوى عبر Gemini: {e}")
        return f"✨ {topic} ✨\n\nيتناول موضوع اليوم الإنسان والحضارة من منظور يتفكر في سنن الله في الخلق والعمران وتتابع الأمم."

# 📡 دالة النشر المجدول إلى القناة
async def send_scheduled_post(app, time_of_day: str):
    global topic_index
    current_topic = TOPICS[topic_index % len(TOPICS)]
    topic_index += 1

    print(f"⏳ جاري تحضير ونشر منشور {time_of_day} عن: {current_topic}...")

    # توليد النص عبر Gemini
    post_text = generate_post_with_gemini(current_topic, time_of_day)
    full_message = f"🌅 **منشور {time_of_day}**\n\n✨ **{current_topic}** ✨\n\n{post_text}"

    try:
        await app.bot.send_message(
            chat_id=CHANNEL_ID,
            text=full_message,
            parse_mode="Markdown"
        )
        print(f"✅ تم نشر منشور {time_of_day} بنجاح!")
    except Exception as e:
        print(f"❌ فشل إرسال المنشور إلى القناة: {e}")

# ⏰ حلقة الجدولة الزمنية (يمكنك تعديل الأوقات أو إضافة أوقات أخرى)
def run_scheduler(loop, app):
    # مواعيد النشر اليومية (صباحاً ومساءً)
    schedule.every().day.at("07:00").do(
        lambda: asyncio.run_coroutine_threadsafe(send_scheduled_post(app, "الصباح"), loop)
    )
    schedule.every().day.at("19:00").do(
        lambda: asyncio.run_coroutine_threadsafe(send_scheduled_post(app, "المساء"), loop)
    )

    while True:
        schedule.run_pending()
        time.sleep(30)

# 🚀 أمر البداية للمستخدمين /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "السلام عليكم ورحمة الله وبركاته 🌹\n"
        "أهلاً بك! البوت يعمل حالياً بنجاح وينشر منشورات أنثروبولوجية إسلامية تلقائياً وبشكل مجدول إلى القناة."
    )

# ⚙️ تشغيل التطبيق
if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        print("❌ خطأ: يرجى التأكد من ضبط TELEGRAM_TOKEN و GEMINI_API_KEY في متغيرات البيئة!")
    else:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))

        # تشغيل الجدولة في الخلفية
        loop = asyncio.get_event_loop_policy().get_event_loop()
        threading.Thread(target=run_scheduler, args=(loop, app), daemon=True).start()

        print("🚀 البوت يعمل بنجاح مع Gemini وبدون مجلة!")
        app.run_polling()
        
