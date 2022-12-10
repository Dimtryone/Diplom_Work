import os
import vk_api
import random
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from models import create_tables, UserInfo, ValueSearch, BlackList
import psycopg2
from datetime import datetime


class BaseBot:
    """
    Базовый класс бота VK, отправка сообщений, сохранение о пользователе информации в БД авторизация
    """

    vk_session = None
    # метка доступа к API
    vk_api_access = None
    # сессия приложения
    app_session = None
    authorized = False

    def __init__(self):
        """
        Инициализация бота при помощи получения доступа к API ВКонтакте
        """
        self.vk_session = self.get_auth_group()
        self.app_session = self.get_auth_app()
        if self.vk_session is not None: #and self.app_session is not None:
            self.authorized = True


    def get_tokens(self):
        """
        Извлечение паролей и токенов
        :return: словарь паролей и токенов
        """
        path = os.getenv('HOME') + '//Documents//Diplom_netology//tokens.txt'
        token_dict = {}
        with open(path, 'r', encoding='utf-8') as file:
            parametrs = list(map(str.strip, file.readlines()))
            token_dict['TOKEN_GROUP'] = parametrs[1]
            token_dict['ID_APP']  = parametrs[4]
            token_dict['username'] = parametrs[8]
            token_dict['password_BD'] = parametrs[9]
            token_dict['name_BD'] = parametrs[10]
            token_dict['name_host'] = parametrs[11]
            token_dict['num_host'] = parametrs[12]
        return token_dict

    def get_auth_group(self, tokens=self.get_tokens()):
        """
        Авторизация группы использует переменную TOKEN_GROUP, ее получаем из файла
        :return: возможность работать с API
        """
        token_dict = tokens
        TOKEN_GROUP = token_dict['TOKEN_GROUP']
        try:
            self.vk_session = vk_api.VkApi(token=TOKEN_GROUP)
            return self.vk_session
        except Exception as error:
            print('Unable to connect to the API_VK')
            return None

    def get_auth_app(self):
        """
        Авторизация приложения для поиска людей. Использует переменную ID_APP, ее получаем из файла
        :return: сессия с возможностью работать с API от приложения
        """
        token_dict = self.get_tokens()
        ID_APP = token_dict['ID_APP']
        SCOPE='PHOTO'
        self.app_session = vk_api.VkApi(app_id=ID_APP, scope=SCOPE)
        try:
            self.app_session.get_api()  #code_auth(ID_APP, redirect_url)
        except vk_api.AuthError as error_msg:
            print('error AuthError')


            self.app_session.auth()
            return self.app_session.get_api()  # !!!!!!&&&&
        except Exception as error:
            print('Unable to connect to the API_VK (app)')
            return None

    def send_message(self, user_id, message, keyboard=None):
        """
         Отправка сообщения от лица авторизованного пользователя
         :param user_id: уникальный идентификатор получателя сообщения
         :param message: текст отправляемого сообщения
         :param  keyboard: клавиатура с кнопкой выбора, например, вначале общения это кнопка START и FINISH
         """

        if not self.authorized:
            print("Please check your Token")
            return
        if keyboard != None:
            param= {"user_id": user_id, "message": message, "random_id": random.randint(1, 10000),
                        "keyboard": keyboard}
        else:
            param = {"user_id": user_id, "message": message, "random_id": random.randint(1, 10000)}

        try:
            #self.vk_api_access.method("messages.send", param)
            self.vk_session.method("messages.send", param)
            print(f"Сообщение отправлено для ID {user_id} с текстом: {message}")
        except Exception as error:
            print("Failed to send massage")

    def get_info_user(self, user_id):
        """
        Для получения  пользователя
        """
        fields = ['education', 'interests', 'movies', 'music', 'relation', 'sex', 'city']
        param = {'user_ids': user_id, 'fields': fields, 'name_case': 'nom'}
        with vk_api.VkRequestsPool(self.vk_session) as pool:
            request = pool.method('users.get', param)
        if request.error == True:
            return False
        else:
            return request

    def save_database(self, request):
        """
        Сохранение данных о пользователе в таблицу UserInfo, занесене user_id  в ValueSearch
        уникальность по user_id
        :param request:
        :return: False/True
        """
        token_dict = self.get_tokens()
        username = token_dict["username"]
        password_BD = token_dict["password_BD"]
        name_BD = token_dict["name_BD"]
        name_host = token_dict["name_host"]
        num_host = token_dict["num_host"]

        DSN = f"postgresql://{username}:{password_BD}@{name_host}:{num_host}/{name_BD}"
        engine = sqlalchemy.create_engine(DSN, echo=True, future=True)
        #create_tables(engine)  - деактивирован код по очистке и созданию таблиц в БД
        Session = sessionmaker(bind=engine)
        session = Session()

        sex_id = {1: "женский", 2: "мужской", 3: "пол не указан"}
        relation_id = {1: 'не женат/не замужем', 2: 'есть друг/есть подруга', 3: 'помолвлен/помолвлена',
                    4: 'женат/замужем', 5: 'всё сложно', 6: 'в активном поиске', 7: 'влюблён/влюблена',
                    8: 'в гражданском браке', 0: 'не указано'}

        first_name = request[0].get('first_name')
        last_name = request[0].get('last_name')
        user_id = request[0].get('id')
        sex = request[0].get('sex')
        sex = sex_id.get(sex)
        interests = request[0].get('interests')
        university_name = request[0].get('university_name')
        faculty_name = request[0].get('faculty_name')
        movies = request[0].get('movies')
        music = request[0].get('music')
        relation = request[0].get('relation')
        relation = relation_id.get(relation)

        #city = sq.Column(sq.String(length=200))
        user = UserInfo(first_name=first_name, last_name=last_name, user_id=user_id, sex=sex, movies=movies, music=music, relation=relation, interests=interests, university_name=university_name, faculty_name=faculty_name)
        session.add_all([user])
        value = ValueSearch(user_id=user_id)
        session.add_all([value])
        try:
            session.commit()
            return True
        except Exception as error:
            return False
        finally:
            session.close()


