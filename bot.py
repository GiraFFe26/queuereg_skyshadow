from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import asyncio
from seller import DigisellerApi
from config import ADMINS, TOKEN


bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class UserState(StatesGroup):
    login = State()
    password = State()
    item = State()
    value = State()
    comment = State()
    accept = State()


async def token():
    while True:
        DigisellerApi().get_token()
        await asyncio.sleep(3600)


async def clear_sheet():
    while True:
        DigisellerApi().del_lines()
        await asyncio.sleep(86400)


async def sales():
    while True:
        DigisellerApi().get_sales()
        await asyncio.sleep(180)


@dp.message_handler(commands='start')
async def menu(message: types.Message):
    if message.from_user.id in ADMINS:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Добавить заказ')
        # отправка начального сообщения после кнопки start
        await message.answer('Ты в главном меню бота', reply_markup=keyboard)


@dp.message_handler(Text(equals='Добавить заказ'))
async def get_login(message: types.Message):
    if message.from_user.id in ADMINS:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Отмена')
        await message.answer('Введите логин пользователя', reply_markup=keyboard)
        await UserState.login.set()


@dp.message_handler(state=UserState.login)
async def get_password(message: types.Message, state: FSMContext):
    msg = message.text
    if msg == 'Отмена':
        await state.finish()
        await menu(message)
    else:
        await state.update_data(login=msg)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Отмена')
        await message.answer('Введите пароль пользователя', reply_markup=keyboard)
        await UserState.next()


@dp.message_handler(state=UserState.password)
async def get_product(message: types.Message, state: FSMContext):
    msg = message.text
    if msg == 'Отмена':
        await state.finish()
        await menu(message)
    else:
        await state.update_data(password=msg)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Отмена')
        await message.answer('Введите название товара', reply_markup=keyboard)
        await UserState.next()


@dp.message_handler(state=UserState.item)
async def get_amount(message: types.Message, state: FSMContext):
    msg = message.text
    if msg == 'Отмена':
        await state.finish()
        await menu(message)
    else:
        await state.update_data(item=msg)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Отмена')
        await message.answer('Введите кол-во товара', reply_markup=keyboard)
        await UserState.next()


@dp.message_handler(state=UserState.value)
async def get_status(message: types.Message, state: FSMContext):
    msg = message.text
    if msg == 'Отмена':
        await state.finish()
        await menu(message)
    else:
        await state.update_data(value=msg)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Да').add('Нет').add('Вход по одобрению').add('Отмена')
        await message.answer('Заказ зареган в боте?', reply_markup=keyboard)
        await UserState.next()


@dp.message_handler(state=UserState.comment)
async def get_accept(message: types.Message, state: FSMContext):
    msg = message.text
    if msg == 'Отмена':
        await state.finish()
        await menu(message)
    else:
        if msg == 'Да':
            msg = '✅'
        elif msg == 'Нет':
            msg = '❌'
        elif msg == 'Вход по одобрению':
            msg = '📱'
        await state.update_data(comment=msg)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Отправить в таблицу').add('Отмена')
        await message.answer('Отправить заказ в таблицу?', reply_markup=keyboard)
        await UserState.next()


@dp.message_handler(state=UserState.accept)
async def accept(message: types.Message, state: FSMContext):
    msg = message.text
    if msg == 'Отмена':
        await state.finish()
        await menu(message)
    elif msg == 'Отправить в таблицу':
        data = await state.get_data()
        await state.finish()
        if message.from_user.id == ADMINS[0]:
            owner = 'GiraFFe'
        else:
            owner = 'hatexx'
        ans = DigisellerApi().send_to_sheets(owner, data['login'], data['password'], data['item'],
                                             data['value'], data['comment'])
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add('Добавить заказ')
        await message.answer(ans, reply_markup=keyboard)

if __name__ == '__main__':
    asyncio.get_event_loop().create_task(token())
    asyncio.get_event_loop().create_task(clear_sheet())
    asyncio.get_event_loop().create_task(sales())
    executor.start_polling(dp, skip_updates=True)

