# -*- coding: utf-8 -*-
import time

from config.config import config
from game.driver import GameDriver
from game.worker import GameWorker
from telegram.dictionary import PAUSED_MESSAGES, GREETINGS_MESSAGES, LETS_GO_MESSAGES, START_PAUSE_MESSAGES, \
    RESUME_MESSAGES, END_PAUSE_MESSAGES, BYE_MESSAGES, NO_CODE_FOUND_MESSAGE, GIVE_ME_LOGIN, GIVE_ME_PASSWORD, \
    GIVE_ME_HOST, GIVE_ME_GAME, AFFIRMATIVE_MESSAGES, NOT_GROUP_CHAT_MESSAGES, CONNECTION_PROBLEM_MESSAGES, \
    CONNECTION_OK_MESSAGES, PLEASE_APPROVE_MESSAGES, TOO_MUCH_ATTEMPTS_MESSAGES, ACCESS_VIOLATION_MESSAGES, \
    ALREADY_PAUSED_MESSAGES, UNKNOWN_MESSAGES, WRONG_CODE_MESSAGE, STATUS_MESSAGE, \
    PAUSED_STATUS_MESSAGES, GAME_CONNECTION_MESSAGES, INFO_MESSAGE, NOT_FOR_GROUP_CHAT_MESSAGES, NO_GROUP_CHAT_MESSAGES, \
    DISAPPROVE_MESSAGES
from telegram.driver import TelegramDriver

# TODO: To class attributes?
MAX_ATTEMPTS = 5
DRAGA_ID = 170302127
APPROVE_COMMAND = '/approve'
DISAPPROVE_COMMAND = '/disapprove'
CODE_COMMAND = '/c'
CODES_COMMAND = '/cc'
PAUSE_COMMAND = '/pause'
RESUME_COMMAND = '/resume'
STOP_COMMAND = '/stop'
CHANGE_SETTINGS_COMMAND = '/change'
STATUS_COMMAND = '/status'
INFO_COMMAND = '/info'

# Commands, that should be processed on any bot state
HIGH_LEVEL_COMMANDS = [STOP_COMMAND,
                       RESUME_COMMAND,
                       APPROVE_COMMAND]

# Commands, that should be processed in group chat only
GROUP_CHAT_COMMANDS = [CODE_COMMAND, CODES_COMMAND, APPROVE_COMMAND]

# Commands that allowed only for admins
ADMIN_COMMANDS = [APPROVE_COMMAND,
                  STOP_COMMAND,
                  RESUME_COMMAND,
                  PAUSE_COMMAND,
                  INFO_COMMAND,
                  CHANGE_SETTINGS_COMMAND]

# Commands that are forbidden to execute in group chat unless
# this group chat is approved to use
GROUP_CHAT_IGNORE_COMMANDS = [PAUSE_COMMAND, CODE_COMMAND, CODES_COMMAND, STATUS_COMMAND]

# Commands that are allowed for other users in private messages
PRIVATE_COMMANDS = []


