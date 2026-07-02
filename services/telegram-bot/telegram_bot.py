import logging
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_BOT_ADMIN_CHAT_ID")

if not BOT_TOKEN:
    logger.critical("BOT_TOKEN is not set")
    sys.exit(1)
if not ADMIN_CHAT_ID:
    logger.critical("ADMIN_CHAT_ID is not set")
    sys.exit(1)

(
    WELCOME,
    PARTICIPANTS, WHO_TRAVELS,
    DATES, DEPARTURE_CITY,
    BUDGET,
    AIRLINE_PREF, FLIGHT_DURATION,
    LAYOVER, LUGGAGE, TRANSFER,
    TRIP_GOAL, ATMOSPHERE, HOTEL_STYLE,
    ACTIVITIES, DESIGN_STYLE,
    ACCOMMODATION_TYPE,
    SLEEP_SENSITIVITY, SLEEP_SCHEDULE,
    MEAL_PLAN, DIETARY, ALACARTE,
    CUISINE, OUTSIDE_WALK, BEACH_TYPE,
    BEACH_FEATURES, SPECIAL_WISHES, TOP_PRIORITIES,
    FIO, EMAIL, CONTACT_METHOD, CONTACT_LINK,
    DISCUSS_FORMAT,
) = range(33)

CONTACT_NEEDS_LINK = {"vk", "telegram_contact"}

TOTAL = 32


# ══════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ══════════════════════════════════════════════════════════════

def make_inline(options: list, cols: int = 1) -> InlineKeyboardMarkup:
    keyboard, row = [], []
    for opt in options:
        label, cb = opt if isinstance(opt, tuple) else (opt, opt)
        row.append(InlineKeyboardButton(label, callback_data=cb[:60]))
        if len(row) == cols:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


def make_multi_inline(options: list, selected: set, cols: int = 2) -> InlineKeyboardMarkup:
    keyboard, row = [], []
    for label, key in options:
        btn = f"✅  {label}" if key in selected else f"     {label}"
        row.append(InlineKeyboardButton(btn, callback_data=f"t:{key}"[:60]))
        if len(row) == cols:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✔️  Подтвердить выбор", callback_data="done")])
    return InlineKeyboardMarkup(keyboard)


def save(context, key, value):
    context.user_data[key] = value


async def _delete_msg(bot, chat_id, msg_id):
    if not msg_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass


async def ask(context, chat_id, text, markup=None):
    await _delete_msg(context.bot, chat_id, context.user_data.get('last_bot_msg_id'))
    sent = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
    context.user_data['last_bot_msg_id'] = sent.message_id
    return sent


async def del_user_msg(message):
    try:
        await message.delete()
    except Exception:
        pass


def step(n):
    return f"Шаг {n} из {TOTAL}\n"


