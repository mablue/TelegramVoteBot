import logging
import sqlite3
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import csv
import os
from datetime import datetime
import os
TOKEN = os.environ.get('TOKEN')

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# تنظیمات دیتابیس
DB_NAME = "movie_poll.db"

def init_database():
    """ایجاد جداول دیتابیس"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # جدول فیلم‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول رای‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            movie_id TEXT NOT NULL,
            voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (movie_id) REFERENCES movies (id),
            UNIQUE(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def load_movies_from_csv():
    """بارگذاری فیلم‌ها از فایل CSV"""
    movies = {}
    try:
        with open('movies.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    movie_id = row[0].strip()
                    title = row[1].strip()
                    if movie_id and title:
                        movies[movie_id] = title
    except FileNotFoundError:
        logging.warning("فایل movies.csv یافت نشد")
    
    return movies

def sync_movies_to_db():
    """همگام‌سازی فیلم‌ها از CSV به دیتابیس"""
    csv_movies = load_movies_from_csv()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # دریافت فیلم‌های موجود در دیتابیس
    cursor.execute("SELECT id, title FROM movies")
    db_movies = {row[0]: row[1] for row in cursor.fetchall()}
    
    # اضافه کردن فیلم‌های جدید
    for movie_id, title in csv_movies.items():
        if movie_id not in db_movies:
            cursor.execute(
                "INSERT INTO movies (id, title) VALUES (?, ?)",
                (movie_id, title)
            )
            logging.info(f"فیلم جدید اضافه شد: {movie_id} - {title}")
        elif db_movies[movie_id] != title:
            cursor.execute(
                "UPDATE movies SET title = ? WHERE id = ?",
                (title, movie_id)
            )
            logging.info(f"فیلم بروزرسانی شد: {movie_id} - {title}")
    
    # حذف فیلم‌هایی که در CSV نیستند (اما رای دارند)
    # برای ایمنی، فقط فیلم‌های بدون رای حذف می‌شوند
    for db_id in db_movies:
        if db_id not in csv_movies:
            cursor.execute("SELECT COUNT(*) FROM votes WHERE movie_id = ?", (db_id,))
            vote_count = cursor.fetchone()[0]
            if vote_count == 0:
                cursor.execute("DELETE FROM movies WHERE id = ?", (db_id,))
                logging.info(f"فیلم حذف شد: {db_id}")
    
    conn.commit()
    conn.close()

def get_movies_from_db():
    """دریافت فیلم‌ها از دیتابیس"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM movies ORDER BY created_at")
    movies = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return movies