class TelegramWorker:
    def __init__(self):
        self.telegram_driver = TelegramDriver()
        self.telegram_driver.get_updates()
        self.initial_message = None
        self.initialize_attempts = 0
        self.paused = False
        self.stopped = False
        self.game_worker = None
        self.chat_id = None

        # Messages dictionary
        self.pause_messages = 0
        self.resume_messages = 0

    def setup_bot(self,
                  game_login=None,
                  game_password=None,
                  game_host=None,
                  game_id=None):
        messages = self.check_new_messages()
        if self.initialize_attempts == 0:
            self.telegram_driver.send_message(
                DRAGA_ID,
                "<b>-----------------------------------------</b>\r\n\r\n",
                parse_mode="HTML")
        if self.initialize_attempts >= MAX_ATTEMPTS:
            self.stopped = True
            self.telegram_driver.send_message(
                DRAGA_ID,
                TOO_MUCH_ATTEMPTS_MESSAGES)
            self.telegram_driver.send_message(
                DRAGA_ID,
                BYE_MESSAGES)
            return True

        for message in messages:
            message_text = message['message']['text']
            from_id = message['message']['from']['id']
            if message_text.startswith(STOP_COMMAND) and from_id == DRAGA_ID:
                self._do_stop(message)
                return True

        self.telegram_driver.send_message(
            DRAGA_ID,
            GREETINGS_MESSAGES)
        if game_login is None:
            self.telegram_driver.send_message(
                DRAGA_ID,
                GIVE_ME_LOGIN)
            GameDriver.login = self.wait_for_answer(DRAGA_ID)['message']['text']
        else:
            GameDriver.login = game_login
        if game_password is None:
            self.telegram_driver.send_message(
                DRAGA_ID,
                GIVE_ME_PASSWORD)
            GameDriver.password = self.wait_for_answer(DRAGA_ID)['message']['text']
        else:
            GameDriver.password = game_password
        if game_host is None:
            self.telegram_driver.send_message(
                DRAGA_ID,
                GIVE_ME_HOST)
            GameDriver.host = self.wait_for_answer(DRAGA_ID)['message']['text']
        else:
            GameDriver.host = game_host
        if game_id is None:
            self.telegram_driver.send_message(
                DRAGA_ID,
                GIVE_ME_GAME)
            GameDriver.game_id = self.wait_for_answer(DRAGA_ID)['message']['text']
        else:
            GameDriver.game_id = game_id
        self.game_worker = GameWorker()
        if self.game_worker.connected:
            self.telegram_driver.send_message(
                DRAGA_ID,
                CONNECTION_OK_MESSAGES)
            self.telegram_driver.send_message(
                DRAGA_ID,
                PLEASE_APPROVE_MESSAGES)
            self.initialize_attempts = 0
            return True
        else:
            self.telegram_driver.send_message(
                DRAGA_ID,
                CONNECTION_PROBLEM_MESSAGES)
            self.initialize_attempts += 1
            return False

    @staticmethod
    def check_answer_from_chat_id(chat_id, messages):
        for message in messages:
            if message['message']['from']['id'] == chat_id \
                    and 'text' in message['message']:
                return message

    def wait_for_answer(self, chat_id):
        answer = self.check_answer_from_chat_id(DRAGA_ID,
                                                self.check_new_messages())
        while answer is None:
            answer = self.check_answer_from_chat_id(DRAGA_ID,
                                                    self.check_new_messages())
            time.sleep(1)
        return answer

    def check_new_messages(self):
        """
        :return:
        :rtype: list of dict
        """
        messages_with_text = []
        messages = self.telegram_driver.get_updates()
        for message in messages:
            if 'message' in message and 'text' in message['message']:
                messages_with_text.append(message)
        return messages_with_text

    def check_codes(self, message):
        codes = message['message']['text'].replace(CODES_COMMAND, '').rstrip().lstrip()
        codes = codes.split()
        results = NO_CODE_FOUND_MESSAGE
        if len(codes):
            results = ''
            for code in codes:
                result = self.game_worker.game_driver.try_code(code)
                if result:
                    results += u'\r\n{code}: +'.format(code=code)
                else:
                    results += u'\r\n{code}: {wrong}'.format(code=code,
                                                             wrong=WRONG_CODE_MESSAGE)
        return results

    def check_code(self, message):
        code = message['message']['text'].replace(CODE_COMMAND, '').rstrip().lstrip()
        results = NO_CODE_FOUND_MESSAGE
        if len(code):
            result = self.game_worker.game_driver.try_code(code)
            if result:
                results = u'\r\n{code}: +'.format(code=code)
            else:
                results = u'\r\n{code}: {wrong}'.format(code=code,
                                                        wrong=WRONG_CODE_MESSAGE)
        return results

    @staticmethod
    def get_command(message):
        return message.split()[0]

    def _do_stop(self, message):
        self.telegram_driver.answer_message(
            message,
            BYE_MESSAGES)
        self.stopped = True

    def stop_command(self, message):
        from_id = message['message']['from']['id']
        chat_id = message['message']['chat']['id']
        if from_id == DRAGA_ID:
            if chat_id < 0:
                if chat_id == self.chat_id:
                    self._do_stop(message)
                else:
                    self.telegram_driver.answer_message(
                        message,
                        NOT_FOR_GROUP_CHAT_MESSAGES)
            else:
                self._do_stop(message)
        else:
            self.telegram_driver.answer_message(
                message,
                ACCESS_VIOLATION_MESSAGES)

    def _do_pause(self, message):
        if not self.paused:
            self.pause_messages = 0
            self.telegram_driver.answer_message(
                message,
                START_PAUSE_MESSAGES)
            self.paused = True
        else:
            self.pause_messages += 1
            pause_message = ALREADY_PAUSED_MESSAGES[self.pause_messages - 1] \
                if len(ALREADY_PAUSED_MESSAGES) > self.pause_messages \
                else ALREADY_PAUSED_MESSAGES[-1]
            self.telegram_driver.answer_message(message, pause_message)

    def pause_command(self, message):
        from_id = message['message']['from']['id']
        chat_id = message['message']['chat']['id']
        if from_id == DRAGA_ID:
            if chat_id < 0:
                if chat_id == self.chat_id:
                    self._do_pause(message)
                else:
                    self.telegram_driver.answer_message(
                        message,
                        NOT_FOR_GROUP_CHAT_MESSAGES)
            else:
                self._do_pause(message)
        else:
            self.telegram_driver.answer_message(
                message,
                ACCESS_VIOLATION_MESSAGES)

    def _do_resume(self, message):
        if self.paused:
            self.resume_messages = 0
            self.telegram_driver.answer_message(
                message,
                END_PAUSE_MESSAGES)
            self.paused = False
        else:
            self.resume_messages += 1
            resume_message = RESUME_MESSAGES[self.resume_messages - 1] \
                if len(RESUME_MESSAGES) > self.resume_messages \
                else RESUME_MESSAGES[-1]
            self.telegram_driver.answer_message(message, resume_message)

    def resume_command(self, message):
        from_id = message['message']['from']['id']
        chat_id = message['message']['chat']['id']
        if from_id == DRAGA_ID:
            if chat_id < 0:
                if chat_id == self.chat_id:
                    self._do_resume(message)
                else:
                    self.telegram_driver.answer_message(
                        message,
                        NOT_FOR_GROUP_CHAT_MESSAGES)
            else:
                self._do_resume(message)
        else:
            self.telegram_driver.answer_message(
                message,
                ACCESS_VIOLATION_MESSAGES)

    def _do_codes(self, message):
        if not self.paused:
            result = self.check_codes(message)
            self.telegram_driver.answer_message(message, result)
        else:
            self.pause_messages += 1
            pause_message = PAUSED_MESSAGES[self.pause_messages - 1] \
                if len(PAUSED_MESSAGES) > self.pause_messages \
                else PAUSED_MESSAGES[-1]
            self.telegram_driver.answer_message(message, pause_message)

    def codes_command(self, message):
        from_id = message['message']['from']['id']
        chat_id = message['message']['chat']['id']
        if from_id == DRAGA_ID:
            if chat_id < 0:
                if self.chat_id == chat_id:
                    self._do_codes(message)
                else:
                    self.telegram_driver.answer_message(
                        message,
                        NO_GROUP_CHAT_MESSAGES)
            else:
                self._do_codes(message)
        else:
            self.telegram_driver.answer_message(
                message,
                ACCESS_VIOLATION_MESSAGES)

    def _do_code(self, message):
        if not self.paused:
            result = self.check_code(message)
            self.telegram_driver.answer_message(message, result)
        else:
            self.pause_messages += 1
            pause_message = PAUSED_MESSAGES[self.pause_messages - 1] \
                if len(PAUSED_MESSAGES) > self.pause_messages \
                else PAUSED_MESSAGES[-1]
            self.telegram_driver.answer_message(message, pause_message)

    def code_command(self, message):
        from_id = message['message']['from']['id']
        chat_id = message['message']['chat']['id']
        if from_id == DRAGA_ID:
            if chat_id < 0:
                if self.chat_id == chat_id:
                    self._do_code(message)
                else:
                    self.telegram_driver.answer_message(
                        message,
                        NO_GROUP_CHAT_MESSAGES)
            else:
                self._do_code(message)
        else:
            self.telegram_driver.answer_message(
                message,
                ACCESS_VIOLATION_MESSAGES)

    def _do_approve(self, message):
        chat_id = message['message']['chat']['id']
        self.telegram_driver.answer_message(
            message,
            AFFIRMATIVE_MESSAGES)
        self.chat_id = chat_id
        self.paused = False
        self.telegram_driver.send_message(
            self.chat_id,
            LETS_GO_MESSAGES)

    def approve_command(self, message):
        from_id = message['message']['from']['id']
        chat_id = message['message']['chat']['id']
        if from_id == DRAGA_ID:
            if chat_id < 0:
                self._do_approve(message)
            else:
                self.telegram_driver.answer_message(
                    message,
                    NOT_GROUP_CHAT_MESSAGES)
        else:
            self.telegram_driver.answer_message(
                message,
                ACCESS_VIOLATION_MESSAGES)

    def _do_disapprove(self, message):
        chat_id = message['message']['chat']['id']
        self.telegram_driver.answer_message(
            message,
            AFFIRMATIVE_MESSAGES)
        self.chat_id = None
        self.paused = False
        self.telegram_driver.send_message(
            chat_id,
            DISAPPROVE_MESSAGES)

    def disapprove_command(self, message):
        from_id = message['message']['from']['id']
        chat_id = message['message']['chat']['id']
        if from_id == DRAGA_ID:
            if chat_id < 0:
                if chat_id == self.chat_id:
                    self._do_disapprove(message)
                else:
                    self.telegram_driver.answer_message(
                        message,
                        NO_GROUP_CHAT_MESSAGES)
            else:
                self.telegram_driver.answer_message(
                    message,
                    NOT_GROUP_CHAT_MESSAGES)
        else:
            self.telegram_driver.answer_message(
                message,
                ACCESS_VIOLATION_MESSAGES)

    def _do_status(self, message):
        status_message = STATUS_MESSAGE.format(
            paused=PAUSED_STATUS_MESSAGES[self.paused],
            chat_id=self.chat_id,
            game_connection=GAME_CONNECTION_MESSAGES[self.game_worker.game_driver.is_logged()])
        self.telegram_driver.answer_message(message,
                                            status_message)

    def status_command(self, message):
        from_id = message['message']['from']['id']
        chat_id = message['message']['chat']['id']
        if from_id == DRAGA_ID:
            if chat_id < 0:
                if self.chat_id == chat_id:
                    self._do_status(message)
                else:
                    self.telegram_driver.answer_message(
                        message,
                        NO_GROUP_CHAT_MESSAGES)
            else:
                self._do_status(message)
        else:
            self.telegram_driver.answer_message(
                message,
                ACCESS_VIOLATION_MESSAGES)

    def _do_info(self, message):
        info_message = INFO_MESSAGE.format(
            login=self.game_worker.game_driver.login,
            password=self.game_worker.game_driver.password,
            host=self.game_worker.game_driver.host,
            game_id=self.game_worker.game_driver.game_id)
        self.telegram_driver.answer_message(message,
                                            info_message)

    def info_command(self, message):
        from_id = message['message']['from']['id']
        chat_id = message['message']['chat']['id']
        if from_id == DRAGA_ID:
            if chat_id < 0:
                self.telegram_driver.answer_message(
                    message,
                    NOT_FOR_GROUP_CHAT_MESSAGES)
            else:
                self._do_info(message)
        else:
            self.telegram_driver.answer_message(
                message,
                ACCESS_VIOLATION_MESSAGES)

    def _do_change_settings(self):
        self.setup_bot()

    def change_settings_command(self, message):
        from_id = message['message']['from']['id']
        chat_id = message['message']['chat']['id']
        if from_id == DRAGA_ID:
            if chat_id < 0:
                self.telegram_driver.answer_message(
                    message,
                    NOT_FOR_GROUP_CHAT_MESSAGES)
            else:
                self._do_change_settings()
        else:
            self.telegram_driver.answer_message(
                message,
                ACCESS_VIOLATION_MESSAGES)

    def _do_unknown(self, message):
        self.telegram_driver.answer_message(
            message,
            UNKNOWN_MESSAGES)

    def unknown_command(self, message):
        if config.answer_unknown:
            self.telegram_driver.answer_message(message,
                                                UNKNOWN_MESSAGES)

    def process_messages(self):
        for message in self.check_new_messages():
            if self.initial_message is None:
                self.initial_message = message
            message_text = message['message']['text']
            command = self.get_command(message_text)

            if command == CODE_COMMAND:
                self.code_command(message)
            elif command == CODES_COMMAND:
                self.codes_command(message)
            elif command == STOP_COMMAND:
                self.stop_command(message)
            elif command == RESUME_COMMAND:
                self.resume_command(message)
            elif command == PAUSE_COMMAND:
                self.pause_command(message)
            elif command == APPROVE_COMMAND:
                self.approve_command(message)
            elif command == DISAPPROVE_COMMAND:
                self.disapprove_command(message)
            elif command == STATUS_COMMAND:
                self.status_command(message)
            elif command == INFO_COMMAND:
                self.info_command(message)
            elif command == CHANGE_SETTINGS_COMMAND:
                self.change_settings_command(message)
            else:
                self.unknown_command(message)

    def process_game_tasks(self):
        if not self.paused and self.chat_id is not None:
            updates = self.game_worker.check_updates()
            if updates is None:
                self.telegram_driver.send_message(
                    DRAGA_ID,
                    CONNECTION_PROBLEM_MESSAGES)
            elif len(updates):
                for update in updates:
                    self.telegram_driver.send_message(self.chat_id,
                                                      update,
                                                      parse_mode="HTML")