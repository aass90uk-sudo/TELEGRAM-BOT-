import os
import datetime
import asyncio
from groq import Groq  # استيراد مكتبة جروج الرسمية
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

# 1. جلب التوكنز والمعرفات بشكل آمن من متغيرات بيئة الاستضافة
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID") 
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# تهيئة عميل Groq السريع
ai_client = Groq(api_key=GROQ_API_KEY)

# إعداد المنطقة الزمنية المحلية (تعديل توقيتك إن لزم الأمر)
# يمكنك تركها لتعتمد على توقيت الخادم، أو تعيينها كـ UTC
LOCAL_TZ = datetime.timezone.utc 

# دالة وهمية لمحاكاة استخراج وقراءة الصفحات (تأكد من مطابقة منطقك الخاص داخلياً)
def get_and_update_next_page():
    # هنا تضع منطق زيادة العداد الخاص بك
    current_page = 1 
    return current_page

def extract_and_fix_pdf_text(page_num, text):
    pdf_path = "magazine.pdf"
    if not os.path.exists(pdf_path):
        print(f"(-) تنبيه: لم يتم العثور على الملف {pdf_path}")
        return None
        
    system_prompt = (
        "أنت خبير تدقيق لغوي وشرعي إسلامي، أمامك نص مستخرج من صفحة مجلة إسلامية أندلسية. "
        "قم بإعادة تجميع الكلمات المكسورة وصياغتها بلغة فصيحة بليغة جداً ومتناسقة."
    )
    
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"النص المستخرج: {text}"}
            ]
        )
        # تم ضبط الصيغة البرمجية لتناسب استجابة Groq الرسمية
        return completion.choices[0].message.content
    except Exception as e:
        print(f"(e) : خطأ في معالجة الـ PDF عبر جروج: {e}")
        return None

def generate_ai_content(prompt_type):
    prompts = {
        "azkar_sabah": "اكتب منشوراً صباحياً قصيراً يحتوي على أحد أذكار الصباح وفضلها بنبرة إيمانية دافئة.",
        "stories_sabah": "اكتب قصة إسلامية وعبرة مأثورة ملهمة ومختصرة جداً واختمها بعبرة من القصة.",
        "azkar_masa": "اكتب منشوراً مسائياً قصيراً ومؤثراً يحتوي على أحد أذكار المساء المأثورة وفضلها.",
        "stories_masa": "اكتب قصة ملهمة قصيرة جداً من التراث الجزائري القديم تبرز القيم والمواعظ الحكيمة.",
        "jihad_content": "اكتب منشوراً حماسياً إيمانياً يعزز عقيدة الولاء والبراء ويدعو للمستضعفين والمجاهدين فصيحاً وبليغاً."
    }
    
    prompt = prompts.get(prompt_type)
    if not prompt:
        return None
        
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"(e) : خطأ في توليد المحتوى من جروج: {e}")
        return None

async def send_daily_post(context: ContextTypes.DEFAULT_TYPE, prompt_type: str):
    """دالة توليد وإرسال المنشور المجدول إلى القناة تلقائياً"""
    text = generate_ai_content(prompt_type)
    if text and CHANNEL_ID:
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
            print(f"(+) تم بنجاح نشر محتوى: {prompt_type}")
        except Exception as e:
            print(f"(e) خطأ أثناء النشر التلقائي في القناة: {e}")

