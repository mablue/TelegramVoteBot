برای اینکه بات رو در گروه استارت کنی و پیام رای‌گیری رو بفرسته، دو روش داری:

روش ۱: دستی در گروه

در گروه تایپ کن:

```
/start@YourBotUsername
```

(بجای YourBotUsername یوزرنیم واقعی باتت رو بنویس)

روش ۲: اتوماتیک با کد

کد بات رو به این شکل آپدیت کن (بخش main رو تغییر بده):

```python
async def post_voting_message(application):
    """ارسال پیام رای‌گیری به گروه"""
    try:
        # آیدی عددی گروه رو اینجا قرار بده
        GROUP_CHAT_ID = "-1001234567890"  # جایگزین کن با آیدی واقعی گروه
        
        message_text = (
            "🎬 **نظرسنجی فیلم این هفته**\n\n"
            "برای انتخاب فیلم مورد علاقتون روی دکمه زیر کلیک کنید:\n"
            "هر نفر فقط می‌تونه به یک فیلم رای بده!"
        )
        
        await application.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=message_text,
            reply_markup=create_movie_keyboard(),
            parse_mode='Markdown'
        )
        print("✅ پیام رای‌گیری با موفقیت ارسال شد")
    except Exception as e:
        print(f"❌ خطا در ارسال پیام: {e}")

def main():
    # راه‌اندازی دیتابیس
    init_database()
    sync_movies_to_db()
    
    # توکن بات
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    application = Application.builder().token(TOKEN).build()
    
    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("results", show_results))
    application.add_handler(CommandHandler("reload", reload_movies))
    application.add_handler(CommandHandler("status", system_status))
    application.add_handler(CallbackQueryHandler(handle_vote, pattern="^vote_"))
    
    # ارسال پیام به گروه بعد از راه‌اندازی
    application.run_polling()
    
    # بعد از run_polling این خط اجرا نمیشه، پس بهتره از روش زیر استفاده کنی
```

روش ۳: دستور جدید برای ادمین

این کد رو به بات اضافه کن:

```python
# دستور برای ارسال پیام رای‌گیری در گروه (فقط برای ادمین)
async def broadcast_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بررسی ادمین بودن (آیدی عددی خودت رو اینجا قرار بده)
    ADMIN_IDS = [123456789, 987654321]  # جایگزین کن با آیدی عددی ادمین‌ها
    
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ فقط ادمین‌ها می‌تونن از این دستور استفاده کنن!")
        return
    
    try:
        # اگر آیدی گروه رو مستقیم بدی
        group_id = "-1001234567890"  # آیدی گروه
        
        message_text = (
            "🎬 **نظرسنجی فیلم این هفته**\n\n"
            "برای انتخاب فیلم مورد علاقتون روی دکمه‌ها کلیک کنید:\n"
            "• هر نفر فقط یک رای مجاز\n"
            "• با کلیک جدید، رای قبلی جایگزین می‌شود\n"
            "• برای نتایج: /results"
        )
        
        await context.bot.send_message(
            chat_id=group_id,
            text=message_text,
            reply_markup=create_movie_keyboard(),
            parse_mode='Markdown'
        )
        await update.message.reply_text("✅ پیام رای‌گیری با موفقیت ارسال شد!")
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال: {e}")

# به بخش هندلرها اضافه کن:
application.add_handler(CommandHandler("poll", broadcast_poll))
```

نحوه استفاده:

1. آیدی گروه رو پیدا کن:
   · بات رو به گروه اضافه کن
   · یه پیام بفرست
   · برو به آدرس: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   · آیدی عددی گروه رو پیدا کن (مثل -1001234567890)
2. در گروه از بات استفاده کن:
   · به عنوان ادمین در گروه: /poll
   · یا مستقیم: /start@YourBotUsername

پیشنهاد: روش ۳ رو پیاده‌سازی کن که کنترل بهتری داری! 🚀
