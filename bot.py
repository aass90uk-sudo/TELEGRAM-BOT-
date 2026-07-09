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
        "اكتب منشوراً إسلامياً دعوياً قصيراً ومؤثراً جداً باللغة العربية الفصحى. "
        "يركز المنشور على مواضيع محددة تتناوب بينها: مواعظ إيمانية، أهمية الجهاد في سبيل الله وعقيدة الولاء والبراء، "
        "مراغمة الكفار في جزيرة العرب، والدعاء الصادق والمخلص للمجاهدين وثباتهم في كل بقاع الأرض وثغور المسلمين. "
        "اجعل الأسلوب بليغاً وحماسياً يحيي القلوب ويحفز الهمم، مع إنهاء المنشور بملخص بليغ أو دعاء."
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

# حلقة النشر التلقائي المكثف (كل 30 دقيقة)
async def intensive_scheduler(context: ContextTypes.DEFAULT_TYPE):
    print("بدء حلقة النشر المكثف كل 30 دقيقة...")
    while True:
        text = generate_jihad_content()
        if text:
            full_message = f"{get_hijri_date()}\n\n{text}"
            try:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=full_message, parse_mode="Markdown")
                print("تم نشر المنشور الدوري بنجاح.")
            except Exception as e:
                print(f"خطأ أثناء النشر الدوري: {e}")
        
        # الانتظار لمدة 30 دقيقة (30 * 60 ثانية)
        await asyncio.sleep(1800)

# 🏛️ دالة الرد الشرعي الفوري على تعليقات ورسائل الأعضاء
async def reply_to_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or update.message.from_user.is_bot:
        return

    user_text = update.message.text
    user_name = update.message.from_user.first_name

    system_instruction = (
        "أنت مساعد إسلامي فقيه، ترد على أسئلة المسلمين بأدب وفق الكتاب والسنة بفهم سلف الأمة. "
        "يجب أن تبدأ ردك دائماً بعبارة حافلة ومخصصة بناءً على جنس السائل إن أمكن، "
        "مثل: 'نعم أخي الموحد البطل' أو 'نعم أختي الموحدة العفيفة' أو 'مرحباً بك أخي الموحد / أختي الموحدة'. "
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

# 🤝 دالة الترحيب الجهادي الشرعي الحماسي بالعضو الجديد
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        
        prompt = (
            f"اكتب رسالة ترحيبية إسلامية جهادية حماسية وقصيرة جداً لشخص انضم حديثاً لمجموعتنا الدعوية. "
            f"اسمه الأول هو {member.first_name}. رحب به بعبارات قوية تحث على نصرة الدين، الثبات على الحق، "
            f"والدعاء للمجاهدين المرابطين على الثغور في شتى بقاع الأرض، ليكون الترحيب محفزاً وموقظاً للهمم."
        )
        try:
            completion = ai_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6
            )
            await update.message.reply_text(text=completion.choices.message.content, parse_mode="Markdown")
        except Exception as e:
            print(f"خطأ في رسالة الترحيب: {e}")

def main():
    application = Application.builder().token(TOKEN).build()

    # معالج الرسائل النصية للرد الفوري
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to_member))
    
    # معالج رصد دخول الأعضاء الجدد للترحيب بهم
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    # تشغيل حلقة النشر التلقائي المكثف في الخلفية فور بدء البوت
    loop = asyncio.get_event_loop()
    loop.create_task(intensive_scheduler(application.initialize().__await__()))

    print("البوت المطور يعمل الآن ويستمع ويقوم بالنشر المكثف...")
    application.run_polling()

if __name__ == "__main__":
    main()
            
