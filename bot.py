# requirements:
# python-telegram-bot==20.7
# Run with: python bot.py

import os, json, datetime as dt
from zoneinfo import ZoneInfo
from typing import Dict, Any
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise SystemExit("Environment variable BOT_TOKEN is not set. Please set it to your @BotFather token.")

DATA_FILE = "users.json"
KYIV_TZ = ZoneInfo("Europe/Kyiv")

# ---------- Persistence ----------
def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"users": {}}

def save_data(data: Dict[str, Any]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- Program Logic ----------
WEEK_FOCUS = {
    1: "Активація печінки й стабілізація щитоподібки",
    2: "Запуск жовчовиділення і травлення",
    3: "Виведення естрогенів (DIM/I3C)",
    4: "Глибока детоксикація + антиоксиданти",
    5: "Відновлення мікробіому і стабілізація гормонів",
    6: "Закріплення ефекту + підтримка наднирників",
}

def day_plan(day_number: int) -> str:
    """Return checklist text for given day (1..42)."""
    week = (day_number - 1) // 7 + 1
    base_morning = "• Після сніданку: Thyrocsin (2 капс), D3+K2 (1), Омега-3 (2000 мг), зелений чай"
    base_day = "• Обід: NAC 600 мг, Куркумін 500 мг, + білок (риба/м’ясо) і овочі"
    base_even = "• Вечір: Магній, Таурин 500–1000 мг, Примула, Пробіотик перед сном"

    if week == 1:
        add_morning = ""
        add_day = "• Травлення: Артишок / чай з кульбаби після їжі"
        add_even = "• 15 хв прогулянка або легка розтяжка"
    elif week == 2:
        add_morning = "• Вранці вода з лимоном + дрібка солі"
        add_day = "• Додай буряковий салат або квашену капусту"
        add_even = "• Клітковина: 1 ст. ложка льону/чіа"
    elif week == 3:
        add_morning = "• DIM 100 мг після сніданку"
        add_day = "• Броколі/капустяні щодня"
        add_even = "• Дихання 4-7-8, 10 хв перед сном"
    elif week == 4:
        add_morning = "• DIM 100 мг + Вітамін C 500 мг"
        add_day = "• Розторопша 200–400 мг"
        add_even = "• Тепла ванна/сауна (1–2 рази цього тижня)"
    elif week == 5:
        add_morning = "• DIM або I3C (за наявності)"
        add_day = "• Клітковина щодня + капустяні"
        add_even = "• Тепле молоко/чай з гліцином перед сном (за бажання)"
    else:  # week 6
        add_morning = ""
        add_day = "• Рух 30 хв/день (мінімум 6000–8000 кроків)"
        add_even = "• Запиши 3 речі, за які вдячна"

    text = (
        f"День {day_number} • Тиждень {week}: {WEEK_FOCUS[week]}"
        f"\n\n🌞 Ранок\n{base_morning}"
        + (f"\n{add_morning}" if add_morning else "") +
        f"\n\n🍽️ День\n{base_day}\n{add_day}"
        f"\n\n🌙 Вечір\n{base_even}\n{add_even}"
        "\n\n💧 Вода 30 мл/кг, 10 хв ходьби після кожного прийому їжі, без кави натще."
    )
    return text

def calc_day_number(start_date: str) -> int:
    s = dt.date.fromisoformat(start_date)
    today = dt.datetime.now(KYIV_TZ).date()
    return (today - s).days + 1

# ---------- Bot Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    chat_id = str(update.effective_chat.id)
    today_iso = dt.datetime.now(KYIV_TZ).date().isoformat()

    if chat_id not in data["users"]:
        data["users"][chat_id] = {"start_date": today_iso, "time": "09:00"}
        save_data(data)
        await update.message.reply_text(
            "Привіт! Я нагадаю тобі щодня про програму “Estrogen & Liver Reset”. "
            "Старт сьогодні. Час нагадувань: 09:00 (Europe/Kyiv). "
            "Можеш змінити командою /set_time HH:MM (напр., /set_time 08:30). "
            "Команди: /today, /week, /set_time, /stop, /help"
        )
    else:
        await update.message.reply_text("Я вже активований. Команди: /today, /week, /set_time, /stop, /help")
    await schedule_reminder_for_user(context, chat_id)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команди:\n"
        "/today — чекліст на сьогодні\n"
        "/week — фокус поточного тижня\n"
        "/set_time HH:MM — змінити час щоденного нагадування\n"
        "/stop — вимкнути нагадування\n"
        "/start — увімкнути та запланувати знову"
    )

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    chat_id = str(update.effective_chat.id)
    if chat_id not in data["users"]:
        await update.message.reply_text("Спочатку натисни /start")
        return
    day = calc_day_number(data["users"][chat_id]["start_date"])
    day = max(1, min(42, day))
    await update.message.reply_text(day_plan(day))

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    chat_id = str(update.effective_chat.id)
    if chat_id not in data["users"]:
        await update.message.reply_text("Спочатку натисни /start")
        return
    day = calc_day_number(data["users"][chat_id]["start_date"])
    day = max(1, min(42, day))
    week_num = (day - 1)//7 + 1
    await update.message.reply_text(f"Тиждень {week_num}: {WEEK_FOCUS[week_num]}")

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    chat_id = str(update.effective_chat.id)
    if chat_id not in data["users"]:
        await update.message.reply_text("Спочатку натисни /start")
        return
    if not context.args or len(context.args[0]) != 5 or context.args[0][2] != ":":
        await update.message.reply_text("Формат: /set_time HH:MM (наприклад, 08:30)")
        return
    hh, mm = context.args[0].split(":")
    try:
        hh, mm = int(hh), int(mm)
        assert 0 <= hh < 24 and 0 <= mm < 60
    except Exception:
        await update.message.reply_text("Формат: /set_time HH:MM (наприклад, 08:30)")
        return
    data["users"][chat_id]["time"] = f"{hh:02d}:{mm:02d}"
    save_data(data)
    await update.message.reply_text(f"Готово. Щоденні нагадування о {hh:02d}:{mm:02d} (Europe/Kyiv).")
    await schedule_reminder_for_user(context, chat_id, reschedule=True)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    chat_id = str(update.effective_chat.id)
    if chat_id in data["users"]:
        job_name = f"daily_{chat_id}"
        for job in context.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()
        await update.message.reply_text("Нагадування вимкнено. Повернути — /start")
    else:
        await update.message.reply_text("Активних нагадувань не знайдено.")