def get_answers(ud: dict) -> str:
    lines = [
        "✨ НОВАЯ АНКЕТА ДЛЯ ПОДБОРА ОТДЫХА ✨\n",
        f"👤  ФИО:                 {ud.get('fio', '—')}",
        f"📧  Email:               {ud.get('email', '—')}",
        f"📲  Способ связи:        {ud.get('contact_method', '—')}",
        f"🔗  Контакт:             {ud.get('contact_link', '—')}",
        f"🗣  Формат общения:      {ud.get('discuss_format', '—')}",
        "",
        f"👥  Участники тура:      {ud.get('participants', '—')}",
        f"🧑‍🤝‍🧑  Кто едет:             {ud.get('who_travels', '—')}",
        f"💰  Бюджет:              {ud.get('budget', '—')}",
        f"✈️  Город вылета:        {ud.get('departure_city', '—')}",
        f"📅  Даты / ночей:        {ud.get('dates', '—')}",
        "",
        f"🛫  Авиакомпании:        {ud.get('airline_pref', '—')}",
        f"⏱  Длительность:        {ud.get('flight_duration', '—')}",
        f"🔄  Пересадки:           {ud.get('layover', '—')}",
        f"🧳  Багаж:               {ud.get('luggage', '—')}",
        f"🚐  Трансфер:            {ud.get('transfer', '—')}",
        "",
        f"🎯  Цель поездки:        {ud.get('trip_goal', '—')}",
        f"🌴  Атмосфера:           {ud.get('atmosphere', '—')}",
        f"🏨  Важно в отеле:       {ud.get('hotel_style', '—')}",
        f"🏄  Активности:          {ud.get('activities', '—')}",
        f"🎨  Стиль дизайна:       {ud.get('design_style', '—')}",
        f"🛏  Размещение:          {ud.get('accommodation_type', '—')}",
        f"😴  Чуткий сон:          {ud.get('sleep_sensitivity', '—')}",
        f"🌙  Сова / жаворонок:    {ud.get('sleep_schedule', '—')}",
        "",
        f"🍽  Питание:             {ud.get('meal_plan', '—')}",
        f"🥗  Диеты / аллергии:    {ud.get('dietary', '—')}",
        f"🍷  А-ля-карт:           {ud.get('alacarte', '—')}",
        f"🍜  Кухня:               {ud.get('cuisine', '—')}",
        f"🚶  Выход за отель:      {ud.get('outside_walk', '—')}",
        f"🏝  Тип пляжа:           {ud.get('beach_type', '—')}",
        f"⛱  Пляж — детали:       {ud.get('beach_features', '—')}",
        "",
        f"💫  Особые пожелания:    {ud.get('special_wishes', '—')}",
        f"⭐️  Важное и доп.:       {ud.get('top_priorities', '—')}",
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# HANDLERS
# ══════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) == ADMIN_CHAT_ID:
        return ConversationHandler.END

    context.user_data.clear()
    sent = await update.message.reply_text(
        "🌴  Добро пожаловать!\n\n"
        "Я помогу подобрать идеальный отдых именно для вас.\n"
        "Заполните короткую анкету — это займёт всего несколько минут 🚀\n\n"
        "Нажмите кнопку ниже, чтобы начать 👇",
        reply_markup=make_inline([("🚀  Начать анкету", "begin")])
    )
    context.user_data['last_bot_msg_id'] = sent.message_id
    return WELCOME


async def welcome_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    opts = [
        ("💑  Партнёр / супруг(а)", "partner"),
        ("👶  Дети",                 "kids"),
        ("👯  Друзья / подруги",    "friends"),
        ("🚶  В одиночестве",      "solo"),
    ]
    context.user_data['who_opts'] = opts
    context.user_data['who_sel'] = set()
    await query.edit_message_text(
        step(1)
        + "👥  Укажите количество участников тура и возраст детей\n"
          "(например: 2 взрослых + 1 ребёнок 6 лет)"
    )
    context.user_data['last_bot_msg_id'] = query.message.message_id
    return PARTICIPANTS


async def participants_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'participants', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    opts = [
        ("💑  Партнёр / супруг(а)", "partner"),
        ("👶  Дети",                 "kids"),
        ("👯  Друзья / подруги",    "friends"),
        ("🚶  В одиночестве",      "solo"),
    ]
    context.user_data['who_opts'] = opts
    context.user_data['who_sel'] = set()
    await ask(context, chat_id,
        step(2)
        + "🧑‍🤝‍🧑  Кто будет с вами в поездке?\n(можно выбрать несколько)",
        make_multi_inline(opts, set(), cols=1)
    )
    return WHO_TRAVELS


async def who_travels_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    opts = context.user_data.get('who_opts', [])
    sel  = context.user_data.get('who_sel', set())
    key_to_label = {k: l for l, k in opts}

    if query.data == "done":
        if not sel:
            await query.answer("Выберите хотя бы один вариант!", show_alert=True)
            return WHO_TRAVELS
        val = ", ".join(key_to_label.get(k, k) for k in sel)
        save(context, 'who_travels', val)
        await query.edit_message_text(
            f"Выбрано: {val}\n\n"
            + step(3)
            + "📅  Даты поездки и количество дней / ночей:"
        )
        context.user_data['last_bot_msg_id'] = query.message.message_id
        return DATES
    else:
        k = query.data.replace("t:", "")
        if k in sel: sel.discard(k)
        else: sel.add(k)
        context.user_data['who_sel'] = sel
        await query.edit_message_reply_markup(reply_markup=make_multi_inline(opts, sel, cols=1))
        return WHO_TRAVELS


async def budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'budget', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(26)
        + "💫  Особые пожелания или мечты?\n"
          "(предложение руки и сердца, день рождения и т.д.)\n"
          "Если нет — напишите «нет»"
    )
    return SPECIAL_WISHES


async def dates_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'dates', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(4)
        + "✈️  Укажите город вылета / прилёта:"
    )
    return DEPARTURE_CITY


async def departure_city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'departure_city', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    opts = [
        ("😌  Полный релакс",        "relax"),
        ("✨  Смена обстановки",      "inspiration"),
        ("🏃  Активный / экскурсии", "active"),
        ("💑  Романтика / медовый",  "romance"),
        ("👨‍👩‍👧  Семейный отдых",       "family"),
        ("📸  Красивые фото",        "photo"),
        ("💆  Оздоровление",         "health"),
        ("🎉  Тусовки / вечеринки",  "party"),
        ("🏛  История и культура",   "culture"),
    ]
    context.user_data['goal_opts'] = opts
    context.user_data['goal_sel'] = set()
    await ask(context, chat_id,
        step(5)
        + "🎯  Цель поездки (можно несколько):",
        make_multi_inline(opts, set(), cols=1)
    )
    return TRIP_GOAL