def get_vote_counts():
    """دریافت تعداد رای‌های هر فیلم"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT movie_id, COUNT(*), GROUP_CONCAT(user_name) 
        FROM votes 
        GROUP BY movie_id
    ''')
    vote_data = {}
    for movie_id, count, user_names in cursor.fetchall():
        vote_data[movie_id] = {
            'count': count,
            'voters': user_names.split(',') if user_names else []
        }
    conn.close()
    return vote_data

def add_vote(user_id, user_name, movie_id):
    """افزودن رای جدید"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # حذف رای قبلی کاربر اگر وجود دارد
        cursor.execute("DELETE FROM votes WHERE user_id = ?", (user_id,))
        
        # افزودن رای جدید
        cursor.execute(
            "INSERT INTO votes (user_id, user_name, movie_id) VALUES (?, ?, ?)",
            (user_id, user_name, movie_id)
        )
        
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"خطا در ثبت رای: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_user_vote(user_id):
    """دریافت رای کاربر"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT movie_id FROM votes WHERE user_id = ?", 
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# ساخت منوی شیشه‌ای
def create_movie_keyboard():
    movies = get_movies_from_db()
    vote_data = get_vote_counts()
    
    keyboard = []
    row = []
    
    for i, (movie_id, title) in enumerate(movies.items()):
        vote_count = vote_data.get(movie_id, {}).get('count', 0)
        
        # کوتاه کردن عنوان اگر طولانی باشد
        short_title = title[:30] + "..." if len(title) > 30 else title
        
        button_text = f"{vote_count}👍{short_title}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"vote_{movie_id}"))
        
        # هر 2 دکمه در یک ردیف (به دلیل طولانی بودن عنوان‌ها)
        if (i + 1) % 1 == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

# ساخت متن لیست فیلم‌ها با رای‌دهندگان
def create_movies_list_text():
    movies = get_movies_from_db()
    vote_data = get_vote_counts()
    
    text = "🎬 **لیست فیلم‌ها و رای‌ها:**\n\n"
    
    for movie_id, title in movies.items():
        votes_info = vote_data.get(movie_id, {})
        vote_count = votes_info.get('count', 0)
        voters = votes_info.get('voters', [])
        
        text += f"**{title}**\n"
        text += f"👥 **{vote_count}** رای"
        
        if voters:
            text += " | "
            display_voters = voters[:3]
            text += "رای‌دهندگان: " + ", ".join(display_voters)
            if len(voters) > 3:
                text += f" و {len(voters) - 3} نفر دیگر"
        
        text += "\n\n"
    
    return text

# دستور start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"سلام {user.first_name}! 👋\n\n"
        "به نظرسنجی فیلم‌ها خوش اومدی!\n"
        "روی دکمه‌های زیر کلیک کن تا به فیلم مورد علاقت رای بدی.\n"
        "**توجه: هر نفر فقط می‌تونه به یک فیلم رای بده!**\n\n"
        "برای مشاهده نتایج از دستور /results استفاده کن."
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=create_movie_keyboard(),
        parse_mode='Markdown'
    )

# هندلر برای رای‌ دادن
async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = str(user.id)
    user_name = user.first_name
    
    await query.answer()
    
    # استخراج آیدی فیلم از callback_data
    movie_id = query.data.replace('vote_', '')
    
    movies = get_movies_from_db()
    movie_title = movies.get(movie_id, "فیلم ناشناخته")
    
    # بررسی رای قبلی کاربر
    previous_vote = get_user_vote(user_id)
    
    # ثبت رای جدید
    success = add_vote(user_id, user_name, movie_id)
    
    if success:
        if previous_vote:
            previous_title = movies.get(previous_vote, "فیلم قبلی")
            message = f"✅ رای شما از **{previous_title}** به **{movie_title}** تغییر کرد!"
        else:
            message = f"🎉 رای شما به **{movie_title}** ثبت شد!"
        
        await query.edit_message_text(
            text=message + "\n\n" + create_movies_list_text(),
            reply_markup=create_movie_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            text="❌ خطا در ثبت رای! لطفاً دوباره تلاش کنید.",
            reply_markup=create_movie_keyboard()
        )

# دستور نمایش نتایج
async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        create_movies_list_text(),
        parse_mode='Markdown',
        reply_markup=create_movie_keyboard()
    )

# دستور ریلود فیلم‌ها
async def reload_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sync_movies_to_db()
    await update.message.reply_text(
        "✅ لیست فیلم‌ها با موفقیت بروزرسانی شد!",
        reply_markup=create_movie_keyboard()
    )

# دستور وضعیت سیستم
async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movies = get_movies_from_db()
    vote_data = get_vote_counts()
    total_votes = sum(data['count'] for data in vote_data.values())
    
    status_text = (
        f"📊 **وضعیت سیستم:**\n"
        f"• تعداد فیلم‌ها: {len(movies)}\n"
        f"• مجموع رای‌ها: {total_votes}\n"
        f"• آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

def main():
    # راه‌اندازی دیتابیس
    init_database()
    sync_movies_to_db()
    
    # توکن بات
    # TOKEN = "xxxxxxx:xxxxxxxxxxxxxxxxxxxxxxxxxxx" # توکن ربات خود را اینجا وارد کنید
    
    application = Application.builder().token(TOKEN).build()
    
    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("results", show_results))
    application.add_handler(CommandHandler("reload", reload_movies))
    application.add_handler(CommandHandler("status", system_status))
    application.add_handler(CallbackQueryHandler(handle_vote, pattern="^vote_"))
    
    # شروع بات
    print("🎬 Bot is running with SQLite database...")
    application.run_polling()

if __name__ == '__main__':
    main()
