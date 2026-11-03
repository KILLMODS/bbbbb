import logging
import sqlite3
import time
from telebot import TeleBot, types
from telebot.states import State, StatesGroup
from telebot.states.sync.middleware import StateMiddleware
from telebot.storage import StateMemoryStorage
from telebot.custom_filters import StateFilter

# ----------------------------------------------------
# КОНФИГУРАЦИЯ И КОНСТАНТЫ
# ----------------------------------------------------
BOT_TOKEN = "9049068595:AAE49NcYh00LpE-ylCze5fnhZ3Q29jJhsyU"
SBP_REQUISITES = "89770496696 (Сбербанк)"
SHOP_NAME = "TimkaCheate Shop"
SUPPORT_USERNAME = "@TimkaYutub"

# Доступ к админ-панели только у этого Telegram ID
ADMIN_IDS = [6139965229]

# ----------------------------------------------------
# КАСТОМНЫЕ EMOJI IDs (HTML)
# ----------------------------------------------------
E_PARTY = '<tg-emoji emoji-id="5345778585959436594">🥳</tg-emoji>'
E_MONEY_FACE = '<tg-emoji emoji-id="5348583560380981713">🤑</tg-emoji>'
E_LIGHTNING = '<tg-emoji emoji-id="5346255254314848940">⚡️</tg-emoji>'
E_CHECK = '<tg-emoji emoji-id="5346281810097642712">✅</tg-emoji>'
E_BOT = '<tg-emoji emoji-id="5346184352994730061">🤖</tg-emoji>'
E_USER = '<tg-emoji emoji-id="5346285456524883921">👤</tg-emoji>'
E_SHIELD = '<tg-emoji emoji-id="5346307103160047735">🛡</tg-emoji>'
E_DESK = '<tg-emoji emoji-id="5346005489081687781">🖥</tg-emoji>'
E_INFO = '<tg-emoji emoji-id="5346333405539773818">ℹ️</tg-emoji>'
E_SEARCH = '<tg-emoji emoji-id="5345999377343224283">🔍</tg-emoji>'
E_CART = '<tg-emoji emoji-id="5345965498641192380">🛒</tg-emoji>'
E_PURSE = '<tg-emoji emoji-id="5346089374087944625">👛</tg-emoji>'
E_CHART = '<tg-emoji emoji-id="5345954039668448167">📈</tg-emoji>'
E_CLIPBOARD = '<tg-emoji emoji-id="5345797951966977760">📋</tg-emoji>'
E_LOCK = '<tg-emoji emoji-id="5348128594495314581">🔐</tg-emoji>'
E_MONEY_BAG = '<tg-emoji emoji-id="5346161808711393212">💰</tg-emoji>'
E_CROSS = '<tg-emoji emoji-id="5346278906699752391">❎</tg-emoji>'
E_PLANE = '<tg-emoji emoji-id="5345944354517196230">✈️</tg-emoji>'

# IDs для Inline-кнопок (icon_custom_emoji_id)
EMOJI_CART_ID = "5345965498641192380"
EMOJI_USER_ID = "5346285456524883921"
EMOJI_PURSE_ID = "5346089374087944625"
EMOJI_INFO_ID = "5346333405539773818"
EMOJI_BOT_ID = "5346184352994730061"
EMOJI_CHECK_ID = "5346281810097642712"
EMOJI_CROSS_ID = "5346278906699752391"
EMOJI_PLANE_ID = "5345944354517196230"
EMOJI_MONEY_ID = "5346161808711393212"