async def airline_pref_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'airline_pref', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(21)
        + "⏱  Готовы к длительным перелётам?",
        make_inline([
            ("⏰  До 2–3 ч",    "fly_2h"),
            ("🕐  3–6 ч",       "fly_6h"),
            ("🕙  До 10 ч",     "fly_10h"),
            ("🌍  Любая длина", "fly_any"),
        ])
    )
    return FLIGHT_DURATION


async def flight_duration_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    labels = {
        "fly_2h":  "До 2–3 часов",
        "fly_6h":  "3–6 часов",
        "fly_10h": "До 10 часов",
        "fly_any": "Любая длительность",
    }
    save(context, 'flight_duration', labels.get(query.data, query.data))
    await query.edit_message_text(
        f"Выбрано: {labels.get(query.data)}\n\n"
        + step(22)
        + "🔄  Прямой рейс или возможны пересадки?\n"
          "(напишите пожелания)"
    )
    context.user_data['last_bot_msg_id'] = query.message.message_id
    return LAYOVER


async def layover_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'layover', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(23)
        + "🧳  Достаточно ручной клади (10 кг) или нужен зарегистрированный багаж?\n"
          "(сколько кг на человека / пару / семью)"
    )
    return LUGGAGE


async def luggage_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'luggage', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(24)
        + "🚐  Предпочтительный трансфер:",
        make_inline([
            ("🚌  Групповой",    "tr_group"),
            ("🚗  Инд. эконом",  "tr_econom"),
            ("🚙  Инд. комфорт", "tr_comfort"),
            ("🏎  Инд. VIP",     "tr_vip"),
        ])
    )
    return TRANSFER


async def transfer_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    labels = {
        "tr_group":   "🚌  Групповой",
        "tr_econom":  "🚗  Инд. (эконом)",
        "tr_comfort": "🚙  Инд. (комфорт)",
        "tr_vip":     "🏎  Инд. (VIP)",
    }
    save(context, 'transfer', labels.get(query.data, query.data))
    await query.edit_message_text(
        f"Выбрано: {labels.get(query.data)}\n\n"
        + step(25)
        + "💰  Планируемый бюджет на поездку?\n"
          "(сумму и на сколько человек)"
    )
    context.user_data['last_bot_msg_id'] = query.message.message_id
    return BUDGET


async def trip_goal_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    opts = context.user_data.get('goal_opts', [])
    sel  = context.user_data.get('goal_sel', set())
    key_to_label = {k: l for l, k in opts}

    if query.data == "done":
        if not sel:
            await query.answer("Выберите хотя бы один вариант!", show_alert=True)
            return TRIP_GOAL
        val = ", ".join(key_to_label.get(k, k) for k in sel)
        save(context, 'trip_goal', val)
        atm_opts = [
            ("🤫  Тихий и спокойный",      "atm_quiet"),
            ("🎭  Активный с анимацией",   "atm_active"),
            ("👨‍👩‍👧  Семейный с клубом",     "atm_family"),
            ("🥳  Молодёжный / вечеринки", "atm_youth"),
            ("🌿  Эко-отель с природой",   "atm_eco"),
            ("💎  Люксовый сервис",        "atm_luxury"),
            ("🍽  Гастрономия",            "atm_gastro"),
        ]
        context.user_data['atm_opts'] = atm_opts
        context.user_data['atm_sel'] = set()
        await query.edit_message_text(
            f"Выбрано: {val}\n\n"
            + step(6)
            + "🌴  Атмосфера отдыха (можно несколько):",
            reply_markup=make_multi_inline(atm_opts, set(), cols=1)
        )
        context.user_data['last_bot_msg_id'] = query.message.message_id
        return ATMOSPHERE
    else:
        k = query.data.replace("t:", "")
        if k in sel: sel.discard(k)
        else: sel.add(k)
        context.user_data['goal_sel'] = sel
        await query.edit_message_reply_markup(reply_markup=make_multi_inline(opts, sel, cols=1))
        return TRIP_GOAL


