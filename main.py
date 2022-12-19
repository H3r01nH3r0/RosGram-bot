import keyboards
from time import sleep
from aiogram import Bot, Dispatcher, types, filters, executor
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.mongo import MongoStorage
from db import DataBase
from utils import get_config, save_config, str2file, check_int
from time import time
from asyncio import sleep


config_filename = "config.json"
config = get_config(config_filename)
db = DataBase(config["db_url"], config["db_name"])
bot = Bot(token=config["bot_token"], parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MongoStorage(db_name=config["db_name"], uri=config["db_url"]))
owners_filter = filters.IDFilter(user_id=config["owners"])

class Form(StatesGroup):
    lang = State()
    mailing = State()
    mailing_markup = State()
    show = State()
    show_markup = State()
    name = State()


class UsersMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super(UsersMiddleware, self).__init__()

    async def on_pre_process_message(self, message: types.Message, data: dict) -> None:
        user = {}
        if message.chat.type == types.ChatType.PRIVATE:
            user_id = message.chat.id
            user = db.get_user(user_id)
            if not user:
                db.add_user(user_id)
                user = db.get_user(user_id)
        data["user"] = user

async def is_subscribed(user_id: int) -> bool:
    arg = await sub_channels(user_id)
    for channel_id in arg.values():
        chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if not chat_member.is_chat_member():
            return False
    return True

async def sub_channels(user_id: int):
    channels = {**config["channels"]}
    dict_one = channels.copy()
    print(dict_one)
    for channel in dict_one:
        chat_member = await bot.get_chat_member(chat_id=channels.get(channel), user_id=user_id)
        if chat_member.is_chat_member():
            del channels[channel]
    return channels

async def on_shutdown(dp: Dispatcher) -> None:
    save_config(config_filename, config)
    db.close()
    await dp.storage.close()
    await dp.storage.wait_closed()

@dp.message_handler(owners_filter, commands=["users", "count"])
async def owners_users_command_handler(message: types.Message) -> None:
    count = db.get_users_count()
    await message.answer(text=config["texts"]["users_count"].format(count=count))


@dp.message_handler(owners_filter, commands=["export"])
async def owners_export_command_handler(message: types.Message) -> None:
    msg = await message.answer(text=config["texts"]["please_wait"])
    file = str2file(" ".join([str(user["user_id"]) for user in db.get_user()]), "users.txt")
    try:
        await message.answer_document(file)
    except:
        await message.answer(text=config["texts"]["no_users"])
    await msg.delete()



@dp.message_handler(owners_filter, commands=["mail", "mailing"])
async def owners_mailing_command_handler(message: types.Message) -> None:

    await Form.mailing.set()

    await message.answer(
        text=config["texts"]["enter_mailing"],
        reply_markup=keyboards.cancel()
    )


@dp.message_handler(content_types=types.ContentType.all(), state=Form.mailing)
async def owners_process_mailing_handler(message: types.Message, state: FSMContext) -> None:

    async with state.proxy() as data:
        data["message"] = message.to_python()

    await Form.mailing_markup.set()

    await message.answer(
        config["texts"]["enter_mailing_markup"],
        reply_markup=keyboards.cancel()
    )


@dp.message_handler(state=Form.mailing_markup)
async def owners_process_mailing_markup_handler(message: types.Message, state: FSMContext) -> None:

    if message.text not in ["-", "."]:
        try:
            markup = keyboards.from_str(message.text)

        except:
            await message.answer(
                text=config["texts"]["incorrect_mailing_markup"],
                reply_markup=keyboards.cancel()
            )

            return

    else:
        markup = types.InlineKeyboardMarkup()

    markup = markup.to_python()

    async with state.proxy() as data:
        _message = data["message"]

    total = 0
    sent = 0
    unsent = 0

    await state.finish()

    await message.answer(config["texts"]["start_mailing"])

    start = time()

    kwargs = {
        "from_chat_id": _message["chat"]["id"],
        "message_id": _message["message_id"],
        "reply_markup": markup
    }

    for user in db.get_user():
        kwargs["chat_id"] = user["user_id"]

        try:
            await bot.copy_message(**kwargs)
            sent += 1

        except:
            unsent += 1

        total += 1

        await sleep(config["sleep_time"])

    await message.answer(
        config["texts"]["mailing_stats"].format(
            total=total,
            sent=sent,
            unsent=unsent,
            time=round(time() - start, 3)
        )
    )

@dp.message_handler(owners_filter, commands=["add_channel"])
async def owners_add_channel_command_handler(message: types.Message) -> None:


    args = message.text.split(" ")[1:]

    if len(args) < 2 or not check_int(args[1]):
        await message.answer(text=config["texts"]["incorrect_value"])
        return

    config["channels"][args[0]] = int(args[1])
    save_config(config_filename, config)

    await message.answer(text=config["texts"]["saved"])

@dp.message_handler(owners_filter, commands=["remove_channel"])
async def owners_add_channel_command_handler(message: types.Message) -> None:

    args = message.text.split(" ")[1:]

    if len(args) < 1 or not check_int(args[0]):
        await message.answer(text=config["texts"]["incorrect_value"])
        return

    channel_id = int(args[0])

    for url in config["channels"]:
        if config["channels"].get(url) == channel_id:
            del config["channels"][url]
            break

    save_config(config_filename, config)

    await message.answer(text=config["texts"]["saved"])

