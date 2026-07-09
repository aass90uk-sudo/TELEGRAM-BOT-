import os
import json
import random
import asyncio
from datetime import datetime
from pytz import timezone
from hijri_converter import Gregorian
from telegram import Bot

# الإعدادات
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
LOCAL_TZ = timezone("Asia/Riyadh") # توقيت مكة المكرمة

bot = Bot(token=TOKEN)

def get_hijri_date():
    now_local = datetime.now(LOCAL_TZ)
    hijri = Gregorian(now_local.year, now_local.month, now_local.day).to_hijri()
    months = ["محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة", "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]
    return f"📅 {hijri.day} {months[hijri.month - 1]} {hijri.year} هـ"

# دالة سحب محتوى عشوائي من ملف الـ JSON
def get_random_content(content_type):
    try:
        with open("content.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        return random.choice(data[content_type])
    except Exception as e:
        print(f"خطأ في قراءة ملف JSON: {e}")
        return None

async def send_post(content_type):
    text = get_random_content(content_type)
    if not text:
        return
    
    full_message = f"{get_hijri_date()}\n\n{text}"
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=full_message, parse_mode="Markdown")
        print(f"تم نشر {content_type} بنجاح!")
    except Exception as e:
        print(f"خطأ أثناء النشر: {e}")

async def scheduler_loop():
    print("البوت يعمل الآن ومستمر في مراقبة الوقت...")
    
    # 🚀 رسالة التجربة الفورية المدمجة جاهزة (ستنشر فوراً بالقناة للتأكد من عمل البوت)
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text="⚡ تم تشغيل البوت بنجاح وهو متصل بالقناة الآن!")
        print("تم إرسال رسالة التجربة بنجاح!")
    except Exception as e:
        print(f"خطأ في رسالة التجربة: {e}")

    while True:
        now = datetime.now(LOCAL_TZ)
        current_time = now.strftime("%H:%M")

        # مواعيد النشر اليومية بدقة
        if current_time == "06:00":
            await send_post("azkar_sabah")
            await asyncio.sleep(60)
        elif current_time == "08:00":
            await send_post("stories_sabah")
            await asyncio.sleep(60)
        elif current_time == "17:00":
            await send_post("azkar_masa")
            await asyncio.sleep(60)
        elif current_time == "21:30":
            await send_post("stories_masa")
            await asyncio.sleep(60)

        await asyncio.sleep(30) # فحص الوقت كل نصف دقيقة

if __name__ == "__main__":
    asyncio.run(scheduler_loop())
    