async def atmosphere_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    opts = context.user_data.get('atm_opts', [])
    sel  = context.user_data.get('atm_sel', set())
    key_to_label = {k: l for l, k in opts}

    if query.data == "done":
        if not sel:
            await query.answer("Выберите хотя бы один вариант!", show_alert=True)
            return ATMOSPHERE
        val = ", ".join(key_to_label.get(k, k) for k in sel)
        save(context, 'atmosphere', val)
        hotel_opts = [
            ("🆕  Новый и современный",       "h_new"),
            ("🏡  Камерный и уютный",         "h_cozy"),
            ("🏢  Большой с инфраструктурой", "h_big"),
            ("🌳  Зелёный с растительностью", "h_green"),
            ("🎉  Активный с анимацией",      "h_active"),
            ("⚽  Много спорта",              "h_sport"),
            ("🌊  Первая береговая линия",    "h_sea"),
            ("👶  Детская концепция",         "h_kids"),
        ]
        context.user_data['hotel_opts'] = hotel_opts
        context.user_data['hotel_sel'] = set()
        await query.edit_message_text(
            f"Выбрано: {val}\n\n"
            + step(7)
            + "🏨  Важно, чтобы отель был (можно несколько):",
            reply_markup=make_multi_inline(hotel_opts, set(), cols=1)
        )
        context.user_data['last_bot_msg_id'] = query.message.message_id
        return HOTEL_STYLE
    else:
        k = query.data.replace("t:", "")
        if k in sel: sel.discard(k)
        else: sel.add(k)
        context.user_data['atm_sel'] = sel
        await query.edit_message_reply_markup(reply_markup=make_multi_inline(opts, sel, cols=1))
        return ATMOSPHERE


async def hotel_style_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    opts = context.user_data.get('hotel_opts', [])
    sel  = context.user_data.get('hotel_sel', set())
    key_to_label = {k: l for l, k in opts}

    if query.data == "done":
        if not sel:
            await query.answer("Выберите хотя бы один вариант!", show_alert=True)
            return HOTEL_STYLE
        val = ", ".join(key_to_label.get(k, k) for k in sel)
        save(context, 'hotel_style', val)
        act_opts = [
            ("🏖  Релакс на пляже",      "act_beach"),
            ("🏊  Релакс у бассейна",    "act_pool"),
            ("🏛  Экскурсии",            "act_excur"),
            ("🎢  Тематические парки",   "act_parks"),
            ("🤿  Дайвинг / снорклинг", "act_dive"),
            ("🏄  Водный спорт",         "act_water"),
            ("💆  СПА и оздоровление",  "act_spa"),
            ("🛍  Шоппинг",             "act_shop"),
            ("⚽  Спорт",               "act_sport"),
        ]
        context.user_data['act_opts'] = act_opts
        context.user_data['act_sel'] = set()
        await query.edit_message_text(
            f"Выбрано: {val}\n\n"
            + step(8)
            + "🏄  Как планируете проводить время? (можно несколько):",
            reply_markup=make_multi_inline(act_opts, set(), cols=1)
        )
        context.user_data['last_bot_msg_id'] = query.message.message_id
        return ACTIVITIES
    else:
        k = query.data.replace("t:", "")
        if k in sel: sel.discard(k)
        else: sel.add(k)
        context.user_data['hotel_sel'] = sel
        await query.edit_message_reply_markup(reply_markup=make_multi_inline(opts, sel, cols=1))
        return HOTEL_STYLE


async def activities_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    opts = context.user_data.get('act_opts', [])
    sel  = context.user_data.get('act_sel', set())
    key_to_label = {k: l for l, k in opts}

    if query.data == "done":
        if not sel:
            await query.answer("Выберите хотя бы один вариант!", show_alert=True)
            return ACTIVITIES
        val = ", ".join(key_to_label.get(k, k) for k in sel)
        save(context, 'activities', val)
        design_opts = [
            ("🌴  Тропический",       "d_tropical"),
            ("🎨  Бохо-шик",          "d_boho"),
            ("🏙  Минимализм",        "d_minimal"),
            ("🌊  Средиземноморский", "d_med"),
            ("🌿  Эко-люкс",          "d_eco"),
            ("🏛  Колониальный",      "d_colonial"),
            ("🎩  Классический",      "d_classic"),
            ("🌸  Восточный",         "d_east"),
        ]
        context.user_data['design_opts'] = design_opts
        context.user_data['design_sel'] = set()
        chat_id = query.message.chat_id

        photo_dir = os.path.dirname(os.path.abspath(__file__)) + "/images"
        photo_files = [
            ("hotel_tropical.jpg", "🌴 Тропический"),
            ("hotel_boho.jpg", "🎨 Бохо-шик"),
            ("hotel_minimal.jpg", "🏙 Минимализм"),
            ("hotel_mediterranean.jpg", "🌊 Средиземноморский"),
            ("hotel_eco_lux.jpg", "🌿 Эко-люкс"),
            ("hotel_colonial.jpg", "🏛 Колониальный"), 
            ("hotel_classic.jpg", "🎩 Классический"),
            ("hotel_east.jpg", "🌸 Восточный"),
        ]
        media = []
        opened = []
        for fname, caption in photo_files:
            path = os.path.join(photo_dir, fname)
            if os.path.exists(path):
                f = open(path, 'rb')
                opened.append(f)
                media.append(InputMediaPhoto(media=f, caption=caption))
        if media:
            await query.edit_message_text(f"Выбрано: {val}\n\n🏨 Посмотрите примеры стилей отелей 👇")
            album_messages = await context.bot.send_media_group(chat_id=chat_id, media=media)
            context.user_data['styles_intro_msg_id'] = query.message.message_id
            context.user_data['album_msg_ids'] = [m.message_id for m in album_messages]
            for f in opened:
                f.close()
        else:
            await query.edit_message_text(f"Выбрано: {val}")
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=step(9) + "🎨  Предпочтительный стиль / дизайн отеля (можно несколько):",
            reply_markup=make_multi_inline(design_opts, set(), cols=1)
        )
        context.user_data['last_bot_msg_id'] = sent.message_id
        return DESIGN_STYLE
    else:
        k = query.data.replace("t:", "")
        if k in sel: sel.discard(k)
        else: sel.add(k)
        context.user_data['act_sel'] = sel
        await query.edit_message_reply_markup(reply_markup=make_multi_inline(opts, sel, cols=1))
        return ACTIVITIES