# ----------------------------------------------------
# БАЗА ДАННЫХ
# ----------------------------------------------------
class Database:
    def __init__(self, db_file: str = "shop_0.db"):
        self.db_file = db_file
        self.create_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_file)

    def create_tables(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    currency TEXT DEFAULT 'RUB',
                    accepted_terms INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    price_rub REAL NOT NULL,
                    price_stars INTEGER NOT NULL,
                    stock INTEGER NOT NULL,
                    photo_id TEXT DEFAULT NULL,
                    sold_count INTEGER DEFAULT 0,
                    is_quantity INTEGER DEFAULT 0
                )
            """)
            
            # Добавляем колонку is_quantity при миграции старой БД, если её нет
            try:
                conn.execute("ALTER TABLE products ADD COLUMN is_quantity INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Колонка уже существует

    def get_user(self, user_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone()

    def add_user(self, user_id: int, username: str):
        with self.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username or "NoUsername")
            )

    def set_terms_accepted(self, user_id: int):
        with self.get_connection() as conn:
            conn.execute("UPDATE users SET accepted_terms = 1 WHERE user_id = ?", (user_id,))

    def update_currency(self, user_id: int, currency: str):
        with self.get_connection() as conn:
            conn.execute("UPDATE users SET currency = ? WHERE user_id = ?", (currency, user_id))

    def get_all_users(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            return [row[0] for row in cursor.fetchall()]

    def get_all_products(self, only_in_stock: bool = True):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if only_in_stock:
                cursor.execute("SELECT * FROM products WHERE stock > 0")
            else:
                cursor.execute("SELECT * FROM products")
            return cursor.fetchall()

    def get_product(self, product_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            return cursor.fetchone()

    def add_product(self, title: str, desc: str, price_rub: float, price_stars: int, stock: int, photo_id: str = None, is_quantity: int = 0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO products (title, description, price_rub, price_stars, stock, photo_id, is_quantity) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, desc, price_rub, price_stars, stock, photo_id, is_quantity)
            )
            return cursor.lastrowid

    def delete_product(self, product_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))

    def decrease_stock(self, product_id: int, amount: int = 1):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE products SET stock = stock - ?, sold_count = sold_count + ? WHERE id = ?",
                (amount, amount, product_id)
            )

db = Database()

# ----------------------------------------------------
# ИНИЦИАЛИЗА TELEBOT
# ----------------------------------------------------
state_storage = StateMemoryStorage()
bot = TeleBot(BOT_TOKEN, parse_mode='HTML', state_storage=state_storage, use_class_middlewares=True)
bot.setup_middleware(StateMiddleware(bot))
bot.add_custom_filter(StateFilter(bot))

class FormStates(StatesGroup):
    add_title = State()
    add_desc = State()
    add_price_rub = State()
    add_price_stars = State()
    add_stock = State()
    add_photo = State()
    add_is_quantity = State()
    add_confirm = State()

    select_quantity = State()
    waiting_for_receipt = State()
    broadcast_msg = State()

# ----------------------------------------------------
# КЛАВИАТУРЫ И СТИЛИ КНОПОК
# ----------------------------------------------------
def make_btn(text: str, callback_data: str, style: str = None, emoji_id: str = None):
    btn = types.InlineKeyboardButton(text=text, callback_data=callback_data)
    if style:
        btn.style = style  # 'primary', 'success', 'danger'
    if emoji_id:
        btn.icon_custom_emoji_id = emoji_id
    return btn

def get_terms_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(make_btn("Принять условия сервиса", "accept_terms", style="success", emoji_id=EMOJI_CHECK_ID))
    return kb

def get_main_menu(user_id: int):
    user = db.get_user(user_id)
    curr = user[2] if user else 'RUB'
    curr_text = "Валюта: Рубли (СБП)" if curr == 'RUB' else "Валюта: ⭐️ Stars"

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(make_btn("Зайти в магазин", "shop_catalog", style="primary", emoji_id=EMOJI_CART_ID))
    kb.row(
        make_btn("Профиль", "user_profile", style="primary", emoji_id=EMOJI_USER_ID),
        make_btn(curr_text, "toggle_currency", style="primary", emoji_id=EMOJI_PURSE_ID)
    )
    kb.add(make_btn("Информация и Помощь", "shop_info", style="primary", emoji_id=EMOJI_INFO_ID))

    if user_id in ADMIN_IDS:
        kb.add(make_btn("Панель Администратора", "admin_panel", style="danger", emoji_id=EMOJI_BOT_ID))

    return kb

def get_products_kb():
    products = db.get_all_products(only_in_stock=True)
    kb = types.InlineKeyboardMarkup()
    
    if not products:
        kb.add(make_btn("Товаров нет в наличии", "main_menu", style="danger", emoji_id=EMOJI_CROSS_ID))
    else:
        for p in products:
            p_id, title, _, price_rub, price_stars, stock, _, _, is_quantity = p
            badge = " 🔢" if is_quantity else ""
            kb.add(make_btn(f"{title}{badge} | {stock} шт.", f"prod_{p_id}", style="primary", emoji_id=EMOJI_CART_ID))
            
    kb.add(make_btn("Назад в главное меню", "main_menu", style="danger", emoji_id=EMOJI_CROSS_ID))
    return kb

def get_product_detail_kb(product_id: int):
    kb = types.InlineKeyboardMarkup()
    kb.add(make_btn("Купить товар", f"buy_{product_id}", style="success", emoji_id=EMOJI_MONEY_ID))
    kb.add(make_btn("Вернуться в каталог", "shop_catalog", style="danger", emoji_id=EMOJI_CROSS_ID))
    return kb

def get_admin_panel_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(make_btn("Добавить товар", "admin_add_product", style="success", emoji_id=EMOJI_CHECK_ID))
    kb.add(make_btn("Существующие товары", "admin_list_products", style="primary", emoji_id=EMOJI_CART_ID))
    kb.add(make_btn("Рассылка пользователям", "admin_broadcast", style="primary", emoji_id=EMOJI_PLANE_ID))
    kb.add(make_btn("Назад в главное меню", "main_menu", style="danger", emoji_id=EMOJI_CROSS_ID))
    return kb

# ----------------------------------------------------
# ОСНОВНАЯ ЛОГИКА
# ----------------------------------------------------

@bot.message_handler(commands=['start'])
def cmd_start(message: types.Message):
    try:
        bot.delete_state(message.from_user.id, message.chat.id)
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name

        db.add_user(user_id, username)
        user = db.get_user(user_id)

        if not user[3]:
            text = (
                f"{E_PARTY} <b>Добро пожаловать в автоматизированный магазин {SHOP_NAME}!</b>\n\n"
                f"{E_DESK} <b>Система авторизации:</b>\n"
                f"Для доступа к цифровым товарам и совершению покупок, пожалуйста, прочитайте и примите условия соглашения.\n\n"
                f"{E_CLIPBOARD} <b>Пользовательские правила:</b>\n"
                f"<blockquote>"
                f"• Все покупки обрабатываются в автоматическом режиме.\n"
                f"• Цифровой товар выдаётся сразу после успешного подтверждения оплаты.\n"
                f"• По всем вопросам обращайтесь к администрации: {SUPPORT_USERNAME}"
                f"</blockquote>\n\n"
                f"{E_SHIELD} Нажмите кнопку ниже для подтверждения."
            )
            bot.send_message(user_id, text, reply_markup=get_terms_kb())
        else:
            welcome_text = (
                f"{E_PARTY} Рады видеть вас снова, <b>{username}</b>!\n\n"
                f"{E_BOT} Вы находитесь в главном меню маркетплейса <b>{SHOP_NAME}</b> {E_MONEY_FACE}\n\n"
                f"{E_CART} Выбирайте интересующий раздел с помощью интерактивных кнопок ниже:"
            )
            bot.send_message(user_id, welcome_text, reply_markup=get_main_menu(user_id))
    except Exception as e:
        logging.error(f"Error start: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "accept_terms")
def accept_terms(call: types.CallbackQuery):
    try:
        db.set_terms_accepted(call.from_user.id)
        bot.answer_callback_query(call.id, "Условия успешно приняты!")
        text = (
            f"{E_CHECK} <b>Правила успешно подтверждены!</b>\n\n"
            f"{E_LIGHTNING} Добро пожаловать в <b>{SHOP_NAME}</b>! Теперь вы можете совершать покупки в любое время."
        )
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_menu(call.from_user.id)
        )
    except Exception as e:
        logging.error(f"Error accept_terms: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "main_menu")
def back_to_main(call: types.CallbackQuery):
    try:
        bot.delete_state(call.from_user.id, call.message.chat.id)
        text = (
            f"{E_BOT} <b>Главное меню магазина {SHOP_NAME}</b>\n\n"
            f"{E_SEARCH} Используйте кнопки с иконками для навигации:"
        )
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_menu(call.from_user.id)
        )
    except Exception:
        bot.send_message(call.message.chat.id, f"{E_BOT} <b>Главное меню</b>", reply_markup=get_main_menu(call.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data == "toggle_currency")
def toggle_currency(call: types.CallbackQuery):
    try:
        user = db.get_user(call.from_user.id)
        new_curr = 'STARS' if user[2] == 'RUB' else 'RUB'
        db.update_currency(call.from_user.id, new_curr)
        
        curr_readable = "⭐️ Telegram Stars" if new_curr == 'STARS' else "🇷🇺 Рубли (СБП)"
        bot.answer_callback_query(call.id, f"Активная валюта: {curr_readable}")
        
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_menu(call.from_user.id)
        )
    except Exception as e:
        logging.error(f"Error toggle_currency: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "user_profile")
def user_profile(call: types.CallbackQuery):
    try:
        user = db.get_user(call.from_user.id)
        curr_str = "🇷🇺 Рубли (СБП)" if user[2] == 'RUB' else "⭐️ Telegram Stars"
        is_admin = call.from_user.id in ADMIN_IDS
        role_str = "👑 Администратор" if is_admin else "👤 Клиент"

        text = (
            f"{E_USER} <b>Личный профиль пользователя</b>\n\n"
            f"🆔 <b>Ваш Telegram ID:</b> <code>{user[0]}</code>\n"
            f"{E_INFO} <b>Имя / Юзернейм:</b> @{user[1]}\n"
            f"{E_PURSE} <b>Выбранный способ оплаты:</b> {curr_str}\n"
            f"{E_SHIELD} <b>Статус аккаунта:</b> {role_str}\n\n"
            f"{E_DESK} <b>Поддержка пользователей:</b> {SUPPORT_USERNAME}"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(make_btn("Вернуться в меню", "main_menu", style="danger", emoji_id=EMOJI_CROSS_ID))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception as e:
        logging.error(f"Error profile: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "shop_info")
def shop_info(call: types.CallbackQuery):
    text = (
        f"{E_INFO} <b>О магазине {SHOP_NAME}</b>\n\n"
        f"{E_LIGHTNING} Наш сервис предлагает моментальную автоматизированную покупку цифровых товаров.\n\n"
        f"{E_MONEY_BAG} <b>Поддерживаемые методы оплаты:</b>\n"
        f"• Быстрые переводы СБП (Сбербанк)\n"
        f"• Telegram Stars (Оплата внутри приложения)\n\n"
        f"{E_SHIELD} <b>Гарантии качества:</b> Все заказы фиксируются в системе.\n"
        f"{E_USER} <b>Техническая поддержка:</b> {SUPPORT_USERNAME}"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text="💬 Написать в поддержку", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}"))
    kb.add(make_btn("Назад", "main_menu", style="danger", emoji_id=EMOJI_CROSS_ID))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

# ----------------------------------------------------
# ТОВАРЫ И ОПЛАТА
# ----------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data == "shop_catalog")
def show_catalog(call: types.CallbackQuery):
    text = (
        f"{E_CART} <b>Каталог товаров {SHOP_NAME}</b> {E_MONEY_FACE}\n\n"
        f"{E_SEARCH} Выберите интересующую позицию из списка ниже:"
    )
    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_products_kb()
        )
    except Exception:
        bot.send_message(call.message.chat.id, text, reply_markup=get_products_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("prod_"))
def show_prod_detail(call: types.CallbackQuery):
    try:
        prod_id = int(call.data.split("_")[1])
        product = db.get_product(prod_id)
        if not product:
            bot.answer_callback_query(call.id, "Товар не найден.")
            return

        user = db.get_user(call.from_user.id)
        curr = user[2]
        
        price_formatted = f"<b>{product[3]} RUB / шт.</b>" if curr == 'RUB' else f"<b>{product[4]} Stars / шт.</b>"
        qty_type_str = "\n🔢 <b>Тип товара:</b> Количественный (можно выбрать объем при покупке)" if product[8] else ""

        caption = (
            f"📦 <b>{product[1]}</b>\n\n"
            f"{E_CLIPBOARD} <b>Подробное описание:</b>\n"
            f"<blockquote>{product[2]}</blockquote>\n"
            f"{qty_type_str}\n"
            f"{E_MONEY_BAG} <b>Стоимость:</b> {price_formatted}\n"
            f"{E_CHART} <b>В наличии:</b> <code>{product[5]} шт.</code>"
        )

        if product[6]:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_photo(call.message.chat.id, product[6], caption=caption, reply_markup=get_product_detail_kb(prod_id))
        else:
            bot.edit_message_text(caption, call.message.chat.id, call.message.message_id, reply_markup=get_product_detail_kb(prod_id))
    except Exception as e:
        logging.error(f"Error prod_detail: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def start_buy(call: types.CallbackQuery):
    try:
        prod_id = int(call.data.split("_")[1])
        product = db.get_product(prod_id)

        if not product or product[5] <= 0:
            bot.answer_callback_query(call.id, "⚠️ Данный товар закончился!", show_alert=True)
            return

        # Если товар КОЛИЧЕСТВЕННЫЙ (is_quantity == 1)
        if product[8] == 1:
            bot.set_state(call.from_user.id, FormStates.select_quantity, call.message.chat.id)
            with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
                data['buying_prod_id'] = prod_id

            kb = types.InlineKeyboardMarkup()
            kb.add(make_btn("Отмена покупки", "shop_catalog", style="danger", emoji_id=EMOJI_CROSS_ID))

            bot.send_message(
                call.message.chat.id,
                f"🔢 <b>Введите желаемое количество товара «{product[1]}»:</b>\n\n"
                f"• Доступно на складе: <b>{product[5]} шт.</b>\n"
                f"• Минимальный заказ: <b>1 шт.</b>\n\n"
                f"<i>Введите число в чат сообщением:</i>",
                reply_markup=kb
            )
        else:
            # Неколичественный товар (всегда 1 шт)
            proceed_checkout(call.from_user.id, call.message.chat.id, prod_id, quantity=1)
    except Exception as e:
        logging.error(f"Error start_buy: {e}")

@bot.message_handler(state=FormStates.select_quantity)
def process_quantity_input(message: types.Message):
    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            prod_id = data.get('buying_prod_id')

        product = db.get_product(prod_id)
        if not product:
            bot.send_message(message.chat.id, "❌ Ошибка: товар не найден.")
            bot.delete_state(message.from_user.id, message.chat.id)
            return

        # Валидация количества (нельзя 0, только положительные целые числа)
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "⚠️ <b>Ошибка!</b> Введите целое число больше нуля (например: 1, 5, 10).")
            return

        qty = int(message.text)

        if qty <= 0:
            bot.send_message(message.chat.id, "⚠️ <b>Ошибка!</b> Нельзя купить 0 шт. Укажите количество от 1.")
            return

        if qty > product[5]:
            bot.send_message(
                message.chat.id,
                f"⚠️ <b>Превышение остатка!</b> На складе всего <b>{product[5]} шт.</b> Введите доступное количество."
            )
            return

        bot.delete_state(message.from_user.id, message.chat.id)
        proceed_checkout(message.from_user.id, message.chat.id, prod_id, quantity=qty)

    except Exception as e:
        logging.error(f"Error quantity input: {e}")

def proceed_checkout(user_id: int, chat_id: int, prod_id: int, quantity: int = 1):
    product = db.get_product(prod_id)
    user = db.get_user(user_id)
    curr = user[2]

    total_rub = round(product[3] * quantity, 2)
    total_stars = int(product[4] * quantity)

    if curr == 'STARS':
        prices = [types.LabeledPrice(label=f"{product[1]} ({quantity} шт.)", amount=total_stars)]
        bot.send_invoice(
            chat_id,
            title=f"Покупка {product[1]} ({quantity} шт.)",
            description=f"{product[2][:150]} (Количество: {quantity} шт.)",
            invoice_payload=f"stars_{prod_id}_{quantity}",
            provider_token="",
            currency="XTR",
            prices=prices
        )
    else:
        bot.set_state(user_id, FormStates.waiting_for_receipt, chat_id)
        with bot.retrieve_data(user_id, chat_id) as data:
            data['buying_prod_id'] = prod_id
            data['buying_qty'] = quantity
            data['total_rub'] = total_rub

        text = (
            f"{E_PURSE} <b>Расчёт и оформление оплаты (СБП)</b>\n\n"
            f"📦 <b>Выбранный товар:</b> {product[1]}\n"
            f"🔢 <b>Количество:</b> <code>{quantity} шт.</code>\n"
            f"🏷 <b>Цена за единицу:</b> <code>{product[3]} RUB</code>\n"
            f"{E_MONEY_BAG} <b>ИТОГО К ОПЛАТЕ:</b> <code>{total_rub} RUB</code>\n\n"
            f"{E_LOCK} <b>Реквизиты для перевода (Сбербанк):</b>\n"
            f"<code>{SBP_REQUISITES}</code>\n\n"
            f"{E_INFO} <b>Пошаговая инструкция:</b>\n"
            f"<blockquote>"
            f"1. Выполните перевод точной суммы ({total_rub} RUB) через СБП.\n"
            f"2. Сделайте скриншот чека об успешном переводе.\n"
            f"3. Отправьте скриншот в этот чат ответом на это сообщение."
            f"</blockquote>"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(make_btn("Отмена покупки", "main_menu", style="danger", emoji_id=EMOJI_CROSS_ID))
        bot.send_message(chat_id, text, reply_markup=kb)

# ----------------------------------------------------
# ОБРАБОТКА ЧЕКОВ И STARS
# ----------------------------------------------------

@bot.message_handler(state=FormStates.waiting_for_receipt, content_types=['photo'])
def handle_receipt_photo(message: types.Message):
    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            prod_id = data.get('buying_prod_id')
            qty = data.get('buying_qty', 1)
            total_rub = data.get('total_rub')

        product = db.get_product(prod_id)
        photo_id = message.photo[-1].file_id

        bot.delete_state(message.from_user.id, message.chat.id)
        bot.reply_to(
            message,
            f"{E_CHECK} <b>Чек успешно принят на проверку!</b>\n"
            f"Администрация верифицирует платеж в ближайшее время."
        )

        kb = types.InlineKeyboardMarkup()
        kb.add(
            make_btn("Подтвердить", f"adm_appr_{message.from_user.id}_{prod_id}_{qty}", style="success", emoji_id=EMOJI_CHECK_ID),
            make_btn("Отклонить", f"adm_rejc_{message.from_user.id}", style="danger", emoji_id=EMOJI_CROSS_ID)
        )

        for admin_id in ADMIN_IDS:
            try:
                bot.send_photo(
                    admin_id,
                    photo_id,
                    caption=(
                        f"📥 <b>Новый чек на проверку</b>\n\n"
                        f"{E_USER} <b>Покупатель:</b> @{message.from_user.username} (ID: <code>{message.from_user.id}</code>)\n"
                        f"📦 <b>Товар:</b> {product[1]}\n"
                        f"🔢 <b>Количество:</b> <code>{qty} шт.</code>\n"
                        f"{E_MONEY_BAG} <b>Сумма:</b> <code>{total_rub} RUB</code>"
                    ),
                    reply_markup=kb
                )
            except Exception as ex:
                logging.error(f"Admin notify error: {ex}")
    except Exception as e:
        logging.error(f"Error receipt_photo: {e}")

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(query: types.PreCheckoutQuery):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def process_stars_pay(message: types.Message):
    try:
        payload = message.successful_payment.invoice_payload.split("_")
        prod_id = int(payload[1])
        qty = int(payload[2]) if len(payload) > 2 else 1

        product = db.get_product(prod_id)

        if product and product[5] >= qty:
            db.decrease_stock(prod_id, qty)

            bot.send_message(
                message.chat.id,
                f"{E_PARTY} <b>Оплата Stars успешно проведена!</b>\n\n"
                f"📦 Товар <b>{product[1]}</b> ({qty} шт.) успешно передан!\n"
                f"{E_INFO} Служба поддержки: {SUPPORT_USERNAME}"
            )

            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(
                        admin_id,
                        f"⭐️ <b>Оплата Stars подтверждена!</b>\n"
                        f"Пользователь ID: <code>{message.from_user.id}</code>\n"
                        f"Товар: <b>{product[1]}</b> ({qty} шт.)"
                    )
                except Exception:
                    pass
    except Exception as e:
        logging.error(f"Error stars pay: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_appr_"))
def approve_order(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = call.data.split("_")
        u_id = int(parts[2])
        p_id = int(parts[3])
        qty = int(parts[4]) if len(parts) > 4 else 1

        product = db.get_product(p_id)
        if product and product[5] >= qty:
            db.decrease_stock(p_id, qty)

            try:
                bot.send_message(
                    u_id,
                    f"{E_PARTY} <b>Ваша оплата подтверждена!</b>\n\n"
                    f"Товар: <b>{product[1]}</b> ({qty} шт.) {E_LIGHTNING}"
                )
            except Exception:
                pass

            bot.edit_message_caption(call.message.caption + f"\n\n{E_CHECK} <b>СТАТУС: ПОДТВЕРЖДЕНО ({qty} шт.)</b>", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Ошибка: не хватает товара в наличии!", show_alert=True)
    except Exception as e:
        logging.error(f"Approve error: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_rejc_"))
def reject_order(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    try:
        u_id = int(call.data.split("_")[2])
        try:
            bot.send_message(u_id, f"{E_CROSS} <b>Ваш платёж был отклонён администратором.</b>")
        except Exception:
            pass
        bot.edit_message_caption(call.message.caption + f"\n\n{E_CROSS} <b>СТАТУС: ОТКЛОНЕНО</b>", call.message.chat.id, call.message.message_id)
    except Exception as e:
        logging.error(f"Reject error: {e}")

# ----------------------------------------------------
# АДМИН-ПАНЕЛЬ
# ----------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data == "admin_panel")
def show_admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Доступ ограничен!", show_alert=True)
        return

    text = (
        f"{E_BOT} <b>Панель управления администратора</b>\n\n"
        f"{E_DESK} Управляйте товарами, проводите рассылки и просматривайте каталог:"
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_admin_panel_kb())

@bot.callback_query_handler(func=lambda c: c.data == "admin_add_product")
def start_add_prod(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.set_state(call.from_user.id, FormStates.add_title, call.message.chat.id)
    bot.send_message(call.message.chat.id, "<b>Шаг 1/7:</b> Введите <b>название товара</b>:")

@bot.message_handler(state=FormStates.add_title)
def step_title(message: types.Message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['title'] = message.text
    bot.set_state(message.from_user.id, FormStates.add_desc, message.chat.id)
    bot.send_message(message.chat.id, "<b>Шаг 2/7:</b> Введите <b>подробное описание</b>:")

@bot.message_handler(state=FormStates.add_desc)
def step_desc(message: types.Message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['desc'] = message.text
    bot.set_state(message.from_user.id, FormStates.add_price_rub, message.chat.id)
    bot.send_message(message.chat.id, "<b>Шаг 3/7:</b> Введите <b>цену за 1 шт. в RUB</b> (например: 500):")

@bot.message_handler(state=FormStates.add_price_rub)
def step_price_rub(message: types.Message):
    try:
        val = float(message.text)
        if val <= 0:
            bot.send_message(message.chat.id, "❌ Ошибка! Цена должна быть больше нуля.")
            return
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['price_rub'] = val
        bot.set_state(message.from_user.id, FormStates.add_price_stars, message.chat.id)
        bot.send_message(message.chat.id, "<b>Шаг 4/7:</b> Введите <b>цену за 1 шт. в Telegram Stars</b> (например: 250):")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка! Введите числовое значение.")

@bot.message_handler(state=FormStates.add_price_stars)
def step_price_stars(message: types.Message):
    try:
        val = int(message.text)
        if val <= 0:
            bot.send_message(message.chat.id, "❌ Ошибка! Цена должна быть больше нуля.")
            return
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['price_stars'] = val
        bot.set_state(message.from_user.id, FormStates.add_stock, message.chat.id)
        bot.send_message(message.chat.id, "<b>Шаг 5/7:</b> Введите <b>доступное количество товара</b> (например: 1000000):")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка! Введите целое число.")

@bot.message_handler(state=FormStates.add_stock)
def step_stock(message: types.Message):
    try:
        val = int(message.text)
        if val < 0:
            bot.send_message(message.chat.id, "❌ Ошибка! Количество не может быть отрицательным.")
            return
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['stock'] = val
        bot.set_state(message.from_user.id, FormStates.add_photo, message.chat.id)

        kb = types.InlineKeyboardMarkup()
        kb.add(make_btn("Пропустить добавление фото", "skip_photo", style="primary"))
        bot.send_message(message.chat.id, "<b>Шаг 6/7:</b> Отправьте <b>фотографию</b> товара или нажмите пропустить:", reply_markup=kb)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка! Введите целое число.")

@bot.message_handler(state=FormStates.add_photo, content_types=['photo'])
def step_photo(message: types.Message):
    photo_id = message.photo[-1].file_id
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['photo_id'] = photo_id
    ask_is_quantity_step(message.from_user.id, message.chat.id)

@bot.callback_query_handler(state=FormStates.add_photo, func=lambda c: c.data == "skip_photo")
def step_photo_skip(call: types.CallbackQuery):
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['photo_id'] = None
    ask_is_quantity_step(call.from_user.id, call.message.chat.id)

def ask_is_quantity_step(user_id: int, chat_id: int):
    bot.set_state(user_id, FormStates.add_is_quantity, chat_id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        make_btn("☑️ Да (Количественный)", "set_qty_yes", style="success", emoji_id=EMOJI_CHECK_ID),
        make_btn("✖️ Нет (Одиночный)", "set_qty_no", style="danger", emoji_id=EMOJI_CROSS_ID)
    )
    bot.send_message(
        chat_id,
        "<b>Шаг 7/7:</b> 🔢 <b>Сделать товар количественным?</b>\n\n"
        "<i>Если выбрано «Да», покупатель при заказе сможет сам указать нужное ему количество товара, а итоговый чек и сумма рассчитаются автоматически.</i>",
        reply_markup=kb
    )

@bot.callback_query_handler(state=FormStates.add_is_quantity, func=lambda c: c.data in ["set_qty_yes", "set_qty_no"])
def step_is_quantity_choice(call: types.CallbackQuery):
    is_qty = 1 if call.data == "set_qty_yes" else 0
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['is_quantity'] = is_qty
    confirm_create_product(call.from_user.id, call.message.chat.id)

def confirm_create_product(user_id: int, chat_id: int):
    with bot.retrieve_data(user_id, chat_id) as data:
        qty_str = "Да (можно указывать при покупке)" if data.get('is_quantity') == 1 else "Нет (одиночный товар)"
        text = (
            f"<b>Проверка создаваемого товара:</b>\n\n"
            f"📌 <b>Название:</b> {data['title']}\n"
            f"📝 <b>Описание:</b> {data['desc']}\n"
            f"💵 <b>Цена RUB:</b> {data['price_rub']}\n"
            f"⭐️ <b>Цена Stars:</b> {data['price_stars']}\n"
            f"📊 <b>Количество на складе:</b> {data['stock']} шт.\n"
            f"🔢 <b>Количественный товар:</b> {qty_str}"
        )
    bot.set_state(user_id, FormStates.add_confirm, chat_id)
    kb = types.InlineKeyboardMarkup()
    kb.add(make_btn("Подтвердить и сохранить", "save_product_final", style="success", emoji_id=EMOJI_CHECK_ID))
    kb.add(make_btn("Отмена", "admin_panel", style="danger", emoji_id=EMOJI_CROSS_ID))
    bot.send_message(chat_id, text, reply_markup=kb)

@bot.callback_query_handler(state=FormStates.add_confirm, func=lambda c: c.data == "save_product_final")
def save_product_final(call: types.CallbackQuery):
    try:
        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            db.add_product(
                title=data['title'],
                desc=data['desc'],
                price_rub=data['price_rub'],
                price_stars=data['price_stars'],
                stock=data['stock'],
                photo_id=data.get('photo_id'),
                is_quantity=data.get('is_quantity', 0)
            )
        bot.delete_state(call.from_user.id, call.message.chat.id)
        bot.send_message(call.message.chat.id, f"{E_CHECK} <b>Товар успешно внесён в базу!</b>", reply_markup=get_admin_panel_kb())
    except Exception as e:
        logging.error(f"Save product error: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "admin_list_products")
def admin_list_products(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    products = db.get_all_products(only_in_stock=False)
    kb = types.InlineKeyboardMarkup()

    for p in products:
        p_id, title, _, _, _, stock, _, _, is_quantity = p
        badge = " 🔢" if is_quantity else ""
        kb.add(make_btn(f"{title}{badge} ({stock} шт.)", f"adm_prod_manage_{p_id}", style="primary", emoji_id=EMOJI_CART_ID))

    kb.add(make_btn("Назад в админку", "admin_panel", style="danger", emoji_id=EMOJI_CROSS_ID))
    bot.edit_message_text("<b>Список всех созданных товаров:</b>", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_prod_manage_"))
def admin_prod_manage(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    p_id = int(call.data.split("_")[3])
    p = db.get_product(p_id)
    if not p:
        bot.answer_callback_query(call.id, "Товар не найден!")
        return

    qty_type_str = "Да" if p[8] else "Нет"
    text = (
        f"<b>Параметры товара:</b>\n\n"
        f"📌 Название: {p[1]}\n"
        f"📝 Описание: {p[2]}\n"
        f"💵 RUB: {p[3]} | Stars: {p[4]}\n"
        f"📊 Ост. в наличии: {p[5]} шт.\n"
        f"🔢 Количественный: {qty_type_str}"
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(make_btn("Удалить товар", f"adm_del_prod_{p_id}", style="danger", emoji_id=EMOJI_CROSS_ID))
    kb.add(make_btn("Назад к списку", "admin_list_products", style="primary", emoji_id=EMOJI_CART_ID))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_prod_"))
def admin_delete_product(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    p_id = int(call.data.split("_")[3])
    db.delete_product(p_id)
    bot.answer_callback_query(call.id, "Товар успешно удален!")
    admin_list_products(call)

@bot.callback_query_handler(func=lambda c: c.data == "admin_broadcast")
def admin_broadcast_start(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.set_state(call.from_user.id, FormStates.broadcast_msg, call.message.chat.id)
    kb = types.InlineKeyboardMarkup()
    kb.add(make_btn("Отмена рассылки", "admin_panel", style="danger", emoji_id=EMOJI_CROSS_ID))
    bot.send_message(call.message.chat.id, f"{E_PLANE} Введите текст сообщения для рассылки пользователям:", reply_markup=kb)

@bot.message_handler(state=FormStates.broadcast_msg)
def admin_broadcast_exec(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot.delete_state(message.from_user.id, message.chat.id)
    users = db.get_all_users()

    success = 0
    failed = 0

    status_msg = bot.send_message(message.chat.id, f"🚀 Запуск рассылки по базам...")

    for u_id in users:
        try:
            bot.send_message(u_id, message.text)
            success += 1
            time.sleep(0.04)
        except Exception:
            failed += 1

    text_res = (
        f"{E_CHECK} <b>Рассылка успешно завершена!</b>\n\n"
        f"🟢 Доставлено: <b>{success}</b>\n"
        f"🔴 Ошибок: <b>{failed}</b>"
    )
    bot.edit_message_text(text_res, message.chat.id, status_msg.message_id, reply_markup=get_admin_panel_kb())

# ----------------------------------------------------
# ЗАПУСК
# ----------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"🤖 Бот {SHOP_NAME} успешно запущен!")

    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as err:
            logging.error(f"Сбой: {err}")
            time.sleep(5)