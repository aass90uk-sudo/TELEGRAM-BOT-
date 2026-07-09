import os
import asyncio
from datetime import datetime
from pytz import timezone
from hijri_converter import Gregorian
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq

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

# دالة توليد المنشورات الدعوية والجهادية كل 30 دقيقة
def generate_jihad_content():
    prompt = (
        "ا... اكتب منشوراً إسلامياً دعوياً قصيراً ومؤثراً جداً باللغة العربية الفصحى. "
        "يركز المنشور على مواضيع محددة تتناوب بينها: مواعظ إيمانية، أهمية الجهاد في سبيل الله وعقيدة الولاء والبراء، "
        "مراغمة الكفار في جزيرة العرب، والدعاء الصادق والمخلص للمجاهدين وثباتهم في كل بقاع الأرض وثغور المسلمين. "
        "اجعل الأسلوب بليغاً وحماسياً يحيي القلوب ويحفز الهمم."
    )
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return completion.choices.message.content
    except Exception as e:
        print(f"خطأ في توليد المحتوى الدعوي: {e}")
        return None

# دالة إرسال الرسالة التعريفية الفورية بجداول البوت ومحتوى القناة
async def send_welcome_intro(context: ContextTypes.DEFAULT_TYPE):
    intro_text = (
        "📣 **مرحباً بكم في قناة رَيْحَانَةُ المَغْرِبِ الأَوْسَطِ** 📣\n\n"
        "يسرنا أن نعلن لكم عن تفعيل **نظام الذكاء الاصطناعي الإسلامي** لإدارة ونشر محتوى القناة تلقائياً على مدار 24 ساعة بجدول منظم كالتالي:\n\n"
        "⏰ **المحتوى اليومي الثابت:**\n"
        "☀️ **06:00 صباحاً:** أذكار الصباح المأثورة وبث الطمأنينة.\n"
        "📖 **08:00 صباحاً:** قصة وعبرة إسلامية مشوقة لبداية يومكم.\n"
        "🌙 **05:00 مساءً:** أذكار المساء لحفظكم وتحصينكم.\n"
        "🌌 **09:30 مساءً:** قصة مسائية ملهمة ورواية من عبق التراث الجزائري (الدزيري) الصالح.\n\n"
        "⚡ **المحتوى الدوري المتجدد:**\n"
        "🔄 **كل نصف ساعة بدون توقف:** مواعظ إيمانية مكثفة، منشورات عن عقيدة الولاء والبراء، مراغمة الكفار في جزيرة العرب، ودعاء مستمر للمجاهدين الأبطال في كل بقاع الأرض وثغور المسلمين.\n\n"
        "💬 **ميزة التفاعل الفوري:**\n"
        "يمكنكم الآن الضغط على زر (التعليقات) أسفل أي منشور وطرح أسئلتكم الشرعية والعلمية، وسيقوم البوت بالرد الفقهي الفوري والمباشر عليكم!\n\n"
        "نسأل الله الثبات والنصر والقبول 🤲🌱"
    )
    try:
        # إرسال الرسالة وتثبيتها بالقناة لكي يراها الجميع
        sent_message = await context.bot.send_message(chat_id=CHANNEL_ID, text=intro_text, parse_mode="Markdown")
        await context.bot.pin_chat_message(chat_id=CHANNEL_ID, message_id=sent_message.message_id)
        print("تم إرسال وتثبيت الرسالة التعريفية الفورية بنجاح!")
    except Exception as e:
        print(f"خطأ أثناء إرسال الرسالة التعريفية: {e}")

# حلقة النشر التلقائي المكثف (كل 30 دقيقة)
async def intensive_scheduler(context: ContextTypes.DEFAULT_TYPE):
    print("بدء حلقة النشر والجدولة اليومية...")
    
    # تشغيل الرسالة التعريفية فوراً لمرة واحدة عند إقلاع البوت
    await send_welcome_intro(context)
    
    while True:
        text = generate_jihad_content()
        if text:
            full_message = f"{get_hijri_date()}\n\n{text}"
            try:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=full_message, parse_mode="Markdown")
                print("تم نشر المنشور الدوري بنجاح.")
            except Exception as e:
                print(f"خطأ أثناء النشر الدوري: {e}")
        
        # الانتظار لمدة 30 دقيقة
        await asyncio.sleep(1800)

# دالة الرد الشرعي الفوري على التعليقات
async def reply_to_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or update.message.from_user.is_bot:
        return

    user_text = update.message.text
    user_name = update.message.from_user.first_name

    system_instruction = (
        "أنت مساعد إسلامي فقيه، ترد على أسئلة المسلمين بأدب وفق الكتاب والسنة بفهم سلف الأمة. "
        "يجب أن تبدأ ردك دائماً بعبارة حافلة ومخصصة بناءً على جنس السائل إن أمكن، "
        "مثل: 'نعم أخي الموحد البطل' أو 'نعم أختي الموحدة العفيفة'. "
        "اجعل ردودك شرعية، واضحة، ومختصرة، والتزم باللغة العربية الفصحى الفخمة."
    )

    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"السائل يدعى {user_name}، وسؤاله هو: {user_text}"}
            ],
            temperature=0.5
        )
        await update.message.reply_text(text=completion.choices.message.content, parse_mode="Markdown")
    except Exception as e:
        print(f"خطأ أثناء رد الذكاء الاصطناعي: {e}")

def main():
    application = Application.builder().token(TOKEN).build()

    # معالج الرسائل النصية للرد في التعليقات
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to_member))

    # تشغيل حلقة الجدولة والنشر الفوري في الخلفية
    loop = asyncio.get_event_loop()
    loop.create_task(intensive_scheduler(application.initialize().__await__()))

    print("البوت يعمل الآن ويستعد لنشر الرسالة التعريفية والجدولة...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
