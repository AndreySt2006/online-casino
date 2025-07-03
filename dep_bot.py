import random
import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

TOKEN = "7528291323:AAHqqZ3j87uJIYnLMka2sHitcLUP-WQ_JUk"

user_data = {}
active_games = {}
SLOTS = ["🍒", "🍋", "🍇", "💎", "🔔", "7️⃣"]

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 КРУТИТЬ", callback_data="spin")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance"),
         InlineKeyboardButton("🎁 Бонус", callback_data="daily")],
        [InlineKeyboardButton("🤝 Multiplayer", callback_data="multiplayer")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data.setdefault(user.id, {
        "balance": 100,
        "last_daily": None,
        "username": user.username or f"user_{user.id}"
    })
    await update.message.reply_text(
        f"🎉 Привет, {user.first_name}! Добро пожаловать в Dep Casino SlotBot! 🎰\n"
        f"У тебя есть 💰100 очков.\n\nВыбирай действие ниже 👇",
        reply_markup=main_menu()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    data = user_data.setdefault(user.id, {
        "balance": 100,
        "last_daily": None,
        "username": user.username or f"user_{user.id}"
    })
    if query.data == "balance":
        await query.edit_message_text(
            f"💼 Твой баланс: {data['balance']} очков",
            reply_markup=main_menu()
        )
    elif query.data == "daily":
        now = datetime.datetime.now()
        if data["last_daily"] and (now - data["last_daily"]).days < 1:
            await query.edit_message_text("⏳ Ты уже получал бонус сегодня!", reply_markup=main_menu())
        else:
            bonus = random.choice([10, 20, 30, 50])
            data["balance"] += bonus
            data["last_daily"] = now
            await query.edit_message_text(f"🎁 Ты получил бонус: +{bonus} очков!", reply_markup=main_menu())
    elif query.data == "spin":
        if data["balance"] < 10:
            await query.edit_message_text("🚫 Недостаточно очков для крутки. Попробуй /daily!", reply_markup=main_menu())
            return
        data["balance"] -= 10
        slot_result = [random.choice(SLOTS) for _ in range(3)]
        if slot_result[0] == slot_result[1] == slot_result[2]:
            win = 100
            msg = "🎉 Джекпот!"
        else:
            win = 0
            msg = "🙁 Ничего не выпало..."
        data["balance"] += win
        result = f"{slot_result[0]} {slot_result[1]} {slot_result[2]}\n\n{msg}\n💰 Баланс: {data['balance']}"
        await query.edit_message_text(result, reply_markup=main_menu())
    elif query.data == "multiplayer":
        await query.edit_message_text(
            "🤝 Чтобы вызвать игрока на мультиплеер, используй команду:\n"
            "/challenge @username ставка\n\n"
            "Например: /challenge @player 20",
            reply_markup=main_menu()
        )

async def dep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user
    args = context.args
    if len(args) != 2 or not args[1].isdigit():
        await update.message.reply_text("❗ Используй команду так:\n/dep @username количество")
        return
    target_username = args[0].lstrip('@')
    amount = int(args[1])
    if amount <= 0:
        await update.message.reply_text("❗ Укажи положительное количество очков")
        return
    sender_data = user_data.setdefault(sender.id, {
        "balance": 100,
        "last_daily": None,
        "username": sender.username or f"user_{sender.id}"
    })
    if sender_data["balance"] < amount:
        await update.message.reply_text("🚫 Недостаточно очков")
        return
    target_id = None
    for uid, data in user_data.items():
        if data.get("username") == target_username:
            target_id = uid
            break
    if not target_id:
        await update.message.reply_text("❌ Пользователь не найден. Он должен хотя бы раз использовать /start.")
        return
    sender_data["balance"] -= amount
    user_data[target_id]["balance"] += amount
    await update.message.reply_text(
        f"✅ Ты задепал {amount} очков пользователю @{target_username}.\n"
        f"💰 Новый баланс: {sender_data['balance']}"
    )


async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user
    args = context.args
    if len(args) != 2 or not args[1].isdigit():
        await update.message.reply_text("❗ Используй команду так:\n/challenge @username ставка")
        return
    target_username = args[0].lstrip('@')
    bet = int(args[1])
    if bet <= 0:
        await update.message.reply_text("❗ Укажи положительную ставку")
        return
    sender_data = user_data.setdefault(sender.id, {
        "balance": 100,
        "last_daily": None,
        "username": sender.username or f"user_{sender.id}"
    })
    if sender_data["balance"] < bet:
        await update.message.reply_text("🚫 У тебя недостаточно очков для ставки")
        return
    target_id = None
    for uid, data in user_data.items():
        if data.get("username") == target_username:
            target_id = uid
            break
    if not target_id:
        await update.message.reply_text("❌ Пользователь не найден или он ещё не начал игру")
        return
    if target_id == sender.id:
        await update.message.reply_text("❗ Нельзя вызвать себя")
        return
    game_key = tuple(sorted([sender.id, target_id]))
    if game_key in active_games:
        await update.message.reply_text("❗ У вас уже есть активная игра!")
        return
    active_games[game_key] = {"bet": bet, "challenger": sender.id, "challenged": target_id, "results": {}}

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Принять", callback_data=f"accept_{sender.id}"),
         InlineKeyboardButton("Отклонить", callback_data=f"decline_{sender.id}")]
    ])

    await update.message.reply_text(
        f"🎰 Ты вызвал @{target_username} на игру в слоты с ставкой {bet} очков.\n"
        f"Ждём ответа...",
        reply_markup=main_menu()
    )
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"🎰 @{sender.username or sender.first_name} вызвал тебя на игру в слоты с ставкой {bet} очков.\n"
                f"Прими вызов или отклони его."
            ),
            reply_markup=keyboard
        )
    except Exception:
        await update.message.reply_text(
            f"❗ Не удалось отправить вызов @{target_username}. "
            f"Пусть он сначала напишет боту (нажмёт /start)."
        )