async def design_style_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    opts = context.user_data.get('design_opts', [])
    sel  = context.user_data.get('design_sel', set())
    key_to_label = {k: l for l, k in opts}

    if query.data == "done":
        if not sel:
            await query.answer("Выберите хотя бы один вариант!", show_alert=True)
            return DESIGN_STYLE
        val = ", ".join(key_to_label.get(k, k) for k in sel)
        save(context, 'design_style', val)

        for msg_id in context.user_data.pop('album_msg_ids', []):
            await _delete_msg(context.bot, query.message.chat_id, msg_id)
        await _delete_msg(context.bot, query.message.chat_id, context.user_data.pop('styles_intro_msg_id', None))
        await _delete_msg(context.bot, query.message.chat_id, query.message.message_id)
        context.user_data.pop('last_bot_msg_id', None)

        sent = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Выбрано: {val}\n\n"
            + step(10)
            + "🛏  Предпочтительное размещение:",
            reply_markup=make_inline([
                ("🛏  Стандарт (любой вид)",           "acc_std"),
                ("🌊  Вид на море",                    "acc_sea"),
                ("🏊  С выходом к бассейну (свим-ап)", "acc_pool"),
                ("👨‍👩‍👧  Семейный номер",                 "acc_fam"),
                ("🏡  Вилла",                          "acc_villa"),
            ], cols=1)
        )
        context.user_data['last_bot_msg_id'] = sent.message_id
        return ACCOMMODATION_TYPE
    else:
        k = query.data.replace("t:", "")
        if k in sel: sel.discard(k)
        else: sel.add(k)
        context.user_data['design_sel'] = sel
        await query.edit_message_reply_markup(reply_markup=make_multi_inline(opts, sel, cols=1))
        return DESIGN_STYLE


async def accommodation_type_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    labels = {
        "acc_std":   "🛏  Стандарт (любой вид)",
        "acc_sea":   "🌊  Вид на море",
        "acc_pool":  "🏊  С выходом к бассейну (свим-ап)",
        "acc_fam":   "👨‍👩‍👧  Семейный номер",
        "acc_villa": "🏡  Вилла",
    }
    save(context, 'accommodation_type', labels.get(query.data, query.data))
    await query.edit_message_text(
        f"Выбрано: {labels.get(query.data)}\n\n"
        + step(11)
        + "😴  Чуткий ли у вас сон? Важна ли тишина вокруг номера?",
        reply_markup=make_inline([
            ("✅  Да, тишина важна", "sleep_yes"),
            ("❌  Нет, не важно",    "sleep_no"),
        ])
    )
    context.user_data['last_bot_msg_id'] = query.message.message_id
    return SLEEP_SENSITIVITY


async def sleep_sensitivity_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    labels = {
        "sleep_yes": "✅  Да, тишина важна",
        "sleep_no":  "❌  Нет, не важно",
    }
    save(context, 'sleep_sensitivity', labels.get(query.data, query.data))
    save(context, 'sleep_schedule', '—')
    await query.edit_message_text(
        f"Выбрано: {labels.get(query.data)}\n\n"
        + step(12)
        + "🍽  Тип питания:",
        reply_markup=make_inline([
            ("🚫  Без питания (RO)",           "meal_ro"),
            ("☕  BB — завтрак",               "meal_bb"),
            ("🥗  HB — завтрак / ужин",        "meal_hb"),
            ("🍲  FB — завтрак, обед, ужин",   "meal_fb"),
            ("🍹  AI — всё включено",           "meal_ai"),
            ("🌟  UAI — ультра всё включено",  "meal_uai"),
        ], cols=1)
    )
    context.user_data['last_bot_msg_id'] = query.message.message_id
    return MEAL_PLAN