# ---------- Scheduling ----------
async def schedule_reminder_for_user(context: ContextTypes.DEFAULT_TYPE, chat_id: str, reschedule: bool=False):
    data = load_data()
    if chat_id not in data["users"]:
        return
    job_name = f"daily_{chat_id}"
    for job in context.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()
    time_str = data["users"][chat_id]["time"]
    hour, minute = map(int, time_str.split(":"))
    when = dt.time(hour=hour, minute=minute, tzinfo=ZoneInfo("Europe/Kyiv"))
    context.job_queue.run_daily(send_daily, time=when, data={"chat_id": chat_id}, name=job_name)

async def send_daily(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.data["chat_id"]
    data = load_data()
    if chat_id not in data["users"]:
        return
    day = calc_day_number(data["users"][chat_id]["start_date"])
    if day > 42:
        await context.bot.send_message(chat_id=chat_id,
            text=("🎉 6 тижнів завершено! Перехід у стабілізаційну фазу: "
                  "продовжуй базу (Thyrocsin, D3, Омега, Mg); NAC та DIM — 5 днів/тиж у знижених дозах; "
                  "розторопша/куркумін — курсами 2 тиж/міс. "
                  "За бажанням перезапусти /start, щоб почати новий цикл."))
        for j in context.job_queue.get_jobs_by_name(job.name):
            j.schedule_removal()
        return
    day = max(1, day)
    await context.bot.send_message(chat_id=chat_id, text=day_plan(day))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("set_time", set_time))
    app.add_handler(CommandHandler("stop", stop))
    app.job_queue
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
