#!/usr/bin/env python3
import json
import logging
import sys
from typing import Dict

from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove, KeyboardButton, InputMediaPhoto
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    PicklePersistence,
)

import requests
import pathlib
from requests.auth import HTTPDigestAuth

global config
global domlist

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

GETTING_PHONE, GOT_PHONE = range(2)

give_me_phone_keyboard_markup = ReplyKeyboardMarkup.from_button(KeyboardButton(text="Відправити боту номер телефону", request_contact=True))

def get_domophone_list():
    url = config["opener_url"] + "/auth_digest/intercoms"
    response = requests.get(url, auth=HTTPDigestAuth(config["opener_user"], config["opener_password"]))
    return response.json()

def domophone_snapshot(idx: int):
    url = config["opener_url"] + "/auth_digest/intercoms/%d/big_picture" % idx
    response = requests.get(url, auth=HTTPDigestAuth(config["opener_user"], config["opener_password"]))
    return response.content

def domophone_open(idx: int):
    url = config["opener_url"] + "/auth_digest/intercoms/%d/open_door" % idx
    response = requests.get(url, auth=HTTPDigestAuth(config["opener_user"], config["opener_password"]))
    return


def facts_to_str(user_data: Dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    facts = [f'{key} - {value}' for key, value in user_data.items()]
    return "\n".join(facts).join(['\n', '\n'])

def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask user for input."""
    update.message.reply_text(
        "Вітання! Це бот для відкривання дверей в Gloria Park. Поділіться вашим телефоном, щоб я міг дізнатись чи ви у списку користувачів",
        reply_markup=give_me_phone_keyboard_markup,
    )

    return GETTING_PHONE


def received_phone(update: Update, context: CallbackContext) -> int:
    phone = update.message.contact.phone_number
    if phone not in config["users"]:
        update.message.reply_text(
            f"Телефон +%s не у списку. Ви не можете користуватись ботом-консьєржем" % update.message.contact.phone_number,
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return ConversationHandler.END

    domlist = get_domophone_list()

    #Create open keyboard
    reply_keyboard = []
    # context.dispatcher.handlers.
    for dom_idx in range(0, len(domlist)):
        if "section" in domlist[dom_idx].keys():
            if domlist[dom_idx]["section"] != config["users"][phone]["section"]:
                continue
        kb_open = KeyboardButton(text="Відкрити " + domlist[dom_idx]["description"])
        kb_snapshot = KeyboardButton(text="Фото з " + domlist[dom_idx]["description"])
        reply_keyboard.append([kb_open, kb_snapshot])
    update.message.reply_text(
        f"Телефон +%s у списку. Для зручності користування, використайте віджет телеграму, в який можна додати на основний екран смартфону (втім це не обов'язково). Інструкції на скрінах" % (phone),
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )

    update.message.reply_media_group(
        [InputMediaPhoto(pathlib.Path("instructions/1.jpg").read_bytes()),
         InputMediaPhoto(pathlib.Path("instructions/2.jpg").read_bytes()),
         InputMediaPhoto(pathlib.Path("instructions/3.jpg").read_bytes()),
         InputMediaPhoto(pathlib.Path("instructions/4.jpg").read_bytes()),
         InputMediaPhoto(pathlib.Path("instructions/5.jpg").read_bytes()),
         InputMediaPhoto(pathlib.Path("instructions/6.jpg").read_bytes()),
         InputMediaPhoto(pathlib.Path("instructions/7.jpg").read_bytes()),
         InputMediaPhoto(pathlib.Path("instructions/8.jpg").read_bytes())])
    context.user_data["phone"] = update.message.contact.phone_number
    context.user_data["intercoms"] = domlist
    return GOT_PHONE

def open_command(update: Update, context: CallbackContext):
    for dom_idx in range(0, len(domlist)):
        if domlist[dom_idx]["description"] in update.message.text:
            update.message.reply_text("Відкриваю двері")
            domophone_open(dom_idx)
            update.message.reply_text("Відкрито")
            return
    update.message.reply_text("Не знайдено такого домофона")
    return GOT_PHONE

def snapshot_command(update: Update, context: CallbackContext):
    for dom_idx in range(0, len(domlist)):
        if domlist[dom_idx]["description"] in update.message.text:
            update.message.reply_text("Роблю фото")
            update.message.reply_photo(domophone_snapshot(dom_idx))
            return
    update.message.reply_text("Не знайдено такого домофона")
    return GOT_PHONE

def done(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    update.message.reply_text(
        f"Допобачення",
        reply_markup=ReplyKeyboardRemove(),
    )
    user_data.clear()
    return ConversationHandler.END

def main() -> None:
    global config
    global domlist
    if len(sys.argv) == 2:
        with open(sys.argv[1], "r") as f:
            config = f.read()
    else:
        sys.exit(1)

    config = json.loads(config)
    persistence = PicklePersistence(filename='conversation_archive')
    updater = Updater(config["api-token"], persistence=persistence)

    dispatcher = updater.dispatcher
    domlist = get_domophone_list()
    states = {
        GETTING_PHONE: [
            MessageHandler(
                Filters.reply & Filters.contact, received_phone
            )
        ],
        GOT_PHONE: [
            MessageHandler(Filters.regex(r"^Відкрити\s+"), open_command),
            MessageHandler(Filters.regex(r"^Фото\s+з\s+"), snapshot_command),
        ],
    }

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states=states,
        fallbacks=[MessageHandler(Filters.regex('^Done$'), done)],
        name="GloriaContext",
        persistent=True,
        per_user=True
    )

    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