async def sleep_schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'sleep_schedule', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(13)
        + "🍽  Тип питания:",
        make_inline([
            ("🚫  Без питания (RO)",           "meal_ro"),
            ("☕  BB — завтрак",               "meal_bb"),
            ("🥗  HB — завтрак / ужин",        "meal_hb"),
            ("🍲  FB — завтрак, обед, ужин",   "meal_fb"),
            ("🍹  AI — всё включено",           "meal_ai"),
            ("🌟  UAI — ультра всё включено",  "meal_uai"),
        ], cols=1)
    )
    return MEAL_PLAN


async def meal_plan_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    labels = {
        "meal_ro":  "🚫  Без питания (RO)",
        "meal_bb":  "☕  BB — завтрак",
        "meal_hb":  "🥗  HB — завтрак / ужин",
        "meal_fb":  "🍲  FB — завтрак, обед, ужин",
        "meal_ai":  "🍹  AI — всё включено",
        "meal_uai": "🌟  UAI — ультра всё включено",
    }
    save(context, 'meal_plan', labels.get(query.data, query.data))
    await query.edit_message_text(
        f"Выбрано: {labels.get(query.data)}\n\n"
        + step(14)
        + "🥗  Диеты, аллергии или пищевые предпочтения?\n"
          "(вегетарианство, халяль, безлактозное, детское и т.п.)\n"
          "Если нет — напишите «нет»"
    )
    context.user_data['last_bot_msg_id'] = query.message.message_id
    return DIETARY


async def dietary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'dietary', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(15)
        + "🍷  Важно ли, чтобы у отеля были рестораны а-ля-карт?",
        make_inline([
            ("✅  Да", "alac_yes"),
            ("❌  Нет", "alac_no"),
        ])
    )
    return ALACARTE


async def alacarte_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    labels = {"alac_yes": "✅  Да", "alac_no": "❌  Нет"}
    save(context, 'alacarte', labels.get(query.data, query.data))
    cuisine_opts = [
        ("🥢  Паназиатская", "cuis_asia"),
        ("🥐  Европейская",  "cuis_euro"),
        ("🍔  Американская", "cuis_amer"),
        ("🌶  Восточная",    "cuis_east"),
        ("👨‍🍳  Высокая кухня","cuis_fine"),
        ("🧪  Молекулярная", "cuis_mol"),
    ]
    context.user_data['cuis_opts'] = cuisine_opts
    context.user_data['cuis_sel'] = set()
    await query.edit_message_text(
        f"Выбрано: {labels.get(query.data)}\n\n"
        + step(16)
        + "🍜  Предпочтения по кухне (можно несколько):",
        reply_markup=make_multi_inline(cuisine_opts, set(), cols=1)
    )
    context.user_data['last_bot_msg_id'] = query.message.message_id
    return CUISINE


async def cuisine_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    opts = context.user_data.get('cuis_opts', [])
    sel  = context.user_data.get('cuis_sel', set())
    key_to_label = {k: l for l, k in opts}

    if query.data == "done":
        if not sel:
            await query.answer("Выберите хотя бы один вариант!", show_alert=True)
            return CUISINE
        val = ", ".join(key_to_label.get(k, k) for k in sel)
        save(context, 'cuisine', val)
        await query.edit_message_text(
            f"Выбрано: {val}\n\n"
            + step(17)
            + "🚶  Важно ли выходить за пределы отеля и гулять?",
            reply_markup=make_inline([
                ("✅  Да, важно",         "out_yes"),
                ("❌  Нет, хватит отеля", "out_no"),
            ])
        )
        context.user_data['last_bot_msg_id'] = query.message.message_id
        return OUTSIDE_WALK
    else:
        k = query.data.replace("t:", "")
        if k in sel: sel.discard(k)
        else: sel.add(k)
        context.user_data['cuis_sel'] = sel
        await query.edit_message_reply_markup(reply_markup=make_multi_inline(opts, sel, cols=1))
        return CUISINE


async def outside_walk_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    labels = {"out_yes": "✅  Да, важно", "out_no": "❌  Нет, хватит отеля"}
    save(context, 'outside_walk', labels.get(query.data, query.data))
    await query.edit_message_text(
        f"Выбрано: {labels.get(query.data)}\n\n"
        + step(18)
        + "🏝  Какой пляж предпочтительнее?",
        reply_markup=make_inline([
            ("🪨  Каменистый",       "beach_stone"),
            ("🏖  Песчано-галечный", "beach_mix"),
            ("🌟  Песчаный",         "beach_sand"),
        ], cols=1)
    )
    context.user_data['last_bot_msg_id'] = query.message.message_id
    return BEACH_TYPE