@dp.message_handler(owners_filter, commands=["remove_all_channels"])
async def owners_add_channel_command_handler(message: types.Message) -> None:

    config["channels"].clear()
    save_config(config_filename, config)

    await message.answer(text=config["texts"]["saved"])

@dp.message_handler(owners_filter, commands=["add_bot"])
async def owners_add_channel_command_handler(message: types.Message) -> None:
    args = message.text.split(" ")[1:]
    bot_url = args[0]
    config['bots'].append(bot_url)
    save_config(config_filename, config)
    await message.answer(text=config["texts"]["saved"])

@dp.message_handler(owners_filter, commands=["remove_bot"])
async def owners_add_channel_command_handler(message: types.Message) -> None:
    args = message.text.split(" ")[1:]
    bot_url = args[0]
    config['bots'].remove(bot_url)
    save_config(config_filename, config)
    await message.answer(text=config["texts"]["saved"])

@dp.message_handler(owners_filter, commands=["remove_all_bots"])
async def owners_add_channel_command_handler(message: types.Message) -> None:
    config['bots'].clear()
    save_config(config_filename, config)
    await message.answer(text=config["texts"]["saved"])

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message) -> None:
    user_id = message.chat.id
    user = db.get_user(user_id)
    if not user:
        db.add_user(user_id)
        user = db.get_user(user_id)
    await bot.send_photo(message.from_user.id, open('files/1.jpg', 'rb'))
    await bot.send_message(
        message.from_user.id,
        text='Россграм планирует запуститься 28 марта 2022 года для партнеров (СМИ, спонсоры, инвесторы), затем '
             'расширит свою работу для блогеров и наконец для остальных пользователей.',
    )
    await bot.send_message(
        message.from_user.id,
        text='Больше никаких VPN и ограничений - можно заходить из любой точки России.Не надо привыкать к непонятным'
             ' словам и искать нужные кнопки - интерфейс максимально простой и понятный для любого пользователя.В '
             'Россграм предусмотрены все возможности для общения, бизнеса, ведения блога, публикации новостей или '
             'создания собственного проекта.Не важно - пишете ли вы друзьям или развиваете любимое дело - вам будет '
             'одинаково комфортно и привычно в этой среде.',
        reply_markup=keyboards.main()

    )

@dp.message_handler(content_types = ['text'])
async def bot_message(message: types.Message):
    if message.text == 'Хочу узнать первым':
        await bot.send_message(message.from_user.id, text='Выберите кто вы', reply_markup=keyboards.choose())
    elif message.text in ('Блогер', 'Пользователь'):
        await bot.send_message(message.from_user.id, text='Введите ваш аккаунт/канал/группу в телеграм')
        await Form.name.set()

@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text

    await state.finish()
    await message.answer(text='Спасибо за обратную связь! Ожидайте, Ваш запрос на рассмотрении у модератора. В связи с '
                              'большой загруженностью срок рассмотрения заявки может быть увеличен. Будьте в числе '
                              'первых, займите свою нишу, общайтесь, развивайтесь, отдыхайте вместе с Россграм!')
    await sleep(10)
    await bot.send_message(message.from_user.id, text='Поздравляем, Вы прошли модерацию! Для того чтобы приступить к '
                                                      'бета-тестированию платформы Россграм, просим Вас отправить '
                                                      'ссылку для приглашения вашим друзьями, коллегам и близким. Нам '
                                                      'важно отследить нагрузку на наш сервер.'
                                                      '\nhttp://t.me/rossgram_russia_bot')
    await sleep(10)
    arg = await sub_channels(message.from_user.id)
    bots = config['bots']
    await bot.send_message(message.from_user.id, text='Уважаемый пользователь, считанные часы остались до запуска нашей'
                                                      ' платформы! Предоставляем Вам возможность бесплатно '
                                                      'забронировать никнейм и получить ссылку в нашем приложении!\nДля'
                                                      ' бронирования желаемого имени в приложении и получении ссылки на'
                                                      ' регистрацию, просим Вас подписаться на каналы наших партнеров и'
                                                      ' в обратном сообщении указать желаемый никнейм.\n\nПосле '
                                                      'подписки нажимай кнопку «Зарегистрироваться» и желаемый ник',
                           reply_markup=keyboards.sub_channel(arg, bots))

@dp.callback_query_handler(state="*")
async def callback_query_handler(callback_query: types.CallbackQuery) -> None:
    if callback_query.data == "sub":
        if not await is_subscribed(callback_query.from_user.id):
            arg = await sub_channels(callback_query.from_user.id)
            bots = config['bots']
            await bot.send_message(callback_query.from_user.id, text='Для продолжения необходимо подписаться каналы '
                                                                     'наших партнеров',
                                   reply_markup=keyboards.sub_channel(arg, bots))
            return
        else:
            await bot.send_message(callback_query.from_user.id, text='Информация принята, ожидайте ссылку')

dp.middleware.setup(UsersMiddleware())

if __name__ == '__main__':
    executor.start_polling(dispatcher=dp, skip_updates=False, on_shutdown=on_shutdown)

