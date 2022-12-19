from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup

def main():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('Хочу узнать первым')
    return markup

def choose():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('Блогер', 'Пользователь')
    return markup

def cancel():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="Отмена", callback_data="cancel"))
    return markup

def from_str(text: str):
    markup = InlineKeyboardMarkup()
    for line in text.split("\n"):
        sign, url = line.split(" - ")
        markup.add(InlineKeyboardButton(text=sign, url=url))
    markup.to_python()
    return markup


def sub_channel(channels: dict, bots) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    for i, channel_url in enumerate(channels.keys(), start=1):
        markup.add(
            InlineKeyboardButton(
                text = f"Подписаться #{i}".format(i=i),
                url = channel_url
            )
        )
    for i, bot_url in enumerate(bots, start=len(channels) + 1):
        markup.add(
            InlineKeyboardButton(
                text=f"Подписаться #{i}".format(i=i),
                url=bot_url
            )
        )
    markup.add(
        InlineKeyboardButton(
            text = "Зарегистрироваться",
            callback_data = "sub"
        )
    )
    return markup