async def challenge_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    data = query.data
    action, challenger_id_str = data.split('_')
    challenger_id = int(challenger_id_str)
    game_key = tuple(sorted([user.id, challenger_id]))
    if game_key not in active_games:
        await query.edit_message_text("❗ Эта игра уже неактивна.")
        return
    game = active_games[game_key]
    if action == "decline":
        del active_games[game_key]
        await query.edit_message_text("❌ Вызов отклонён.")
        return
    challenger_data = user_data[challenger_id]
    challenged_data = user_data[user.id]
    bet = game["bet"]
    if challenger_data["balance"] < bet:
        del active_games[game_key]
        await query.edit_message_text("❌ У вызвавшего недостаточно очков для игры.")
        return
    if challenged_data["balance"] < bet:
        del active_games[game_key]
        await query.edit_message_text("❌ У тебя недостаточно очков для игры.")
        return
    challenger_data["balance"] -= bet
    challenged_data["balance"] -= bet
    game["turn"] = user.id
    await query.edit_message_text(
        f"✅ Игра началась! Каждый делает спин по очереди.\n"
        f"@{user_data[game['turn']]['username']}, твой ход. Нажми кнопку ниже.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎰 Спин", callback_data=f"multispin_{user.id}")]
        ])
    )

async def multi_spin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    found_game_key = None
    for key, game in active_games.items():
        if user.id in key and game.get("turn") == user.id:
            found_game_key = key
            break
    if not found_game_key:
        await query.answer("❗ Сейчас не твой ход или игра не найдена.", show_alert=True)
        return
    game = active_games[found_game_key]
    bet = game["bet"]
    slot_result = [random.choice(SLOTS) for _ in range(3)]
    if slot_result[0] == slot_result[1] == slot_result[2]:
        win = 100
        msg = "🎉 Джекпот!"
    else:
        win = 0
        msg = "🙁 Ничего не выпало..."
    game["results"][user.id] = win
    other_player = [pid for pid in found_game_key if pid != user.id][0]
    if other_player in game["results"]:
        first_player, second_player = found_game_key
        total_pot = bet * 2
        first_score = game["results"][first_player]
        second_score = game["results"][second_player]
        if first_score > second_score:
            winner = first_player
        elif second_score > first_score:
            winner = second_player
        else:
            winner = None
        if winner:
            user_data[winner]["balance"] += total_pot + first_score + second_score
            text = f"🎉 Победитель: @{user_data[winner]['username']}!\nРезультаты:\n"
        else:
            user_data[first_player]["balance"] += bet + first_score
            user_data[second_player]["balance"] += bet + second_score
            text = "🤝 Ничья! Ставки возвращены.\nРезультаты:\n"
        text += (f"@{user_data[first_player]['username']}: {first_score}\n"
                 f"@{user_data[second_player]['username']}: {second_score}\n"
                 f"💰 Балансы:\n@{user_data[first_player]['username']}: {user_data[first_player]['balance']}\n"
                 f"@{user_data[second_player]['username']}: {user_data[second_player]['balance']}")
        del active_games[found_game_key]
        await query.edit_message_text(f"{' '.join(slot_result)}\n{msg}\n\n{text}", reply_markup=main_menu())
    else:
        game["turn"] = other_player
        await query.edit_message_text(
            f"{' '.join(slot_result)}\n{msg}\n\nХод передан @{user_data[other_player]['username']}.\n"
            f"Нажми кнопку ниже, чтобы сыграть.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎰 Спин", callback_data=f"multispin_{other_player}")]
            ])
        )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dep", dep))
    app.add_handler(CommandHandler("challenge", challenge))
    app.add_handler(CallbackQueryHandler(challenge_response, pattern="^(accept|decline)_"))
    app.add_handler(CallbackQueryHandler(multi_spin_handler, pattern="^multispin_"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(balance|daily|spin|multiplayer)$"))
    print("🎰 Dep Casino SlotBot с мультиплеером запущен!")
    app.run_polling()