async def beach_type_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    labels = {
        "beach_stone": "🪨  Каменистый",
        "beach_mix":   "🏖  Песчано-галечный",
        "beach_sand":  "🌟  Песчаный",
    }
    save(context, 'beach_type', labels.get(query.data, query.data))
    beach_opts = [
        ("🏠  Свой пляж отеля",            "bf_own"),
        ("🌆  Городской пляж",             "bf_city"),
        ("⛱  Лежаки и зонтики от отеля",  "bf_chairs"),
        ("🍹  Сервис и бар на пляже",      "bf_service"),
        ("🌉  Пирс или понтон для купания","bf_pier"),
        ("👶  Удобства для детей",         "bf_kids"),
    ]
    context.user_data['beach_opts'] = beach_opts
    context.user_data['beach_sel'] = set()
    await query.edit_message_text(
        f"Выбрано: {labels.get(query.data)}\n\n"
        + step(19)
        + "⛱  Характеристики пляжа (можно несколько):",
        reply_markup=make_multi_inline(beach_opts, set(), cols=1)
    )
    context.user_data['last_bot_msg_id'] = query.message.message_id
    return BEACH_FEATURES


async def beach_features_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    opts = context.user_data.get('beach_opts', [])
    sel  = context.user_data.get('beach_sel', set())
    key_to_label = {k: l for l, k in opts}

    if query.data == "done":
        if not sel:
            await query.answer("Выберите хотя бы один вариант!", show_alert=True)
            return BEACH_FEATURES
        val = ", ".join(key_to_label.get(k, k) for k in sel)
        save(context, 'beach_features', val)
        await query.edit_message_text(
            f"Выбрано: {val}\n\n"
            + step(20)
            + "🛫  Предпочтения по авиакомпаниям?\n"
              "(если нет — напишите «нет»)"
        )
        context.user_data['last_bot_msg_id'] = query.message.message_id
        return AIRLINE_PREF
    else:
        k = query.data.replace("t:", "")
        if k in sel: sel.discard(k)
        else: sel.add(k)
        context.user_data['beach_sel'] = sel
        await query.edit_message_reply_markup(reply_markup=make_multi_inline(opts, sel, cols=1))
        return BEACH_FEATURES


async def special_wishes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'special_wishes', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(27)
        + "⭐️  Какие из перечисленных пунктов для вас наиболее важны?\n"
          "Напишите, что ещё важно при выборе отдыха, что не было упомянуто в анкете:"
    )
    return TOP_PRIORITIES


async def top_priorities_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'top_priorities', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(28)
        + "👤  Введите ваше ФИО (полностью):"
    )
    return FIO


async def fio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'fio', update.message.text.strip())
    save(context, 'email', '—')
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(29)
        + "📲  Удобный способ связи:",
        make_inline([
            ("💬  Telegram",    "telegram_contact"),
            ("📞  Телефон",     "phone_contact"),
            ("🔵  ВКонтакте",  "vk"),
            ("📧  Email",       "email_contact"),
            ("📲  MAX",         "max_contact"),
        ])
    )
    return CONTACT_METHOD


async def email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save(context, 'email', update.message.text.strip())
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(30)
        + "📲  Удобный способ связи:",
        make_inline([
            ("💬  Telegram",    "telegram_contact"),
            ("📞  Телефон",     "phone_contact"),
            ("🔵  ВКонтакте",  "vk"),
            ("📧  Email",       "email_contact"),
            ("📲  MAX",         "max_contact"),
        ])
    )
    return CONTACT_METHOD


async def contact_method_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    labels = {
        "telegram_contact": "💬  Telegram",
        "phone_contact":    "📞  Телефон",
        "vk":               "🔵  ВКонтакте",
        "email_contact":    "📧  Email",
        "max_contact":      "📲  MAX",
    }
    chosen = labels.get(query.data, query.data)
    save(context, 'contact_method', chosen)

    if query.data in CONTACT_NEEDS_LINK:
        platform = "ВКонтакте" if query.data == "vk" else "Telegram"
        await query.edit_message_text(
            f"Выбрано: {chosen}\n\n"
            f"🔗  Укажите ссылку на ваш аккаунт {platform}\n"
            f"(например: vk.com/id12345 или @username)"
        )
        context.user_data['last_bot_msg_id'] = query.message.message_id
        return CONTACT_LINK
    elif query.data == "phone_contact":
        await query.edit_message_text(
            f"Выбрано: {chosen}\n\n"
            "📞  Введите ваш номер телефона:"
        )
        context.user_data['last_bot_msg_id'] = query.message.message_id
        return CONTACT_LINK
    elif query.data == "max_contact":
        await query.edit_message_text(
            f"Выбрано: {chosen}\n\n"
            "📲  Введите ваш номер телефона для MAX:"
        )
        context.user_data['last_bot_msg_id'] = query.message.message_id
        return CONTACT_LINK
    else:
        await query.edit_message_text(
            f"Выбрано: {chosen}\n\n"
            "📧  Введите ваш email:"
        )
        context.user_data['last_bot_msg_id'] = query.message.message_id
        return CONTACT_LINK