class LongPollBot(BaseBot):


    COMMANDS = ["START", "FINISH", "HELP"]
    KEYBOARDS = ["МУЖЧИНА", "ЖЕНЩИНА", "НЕ ЖЕНАТ/НЕ ЗАМУЖЕМ", "В АКТИВНОМ ПОИСКЕ", "ВСЁ СЛОЖНО", "НЕ УКАЗАНО"]

    def __init__(self):
        super(LongPollBot, self).__init__()
        self.longpoll = VkLongPoll(self.vk_session)

    def get_keyboard(self):
        pass

    def do_listen(self):
        """
         Прослушивание чата и определение пожеланий пользователя
         """

        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                text = event.text.upper()
                user_id = event.user_id
                session = self.get_session_DB()
                q = session.query(UserInfo.first_name).filter(UserInfo.user_id == user_id).all()  #user_id уникальным, поэтому в момент поиска выйдет одно значение.
                name_us = q
                session.close()
                ### Добавить Фичу про диалог, если пользователь будет отправлять не валидные запросы
                # if text not in self.COMMANDS and text not in self.KEYBOARDS
                if text == "START":
                    info = self.get_info_user(user_id)
                    if info == False:
                        self.send_message(user_id, "Please try again")
                    else:
                        self.tell_start(user_id, info)
                        request_res = info.result
                        self.save_database(request_res)
                if text == "FINISH":
                    message = "Буду снова рад видеть тебя"
                    self.send_message(user_id, message)
                if text == "HELP":
                    self.tell_help(user_id)
                if name_us == []:
                    self.tell_hello(user_id)
                else:
                    name_us = name_us[0][0]
                if name_us != [] and (text == "МУЖЧИНА" or text == "ЖЕНЩИНА"):
                    self.set_sex_for_search(user_id, text)
                    self.tell_choice_status(user_id)
                if name_us != [] and text in ["НЕ ЖЕНАТ/НЕ ЗАМУЖЕМ", "В АКТИВНОМ ПОИСКЕ", "ВСЁ СЛОЖНО", "НЕ УКАЗАНО"]:
                    self.set_status_for_search(user_id, text)
                    message = f'{name_us} укажи название города. Первым словом должно быть слово "город". Например, город Москва.'
                    self.send_message(user_id, message)
                if name_us != [] and "ГОРОД" in text.split():
                    text = text.split()
                    name_city = ' '.join(text[1:])
                    city_id = self.find_city(name_city, user_id)
                    if city_id == False:
                        message = f'{name_us} Данный город не найден в базе VK. повторите команду. ' \
                                  f'Первым должно быть написано слово "город". Например, город Москва.'
                        self.send_message(user_id, message)
                    if type(city_id) == int:
                        self.set_city_search(city_id, user_id)



                    keyboard = VkKeyboard()
                    keyboard.add_button(label="CITY", color=VkKeyboardColor.POSITIVE)
                    keyboard.add_button(label="STATUS", color=VkKeyboardColor.POSITIVE)


    def get_session_DB(self):
        token_dict = self.get_tokens()
        username = token_dict["username"]
        password_BD = token_dict["password_BD"]
        name_BD = token_dict["name_BD"]
        name_host = token_dict["name_host"]
        num_host = token_dict["num_host"]
        DSN = f"postgresql://{username}:{password_BD}@{name_host}:{num_host}/{name_BD}"
        engine = sqlalchemy.create_engine(DSN, echo=True, future=True)
        Session = sessionmaker(bind=engine)
        session = Session()
        return session


    def set_sex_for_search(self, user_id, text):
        """Сохранение в БД параметра поиска пол второй половины"""

        if text == "МУЖЧИНА":
            sex = 2
        if text == "ЖЕНЩИНА":
            sex = 1
        session = self.get_session_DB()
        session.query(ValueSearch).filter(ValueSearch.user_id == user_id).update({"sex": sex}, synchronize_session='fetch')
        try:
            session.commit()
        except Exception as error:
            message = "Не получилось добавить данные для поиска. Возможно сначала надо выбрать команду START"
            self.send_message(user_id, message)
        finally:
            print('Блок кода выполняется всегда!')
            session.close()


    def set_status_for_search(self, user_id, text):
        """Сохранение в БД параметра поиска статус"""

        status_id = {"НЕ ЖЕНАТ/НЕ ЗАМУЖЕМ": 1, "ВСЁ СЛОЖНО": 5, "В АКТИВНОМ ПОИСКЕ": 6, "НЕ УКАЗАНО": 0}
        status = status_id[text]
        session = self.get_session_DB()
        session.query(ValueSearch).filter(ValueSearch.user_id == user_id).update({"status": status},
                                                                                 synchronize_session='fetch')
        try:
            session.commit()
        except Exception as error:
            message = "Не получилось добавить данные для поиска. Возможно сначала надо выбрать команду START"
            self.send_message(user_id, message)
        finally:
            session.close()

    def set_city_search(self, city_id, user_id):
        """ Сохранение в БД параметра поиска город (идентификатор VK)"""
        session = self.get_session_DB()
        session.query(ValueSearch).filter(ValueSearch.user_id == user_id).update({"city_id": city_id},
                                                                                 synchronize_session='fetch')
        try:
            session.commit()
        except Exception as error:
            message = "Не получилось добавить данные для поиска. Возможно сначала надо выбрать команду START"
            self.send_message(user_id, message)
        finally:
            session.close()


    def tell_choice_status(self, user_id):
        """Формирование параметра запроса пользователя (статус второй половины)"""

        keyboard = VkKeyboard()
        keyboard.add_button(label="не женат/не замужем", color=VkKeyboardColor.POSITIVE)
        keyboard.add_button(label="в активном поиске", color=VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button(label="всё сложно", color=VkKeyboardColor.POSITIVE)
        keyboard.add_button(label="не указано", color=VkKeyboardColor.POSITIVE)
        keyboard = keyboard.get_keyboard()
        self.send_message(user_id, "Выбери доступный статус для поиска", keyboard=keyboard)


    def find_city(self, name_city, user_id):
        """определяет город из БД VK"""
        q = name_city
        param = {'q': q}
        with vk_api.VkRequestsPool(self.app_session) as pool:  #  self.app_session
            request = pool.method('database.getCities', param)
        if request.error == True:
            return False
        else:
            city = request.result
            if city[0]['count'] == 1:
                return city[0]['items'][0]['id']
            else:
                message = "Поиск нашел несколько городов с похожим названием. Внимательно изучите список ниже и пришлите" \
                          " сообщение в формате 'ID цифры', Например, 'id 113056'. или пришлите сообщение ОТКАЗАТЬСЯ ОТ ГОРОДА."
                self.send_message(user_id, message)
                for item in city[0]['items']:
                    country = item.get('region')
                    region = item.get('region')
                    area = item.get('area')
                    title = item.get('title')
                    id = item.get('id')
                    message = f'{title} {id} {country} {region} {area}'
                    self.send_message(user_id, message)
                return True






    # def get_sex(self):
    #     message = "Укажи 1 если ищешь женщину своей мечты, укажи 2 если хочешь быть, как за каменной стеной. И скорее жми на следющую кнопку"
    #     self.send_message(user_id, message)
    #     self.do_data_for_search(text)
    #     keyboard.add_button(label="AGE", color=VkKeyboardColor.POSITIVE)
    #     self.send_message(user_id, "Задай возрастной интервал, например в формате  18-22", keyboard=keyboard)
    #
    # def get_age(self):
    #     self.do_data_for_search(text)
    #     keyboard.add_button(label="AGE", color=VkKeyboardColor.POSITIVE)
    #     self.send_message(user_id, "Задай возрастной интервал, например в формате  18-22", keyboard=keyboard)


    def tell_hello(self, user_id):
        """
        Сказать приветственное слово
        :param user_id:
        :return:
        """
        keyboard = VkKeyboard()
        keyboard.add_button(label="START", color=VkKeyboardColor.PRIMARY)
        keyboard.add_button(label="HELP", color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button(label="FINISH", color=VkKeyboardColor.NEGATIVE)
        keyboard = keyboard.get_keyboard()
        start_message = "Hello, I'm Chat Bot"
        self.send_message(user_id, start_message)
        self.send_message(user_id, "Ты можешь выбрать команду Start или Finish. Список всех доступных команд доступен по справке Help", keyboard=keyboard)

    def tell_start(self, user_id, request):
        """
        Начать работу с пользователем
        :param user_id:
        :param request:
        :return:
        """
        name = request.result[0]['first_name']
        message = f'{name} мой учебный чат бот поможе найти тебе вторую половину. Заполни парметры, после ты сможешь выполнить поиск по ВК.'
        self.send_message(user_id, message)
        message = f'Для это, {name}, тебе придется задать параметры для поиска.'
        self.send_message(user_id, message)
        keyboard = VkKeyboard()
        keyboard.add_button(label="Мужчина", color=VkKeyboardColor.POSITIVE)
        keyboard.add_button(label="Женщина", color=VkKeyboardColor.POSITIVE)
        keyboard = keyboard.get_keyboard()
        self.send_message(user_id, "Выбери, кого ищем?", keyboard=keyboard)

    def tell_help(self):
        message = "Это учебный чат бот, целью которого является поиск второй половины по заданным параметрам. " \
                  "\n\tВы можете добавлять человека в черный список. \n\tЧат бот гарантирует, что люди, которые вас не " \
                  "заинтересовали, не будут повторяться. \n\tБот старается искать человека и по общим интересам, например" \
                  "музыка, хобби и прочее.\n\n\tВ любой момент вы можете ввести команду FINISH и остановить Бот."
        self.send_message(user_id, message)

    #database.getCitiesById


    #        friends = pool.method('friends.get')
     #       status = pool.method('status.get')
  #USER_ONLINE

bot = LongPollBot()
bot.do_listen()

