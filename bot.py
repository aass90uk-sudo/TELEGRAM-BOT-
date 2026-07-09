import os
import logging
import requests
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# إعداد تسجيل الأخطاء
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")

# دالة جلب كافة القراء من خادم MP3Quran
def get_all_reciters():
    try:
        url = "https://mp3quran.net"
        response = requests.get(url).json()
        reciters_list = response.get("reciters", [])
        
        reciters_dict = {}
        for r in reciters_list:
            name = r.get("name", "").strip()
            moshaf = r.get("moshaf", [{}])[0] # نأخذ المصحف الأول المتاح
            server = moshaf.get("server")
            surah_list = moshaf.get("surah_list", "")
            
            if name and server and surah_list:
                reciters_dict[name] = {
                    "server": server,
                    "surah_list": surah_list.split(",")
                }
        return reciters_dict
    except Exception as e:
        logging.error(f"Error fetching reciters: {e}")
        return {}

# تحميل البيانات عند الإقلاع
RECITERS_DATA = get_all_reciters()
RECITERS_NAMES = list(RECITERS_DATA.keys())

# أسماء السور مرتبة مصحفياً
SURAH_NAMES = [
    "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التكوير", "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد", "الشمس", "الليل", "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات", "القارعة", "التكاثر", "العصر", "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"
]

ITEMS_PER_PAGE = 8
user_states = {}

# دالة لبناء أزرار القراء المقسمة إلى صفحات
def build_reciters_keyboard(page: int):
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_items = RECITERS_NAMES[start_idx:end_idx]
    
    # أزرار القراء (أزرار شفافة مدمجة للتنقل السلس)
    keyboard = []
    for name in page_items:
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"reciter_{name}")])
    
    # أزرار التحكم بالصفحات
    navigation_row = []
    if page > 0:
        navigation_row.append(InlineKeyboardButton(text="⬅️ السابق", callback_data=f"page_{page-1}"))
    if end_idx < len(RECITERS_NAMES):
        navigation_row.append(InlineKeyboardButton(text="التالي ➡️", callback_data=f"page_{page+1}"))
        
    if navigation_row:
        keyboard.append(navigation_row)
        
    return InlineKeyboardMarkup(keyboard)

# دالة الترحيب /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_user = await context.bot.get_me()
    share_url = f"https://t.me{bot_user.username}&text=✨ أقدم لك بوت القرآن الكريم كاملاً لعشرات القراء العذبين. غذاء للأرواح وشفاء لما في الصدور. ساهم في نشره ليكون لك صدقة جارية! 📖"
    
    # رسالة ترحيبية ملهمة وقوية لموحدين
    welcome_text = (
        "✨ **غِذَاءُ أَرْوَاحِ المُوَحِّدِينَ وَشِفَاءُ الصُّدُورِ** ✨\n\n"
        "مرحباً بك يا باغي الخير في رحاب كلام اللهِ المَنّان. "
        "هنا تجد ضالّتك وتطمئنُّ روحك بالاستماع إلى آيات الذكر الحكيم "
        "بأصواتٍ خاشعة وعذبة تهتزّ لها القلوب وتدمع لها العيون.\n\n"
        "قال تعالى: ﴿الَّذِينَ آمَنُوا وَتَطْمَئِنُّ قُلُوبُهُم بِذِكْرِ اللَّهِ ۗ أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾.\n\n"
        "👇 **اختر الآن قارئك المفضل وابدأ رحلة اليقين:**"
    )
    
    # زر مشاركة البوت
    share_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="📢 مشاركة البوت ونشر الأجر", url=share_url)]
    ])
    
    # إرسال الرسالة الملهمة أولاً مع زر المشاركة
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=share_keyboard)
    
    # ثم إرسال قائمة القراء المقسمة لصفحات
    reciters_keyboard = build_reciters_keyboard(0)
    await update.message.reply_text("📖 **قائمة القراء الأفاضل (الصفحة 1):**", parse_mode="Markdown", reply_markup=reciters_keyboard)

# معالجة النقر على الأزرار الشفافة (الصفحات واختيار القراء)
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # 1. التنقل بين صفحات القراء
    if data.startswith("page_"):
        page = int(data.split("_")[1])
        keyboard = build_reciters_keyboard(page)
        await query.edit_message_text(text=f"📖 **قائمة القراء الأفاضل (الصفحة {page+1}):**", parse_mode="Markdown", reply_markup=keyboard)

    # 2. عند اختيار قارئ محدد
    elif data.startswith("reciter_"):
        reciter_name = data.replace("reciter_", "")
        user_states[user_id] = reciter_name
        available_surahs = RECITERS_DATA[reciter_name]["surah_list"]
        
        # إنشاء أزرار رد عادية (Reply Keyboard) للسور لسهولة التصفح داخل شاشة الكتابة
        keyboard = []
        for idx, surah_name in enumerate(SURAH_NAMES, start=1):
            if str(idx) in available_surahs or f"{idx:03d}" in available_surahs:
                keyboard.append([surah_name])
                
        keyboard.append(["⬅️ العودة لقائمة القراء"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, placeholder="اختر السورة")
        
        await context.bot.send_message(
            chat_id=user_id, 
            text= f"🌿 لقد اخترت الاستماع إلى: *{reciter_name}*\n📖 اختر السورة الكريمة الآن من الأزرار بالأسفل:", 
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

# معالجة رسائل السور وأزرار العودة العادية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "⬅️ العودة لقائمة القراء":
        user_states.pop(user_id, None)
        reciters_keyboard = build_reciters_keyboard(0)
        await update.message.reply_text("📖 **قائمة القراء الأفاضل (الصفحة 1):**", parse_mode="Markdown", reply_markup=reciters_keyboard)

    elif text in SURAH_NAMES:
        current_reader = user_states.get(user_id)
        if current_reader:
            surah_index = SURAH_NAMES.index(text) + 1
            surah_number_str = str(surah_index).zfill(3)
            
            server_url = RECITERS_DATA[current_reader]["server"]
            audio_url = f"{server_url}{surah_number_str}.mp3"
            
            await update.message.reply_text(f"⏳ جاري جلب تلاوة سورة *{text}* بصوت الشيخ *{current_reader}*...", parse_mode="Markdown")
            try:
                await update.message.reply_audio(audio=audio_url, title=text, performer=current_reader)
            except Exception:
                await update.message.reply_text("❌ عذراً، تعذر جلب الملف الصوتي من السيرفر الرئيسي حالياً.")
    else:
        await update.message.reply_text("⚠️ يرجى استخدام الأزرار المتاحة للتنقل.")

def main():
    if not TOKEN:
        print("خطأ: لم يتم ضبط متغير TELEGRAM_TOKEN البيئي")
        return
        
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("البوت المطور يعمل الآن بنجاح...")
    application.run_polling()

if __name__ == "__main__":
    main()