async def contact_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    save(context, 'contact_link', val)
    if context.user_data.get('contact_method') == '📧  Email':
        save(context, 'email', val)
    chat_id = update.message.chat_id
    await del_user_msg(update.message)
    await ask(context, chat_id,
        step(31)
        + "🗣  Удобный формат общения:",
        make_inline([
            ("📞  Звонок",      "call"),
            ("📹  Видеозвонок", "video"),
            ("🎤  Голосовое",   "voice"),
            ("✍️  Текст",       "text"),
        ])
    )
    return DISCUSS_FORMAT


async def discuss_format_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    labels = {
        "call":  "📞  Звонок",
        "video": "📹  Видеозвонок",
        "voice": "🎤  Голосовое",
        "text":  "✍️  Текст",
    }
    save(context, 'discuss_format', labels.get(query.data, query.data))
    chat_id = query.message.chat_id

    await query.edit_message_text(f"Выбрано: {labels.get(query.data)}")
    context.user_data.pop('last_bot_msg_id', None)

    summary = get_answers(context.user_data)

    await context.bot.send_message(
        chat_id=chat_id,
        text="🎉  Анкета заполнена! Большое спасибо!\n\n"
             "Мы получили ваши ответы и свяжемся с вами в ближайшее время "
             "для подбора идеального варианта отдыха 🌴✈️"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary)
    except Exception as e:
        logger.error(f"Ошибка отправки администратору: {e}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Анкета отменена.\n"
        "Чтобы начать заново — введите /start"
    )
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WELCOME:            [CallbackQueryHandler(welcome_cb)],
            PARTICIPANTS:       [MessageHandler(filters.TEXT & ~filters.COMMAND, participants_handler)],
            WHO_TRAVELS:        [CallbackQueryHandler(who_travels_cb)],
            DATES:              [MessageHandler(filters.TEXT & ~filters.COMMAND, dates_handler)],
            DEPARTURE_CITY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, departure_city_handler)],
            BUDGET:             [MessageHandler(filters.TEXT & ~filters.COMMAND, budget_handler)],
            AIRLINE_PREF:       [MessageHandler(filters.TEXT & ~filters.COMMAND, airline_pref_handler)],
            FLIGHT_DURATION:    [CallbackQueryHandler(flight_duration_cb)],
            LAYOVER:            [MessageHandler(filters.TEXT & ~filters.COMMAND, layover_handler)],
            LUGGAGE:            [MessageHandler(filters.TEXT & ~filters.COMMAND, luggage_handler)],
            TRANSFER:           [CallbackQueryHandler(transfer_cb)],
            TRIP_GOAL:          [CallbackQueryHandler(trip_goal_cb)],
            ATMOSPHERE:         [CallbackQueryHandler(atmosphere_cb)],
            HOTEL_STYLE:        [CallbackQueryHandler(hotel_style_cb)],
            ACTIVITIES:         [CallbackQueryHandler(activities_cb)],
            DESIGN_STYLE:       [CallbackQueryHandler(design_style_cb)],
            ACCOMMODATION_TYPE: [CallbackQueryHandler(accommodation_type_cb)],
            SLEEP_SENSITIVITY:  [CallbackQueryHandler(sleep_sensitivity_cb)],
            SLEEP_SCHEDULE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, sleep_schedule_handler)],
            MEAL_PLAN:          [CallbackQueryHandler(meal_plan_cb)],
            DIETARY:            [MessageHandler(filters.TEXT & ~filters.COMMAND, dietary_handler)],
            ALACARTE:           [CallbackQueryHandler(alacarte_cb)],
            CUISINE:            [CallbackQueryHandler(cuisine_cb)],
            OUTSIDE_WALK:       [CallbackQueryHandler(outside_walk_cb)],
            BEACH_TYPE:         [CallbackQueryHandler(beach_type_cb)],
            BEACH_FEATURES:     [CallbackQueryHandler(beach_features_cb)],
            SPECIAL_WISHES:     [MessageHandler(filters.TEXT & ~filters.COMMAND, special_wishes_handler)],
            TOP_PRIORITIES:     [MessageHandler(filters.TEXT & ~filters.COMMAND, top_priorities_handler)],
            FIO:                [MessageHandler(filters.TEXT & ~filters.COMMAND, fio_handler)],
            CONTACT_METHOD:     [CallbackQueryHandler(contact_method_cb)],
            CONTACT_LINK:       [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_link_handler)],
            DISCUSS_FORMAT:     [CallbackQueryHandler(discuss_format_cb)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)
    logger.info("Бот запущен ✅")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