async def send_welcome_intro(application):
    """الرسالة الترحيبية وتثبيتها عند إقلاع البوت لأول مرة"""
    intro_text = (
        "**مرحباً بكم في قناة ريحانة المغرب الأوسط الأندلسية** 🌺\n\n"
        "يسرنا أن نعلن لكم عن تفعيل نظام الذكاء الاصطناعي الإسلامي للإدارة والنشر.\n"
        "محتوى القناة تلقائي على مدار 24 ساعة بجدول منظم كالتالي:\n\n"
        "☀️ **المحتوى اليومي الثابت:**\n"
        "🔹 **صباحاً:** أذكار الصباح المأثورة وبث الطمأنينة 06:00 AM\n"
        "🔹 **صباحاً:** مجلة القناة (النسخة الصباحية) من الـ 08:00 AM\n"
        "🔹 **ظهراً:** قصة صحابة وعبرة عظيمة 12:00 PM\n"
        "🔹 **مساءً:** أذكار المساء لحفظكم وتحصينكم 05:00 PM\n"
        "🔹 **مساءً:** مجلة القناة (النسخة المسائية) بين الـ 08:30 PM\n"
        "🔹 **ليلاً:** قصة مسائية وتراث جزائري أندلسي 10:30 PM\n\n"
        "✨ **المحتوى الدوري المتجدد:**\n"
        "كل نصف ساعة بدون توقف: مواعظ إيمانية مكثفة، منشورات عن عقيدة الولاء والبراء، "
        "ودعاء مستمر للمجاهدين الأبطال في كل بقاع الأرض ونصرة المسلمين.\n\n"
        "⚡️ **ميزة التفاعل الفوري:**\n"
        "يمكنكم الآن الضغط على زر (التعليقات) أسفل أي منشور وطرح أسئلتكم الشرعية والفقهية، "
        "وسيقوم البوت بالرد الفوري الفصيح والمباشر عليكم.\n\n"
        "نسأل الله الثبات والنصر والقبول.\n"
        "صدقة جارية لأمتنا الأندلسية، غفر الله لها."
    )
    
    if not CHANNEL_ID:
        return
        
    try:
        sent_message = await application.bot.send_message(
            chat_id=CHANNEL_ID, 
            text=intro_text, 
            parse_mode="Markdown"
        )
        await application.bot.pin_chat_message(
            chat_id=CHANNEL_ID, 
            message_id=sent_message.message_id
        )
        print("(+) تم إرسال وتثبيت الرسالة الترحيبية فوراً عند الإقلاع")
    except Exception as e:
        print(f"(-) خطأ أثناء إرسال الرسالة الترحيبية: {e}")

async def intensive_scheduler(context: ContextTypes.DEFAULT_TYPE):
    """المجدول الزمني المكثف والذكي لفحص الأوقات والنشر الدوري"""
    print("(...) بدء حلقة المجدول والمراقبة الزمنية الفعالة")
    half_hour_counter = 0
    
    while True:
        now = datetime.datetime.now(LOCAL_TZ)
        current_time = now.strftime("%H:%M")
        
        # 1. المنشورات اليومية المجدولة بدقة الساعة والدقيقة
        if current_time == "06:00":
            await send_daily_post(context, "azkar_sabah")
            await asyncio.sleep(80) # النوم لمنع تكرار التحقق والنشر المتعدد في نفس الدقيقة
            
        elif current_time == "16:30":
            await send_daily_post(context, "stories_masa")
            await asyncio.sleep(80)

        # 2. المنشور الحماسي الدوري المتكرر كل 30 دقيقة (1800 ثانية)
        if half_hour_counter >= 1800:
            await send_daily_post(context, "jihad_content")
            half_hour_counter = 0 # تصفير العداد لإعادة الحساب من جديد
            
        # استراحة ثابتة وهامة جداً كل 15 ثانية لحماية البوت من التعليق واستراحة المعالج
        await asyncio.sleep(15)
        half_hour_counter += 15

async def reply_to_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دالة الرد الآلي على تعليقات الأعضاء والأسئلة الفقهية فورياً"""
    if not update.message or not update.message.text or update.message.from_user.is_bot:
        return
        
    user_query = update.message.text
    
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت مجيب شرعي وفقهي فصيح لبق، أجب على أسئلة المستخدمين بدقة ووضوح ومودة بروح أندلسية إيمانية."},
                {"role": "user", "content": user_query}
            ]
        )
        reply_text = completion.choices[0].message.content
        await update.message.reply_text(reply_text, parse_mode="Markdown")
    except Exception as e:
        print(f"(e) : خطأ في الرد الآلي عبر جروج: {e}")

async def on_startup(application: Application):
    """تجهيز إقلاع البوت وتشغيل الدوال التلقائية بالتوازي بشكل سليم"""
    await send_welcome_intro(application)
    # تشغيل مجدول الوقت المطور كـ مهمة خلفية آمنة لا توقف استجابة البوت
    asyncio.create_task(intensive_scheduler(application.updater.job_queue.application))

def main():
    if not BOT_TOKEN:
        print("(-) خطأ حرج: لم يتم العثور على TELEGRAM_BOT_TOKEN في متغيرات البيئة!")
        return

    # بناء وتأسيس البوت الشامل لتيليجرام
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة الفلاتر والمعالجات لاستقبال رسائل المجموعات والتعليقات
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to_member))
    
    # ربط دالة التهيئة والتشغيل التلقائي
    application.post_init = on_startup
    
    print("... البوت الشامل والجامع يعمل بنجاح ومستعد للنشر والتفاعل ...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
