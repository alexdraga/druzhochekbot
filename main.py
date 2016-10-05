# -*- coding: utf-8 -*-
from time import sleep

from config.config import config
from telegram.worker import TelegramWorker

bot = TelegramWorker()

initialized = bot.setup_bot(config.game_login,
                            config.game_password,
                            config.game_host,
                            config.game_id)
while not initialized:
    initialized = bot.setup_bot(config.game_login,
                                config.game_password,
                                config.game_host,
                                config.game_id)
    sleep(1)

while not bot.stopped and initialized is not None:
    bot.process_messages()
    bot.process_game_tasks()
    sleep(1)