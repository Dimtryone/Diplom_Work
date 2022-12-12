import os
import webbrowser
from urllib.parse import urlencode
from urllib.parse import urlparse
import vk_api
import random
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from models import create_tables, UserInfo, ValueSearch, BlackList



class BaseBot:
    """
    Базовый класс бота VK, отправка сообщений, сохранение о пользователе информации в БД авторизация
    """

    vk_session = None
    app_session = None
    authorized = False

    def __init__(self):
        """
        Инициализация бота при помощи получения доступа к API ВКонтакте
        """
        self.vk_session = self.get_auth_group()
        self.app_session = self.get_auth_app()
        self.token_app = ''
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
            token_dict['ID_US'] = parametrs[14]
            token_dict['PASSWORD_US'] = parametrs[15]
        return token_dict


    def get_auth_group(self):
        """
        Авторизация группы использует переменную TOKEN_GROUP, ее получаем из файла
        :return: возможность работать с API
        """
        token_dict = self.get_tokens()
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

        self.token_app = self.get_token_app()
        try:
            self.app_session = vk_api.VkApi(token=self.token_app)
            return self.app_session
        except Exception or vk_api.AuthError as error_msg:
            print('error AuthError')


    def get_token_app(self):
        """для получения токена, из url копируется вручную, далее программа сама декомпозирует строку и сохраняет токен"""

        URL_REDIRECT = 'https://oauth.vk.com/blank.html'
        URL_AUTH = 'https://oauth.vk.com/authorize/'
        token_dict = self.get_tokens()
        client_id = token_dict['ID_APP']
        FRIENDS = 'friends'
        PHOTOS = 'photos'
        AUDIO = 'audio'
        WALL = 'wall'
        STORIES = 'stories'
        SCOPE_LIST: list[str] = [FRIENDS, PHOTOS, AUDIO, WALL, STORIES]
        SCOPE: str = ','.join(SCOPE_LIST)
        param = {
            "client_id": client_id,
            "redirect_uri": URL_REDIRECT,
            "display": 'page',
            "scope": SCOPE,
            "response_type": "token"
        }
        print('')
        webbrowser.open('?'.join((URL_AUTH, urlencode(param))), new=1)
        url_back = input('вставьте скопированную строку из открывшейся страницы:')
        strange = urlparse(url_back)
        str_with_token = strange[5]
        list_with_token = str_with_token.split('&')
        token = list_with_token[0]
        token = token.replace('access_token=', '')
        self.token_app = token
        print('токен сохранен')
        return self.token_app


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
            param = {"user_id": user_id, "message": message, "random_id": random.randint(1, 10000),
                        "keyboard": keyboard}
        else:
            param = {"user_id": user_id, "message": message, "random_id": random.randint(1, 10000)}

        try:
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
        create_tables(engine)  #- деактивировать код по очистке и созданию таблиц в БД
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
        cities = request[0].get('city')
        city = cities.get('title')
        user = UserInfo(first_name=first_name, last_name=last_name, user_id=user_id, sex=sex, movies=movies, music=music,
                        relation=relation, interests=interests, university_name=university_name, faculty_name=faculty_name,
                        city=city)
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
    """
    Класс чат бота, который постояннно слушает и определяет поведение пользователя и соответственно отвечает ему.
    """

    COMMANDS = ["START", "FINISH", "HELP", "В ЧЕРНЫЙ СПИСОК", "БОЛЬШЕ ФОТО", "ДАЛЬШЕ"]
    KEYBOARDS = ["МУЖЧИНА", "ЖЕНЩИНА", "НЕ ЖЕНАТ/НЕ ЗАМУЖЕМ", "В АКТИВНОМ ПОИСКЕ", "ВСЁ СЛОЖНО", "НЕ УКАЗАНО"]
    COUNTRIES = ['РОССИЯ', 'БЕЛОРУССИЯ', 'УКРАИНА', 'РОС', 'РОСИЯ', 'БЕЛ', 'БЕЛОРУСИЯ', 'УКР']
    AGIES = ["ОТ 18 ДО 21", "ОТ 22 ДО 25", "ОТ 30 ДО 35", "ОТ 36 ДО 40", "ОТ 41 ДО 50", "ОТ 50 ДО 65"]


    def __init__(self):
        super(LongPollBot, self).__init__()
        self.longpoll = VkLongPoll(self.vk_session)
        self.PEOPLE_FOUND = {}
        self.timestamp_id = 0
        self.timestamp_person = []


    def do_listen(self):
        """
         Прослушивание чата и определение пожеланий пользователя
         """

        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                text = event.text.upper()
                user_id = event.user_id
                city_id = self.get_city_id_from_DB(user_id)
                name_us = self.get_name_user_from_DB(user_id)
                if text == "START":
                    info = self.get_info_user(user_id)
                    if info == False:
                        self.send_message(user_id, "Пожалуйста, попробуйте снова")
                    else:
                        self.tell_start(user_id, info)
                        request_res = info.result
                        self.save_database(request_res)
                if text == "FINISH":
                    self.tell_goodbye(user_id)
                if text == "HELP":
                    self.tell_help(user_id)
                if name_us == [] and text not in self.COMMANDS:
                    self.tell_hello(user_id)
                if name_us != [] and (text == "МУЖЧИНА" or text == "ЖЕНЩИНА"):
                    self.set_sex_for_search(user_id, text)
                    self.tell_choice_status(user_id)
                if name_us != [] and text in ["НЕ ЖЕНАТ/НЕ ЗАМУЖЕМ", "В АКТИВНОМ ПОИСКЕ", "ВСЁ СЛОЖНО", "НЕ УКАЗАНО"]:
                    self.set_status_for_search(user_id, text)
                    self.tell_find_city(user_id, name_us)
                if name_us != [] and text.split()[0] in self.COUNTRIES:
                    city_id = self.find_city(text, user_id)
                    if city_id == False:
                        self.not_found_city(user_id, name_us)
                    if type(city_id) == int:
                        self.set_city_for_search(city_id, user_id, name_us)
                        self.get_age(user_id)
                if city_id == None and text.isdigit():
                    self.set_city_for_search(text, user_id, name_us)
                    self.get_age(user_id)
                if type(city_id) == int and text.isdigit():
                    self.change_city_for_search(user_id, name_us, text)
                    self.get_age(user_id)
                if name_us != [] and text in self.AGIES:
                    flag = self.set_age_for_search(user_id, text)
                    if flag == True:
                        self.find_people(user_id)
                        self.show_people(user_id)
                    else:
                        self.tell_error(user_id)
                if name_us != [] and text == "БОЛЬШЕ ФОТО" and self.timestamp_person != []:
                    self.show_more_photos(user_id)
                if name_us != [] and text == "ДАЛЬШЕ" and len(self.PEOPLE_FOUND) > 0:
                    self.show_people(user_id)
                if name_us != [] and text == "В ЧЕРНЫЙ СПИСОК" and self.timestamp_id != '':
                    self.set_black_list(user_id)
                if name_us != [] and text not in self.COMMANDS and text not in self.KEYBOARDS and text not in self.COUNTRIES and text not in self.AGIES:
                    self.tell_something(user_id, name_us)


    def get_name_user_from_DB(self, user_id):
        """Функция проверяет наличие пользователя в нашей БД. User_id уникальный, поэтому поиска выдаст одно значение."""

        session = self.get_session_DB()
        try:
            q = session.query(UserInfo.first_name).filter(UserInfo.user_id == user_id).all()
        except Exception as error:
            print('не получилось узнать user name. Проблема с БД.')
        finally:
            session.close()
        name_us = q
        if name_us != []:
            name_us = name_us[0][0]
        return name_us


    def get_city_id_from_DB(self, user_id):
        """Функция проверяет наличие city_id в нашей БД. User_id уникальный, поэтому поиска выдаст одно значение."""

        session = self.get_session_DB()
        try:
            q = session.query(ValueSearch.city_id).filter(ValueSearch.user_id == user_id).all()
        except Exception as error:
            print('не получилось узнать city_id. Проблема с БД.')
        finally:
            session.close()
        city_id = q
        if city_id != []:
            city_id = q[0][0]
        return city_id


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
            message = "Не получилось добавить пол для поиска. Возможно сначала надо выбрать команду START"
            self.send_message(user_id, message)
        finally:
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
            message = "Не получилось добавить 'статус' для поиска. Возможно сначала надо выбрать команду START"
            self.send_message(user_id, message)
        finally:
            session.close()


    def set_city_for_search(self, city_id, user_id, name_us):
        """ Сохранение в БД параметра поиска город (идентификатор VK)"""

        city_id = int(city_id)
        session = self.get_session_DB()
        session.query(ValueSearch).filter(ValueSearch.user_id == user_id).update({"city_id": city_id},
                                                                                 synchronize_session='fetch')
        try:
            session.commit()
            message = f'{name_us} город {city_id} для поиска сохранен.'
            self.send_message(user_id, message)
        except Exception as error:
            message = "Не получилось добавить Город для поиска. Возможно сначала надо выбрать команду START"
            self.send_message(user_id, message)
        finally:
            session.close()


    def change_city_for_search(self, user_id, name_us, text):
        """Изменяет город, когда пользователь решит изменить кретерии поиска"""

        text = int(text)
        self.set_city_for_search(text, user_id)
        message = f'{name_us} город для поиска изменен.'
        self.send_message(user_id, message)


    def set_age_for_search(self, user_id, text):
        """Сохранение в БД параметра поиска возраст. API VK: age_from, age_to"""

        text = text.split()
        age_from = int(text[1])
        age_to = int(text[3])
        session = self.get_session_DB()
        session.query(ValueSearch).filter(ValueSearch.user_id == user_id).update({"age_from": age_from, "age_to": age_to},
                                                                                 synchronize_session='fetch')
        try:
            session.commit()
            return True
        except Exception as error:
            message = "Не получилось добавить возраст для поиска. Возможно сначала надо выбрать команду START"
            self.send_message(user_id, message)
            return False
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


    def find_city(self, text, user_id):
        """определяет идентификатор города из БД VK"""

        text = text.split()
        q = ' '.join(text[1:])
        countries = {'РОССИЯ': 1, 'БЕЛОРУССИЯ': 3, 'УКРАИНА': 2, 'РОС': 1, 'БЕЛ': 3, 'УКР': 2, 'РОСИЯ': 1, 'БЕЛОРУСИЯ': 3}
        country_id = countries[text[0]]
        param = {'country_id': country_id, 'q': q}
        with vk_api.VkRequestsPool(self.app_session.get_api()) as pool:  #  self.app_session
            request = pool.method('database.getCities', param)
        if request.error == True:
            return False
        else:
            city = request.result
            count = city['count']
            if count == 1:
                return city['items'][0]['id']
            else:
                message = f'Результат поиска выдал {count} городов с похожим названием. Внимательно изучите список ниже и пришлите' \
                          ' сообщение в формате "ID цифры", Например, "id 113056". или пришлите сообщение ОТКАЗАТЬСЯ ОТ ГОРОДА.'
                self.send_message(user_id, message)
                for item in city['items']:
                    country = item.get('country')
                    region = item.get('region')
                    area = item.get('area')
                    title = item.get('title')
                    id = item.get('id')
                    if country != None:
                        message = f'{title} id города: {id}, регион {country} '
                        self.send_message(user_id, message)
                        continue
                    if region != None or area != None:
                        message = f'id города {title}: {id}, регион: {region}, область {area}'
                        self.send_message(user_id, message)
                    else:
                        continue
                return True


    def find_people(self, user_id):
        """Функция ищет людей по заданным параметрам."""

        session = self.get_session_DB()
        try:
            query = session.query(ValueSearch.sex, ValueSearch.age_from, ValueSearch.age_to, ValueSearch.status,
                                  ValueSearch.city_id).filter(UserInfo.user_id == user_id)
        except Exception as error:
            print('не получилось узнать user name. Проблема с БД.')
        finally:
            session.close()
        value = query[0]
        sex = str(value[0])
        age_from = value[1]
        age_to = value[2]
        status = value[3]
        city_id = value[4]
        fields = {'has_photo': 1, 'photo_400_orig': 'photo_400_orig', 'bdate': 'bdate'}

        param = {'city': city_id, 'sex': sex, 'age_from': age_from, 'age_to': age_to, 'status': status, 'offset': '15',
                 'fields': fields}
        with vk_api.VkRequestsPool(self.app_session.get_api()) as pool:  # self.app_session
            request = pool.method('users.search', param)
        if request.error == True:
            return False
        else:
            people = request.result
            self.PEOPLE_FOUND = {}
            for item in people['items']:
                if item.get('can_access_closed') == True:
                    first_name = item.get('first_name')
                    last_name = item.get('last_name')
                    photo_400_orig = item.get('photo_400_orig')
                    id = item.get('id')
                    url_person = 'https://vk.com/id' + str(id)
                    bdate = item.get('bdate')
                    self.PEOPLE_FOUND[id] = [first_name, last_name, photo_400_orig, bdate, url_person]
            flag = self.find_popular_photo()
            if flag == True:
                return True
            else:
                return False


    def find_popular_photo(self):
        """Функция находит популярные 3 фотографии пользователя"""

        for key, value in self.PEOPLE_FOUND.items():
            param = {'owner_id': key, 'album_id': 'profile', 'extended': '1', 'photo_sizes': '1'}
            with vk_api.VkRequestsPool(self.app_session.get_api()) as pool:
                request = pool.method('photos.get', param)
            if request.error == True:
                continue
            else:
                photos = request.result
                if photos['count'] > 2:
                    links_photos = {}
                    likes = []
                    for item in photos['items']:
                        like = item['likes']['count']
                        likes.append(like)
                        for size in item["sizes"]:
                            if size.get("type") == "x":
                                link_photo = size.get('url')
                                links_photos[like] = link_photo
                    likes.sort(reverse=True)
                    result_photos = []
                    index = 0
                    for i in range(3):
                        link = links_photos[likes[index]]
                        result_photos.append(link)
                        index += 1
                else:
                    result_photos = []
                    for size in item["sizes"]:
                        if size.get("type") == "x":
                            link_photo = size.get('url')
                            result_photos.append(link_photo)
            value.append(result_photos)
        return True


    def show_people(self, user_id):
        """Показывает пользователю из результата поиска людей. Во временную переменную присваивается id
         и список с данными о человеке. По этим данным можно получать больше фотографий или перемещать
          человека в черный список"""

        keyss = self.PEOPLE_FOUND.keys()
        keyss = list(keyss)
        self.timestamp_id = keyss[0]
        person = self.PEOPLE_FOUND.pop(self.timestamp_id)
        self.timestamp_person = person
        if self.check_person_in_black_list(user_id, self.timestamp_id):
            first_name = person[0]
            last_name = person[1]
            photo_400_orig = person[2]
            url_person = person[4]
            bdate = person[3]
            message = f'{first_name} {last_name} ссылка на профиль {url_person} дата рождения {bdate} \n фото: \n{photo_400_orig}'
            keyboard = VkKeyboard()
            keyboard.add_button(label="Дальше", color=VkKeyboardColor.PRIMARY)
            keyboard.add_button(label="Больше фото", color=VkKeyboardColor.POSITIVE)
            keyboard.add_line()
            keyboard.add_button(label="В черный список", color=VkKeyboardColor.NEGATIVE)
            keyboard = keyboard.get_keyboard()
            self.send_message(user_id, message, keyboard=keyboard)
            amount = len(self.PEOPLE_FOUND)
            if amount < 1:
                self.find_people(user_id)
        else:
            amount = len(self.PEOPLE_FOUND)
            if amount < 1:
                self.find_people(user_id)
            self.show_people(user_id)


    def show_more_photos(self, user_id):
        """Функция показывает по команде "Больше фото" пользователю больше фотографий"""

        person = self.timestamp_person
        photos = person[5]
        for photo in photos:
            message = {photo}
            self.send_message(user_id, message)


    def set_black_list(self, user_id):
        """Функция помещает id пользователя в таблицу с черным списком"""

        session = self.get_session_DB()
        value = BlackList(block_user_id=self.timestamp_id, users_id=session.query(UserInfo.user_id).filter(UserInfo.user_id == user_id))
        session.add_all([value])
        try:
            session.commit()
            return True
        except Exception as error:
            print('Не удалось добавить в черный список')
            return False
        finally:
            session.close()


    def check_person_in_black_list(self, user_id, black_user_id):
        """Функция проверяет есть ли id в черном списке"""

        session = self.get_session_DB()
        try:
            query = session.query(BlackList.block_user_id).filter(BlackList.users_id == user_id)
        except Exception as error:
            print('не получилось узнать user name. Проблема с БД.')
        finally:
            session.close()
        result = query.all()
        if result == []:
            return True
        else:
            for answer in result:
                if answer == black_user_id:
                    return False
                else:
                    return True


    def get_age(self, user_id):
        """Отображает кнопки выбора возраста"""

        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button(label="от 18 до 21", color=VkKeyboardColor.PRIMARY)
        keyboard.add_button(label="от 22 до 25", color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button(label="от 30 до 35", color=VkKeyboardColor.PRIMARY)
        keyboard.add_button(label="от 36 до 40", color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button(label="от 41 до 50", color=VkKeyboardColor.PRIMARY)
        keyboard.add_button(label="от 50 до 65", color=VkKeyboardColor.PRIMARY)
        keyboard = keyboard.get_keyboard()
        self.send_message(user_id, "Выбирай возраст и переходи к поиску", keyboard=keyboard)


    def tell_hello(self, user_id):
        """
        Сказать приветственное слово, когда пользователь впервые в чат боте
        :param user_id:
        :return:
        """
        keyboard = VkKeyboard()
        keyboard.add_button(label="START", color=VkKeyboardColor.PRIMARY)
        keyboard.add_button(label="HELP", color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button(label="FINISH", color=VkKeyboardColor.NEGATIVE)
        keyboard = keyboard.get_keyboard()
        start_message = "Привет я учебный Чат Бот. Создан, чтобы найти для тебя вторую половину твоей мечты! " \
                        "Скорее жми START"
        self.send_message(user_id, start_message)
        self.send_message(user_id, "Ты можешь выбрать команду Start или Finish. Список всех возможных команд "
                                   "доступен по справке Help", keyboard=keyboard)


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
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button(label="Мужчина", color=VkKeyboardColor.POSITIVE)
        keyboard.add_button(label="Женщина", color=VkKeyboardColor.POSITIVE)
        keyboard = keyboard.get_keyboard()
        self.send_message(user_id, "Выбери кого ищем?", keyboard=keyboard)


    def tell_help(self, user_id):
        """Отправляет сообщение при вводе команды HELP"""

        message = "Это учебный чат бот, целью которого является поиск второй половины по заданным параметрам. " \
                  "\n\tВы можете добавлять человека в черный список. \n\tЧат бот гарантирует, что люди, которые вас не " \
                  "заинтересовали, не будут повторяться. \n\tБот старается искать человека и по общим интересам, например" \
                  "музыка, хобби и прочее.\n\n\tВ любой момент вы можете ввести команду FINISH и остановить Бот.\n\n " \
                  "Доступные команды: START, FINISH  \n\n В любой момент вы можете изменить критерии поиска. Для этого" \
                  "нужно снова ввести команду START"
        self.send_message(user_id, message)


    def tell_goodbye(self, user_id):
        """Отправляет сообщение при вводе команды FINISH"""

        message = "Буду снова рад видеть тебя"
        self.send_message(user_id, message)


    def not_found_city(self, user_id, name_us):
        """Отправляет сообщение пользователю о неудачном поиске города"""

        message = f'{name_us} Данный город не найден в базе VK. повторите команду. ' \
                  f'Первым словом должна быть указана страна, а потом "город". Например, Россия Москва.'
        self.send_message(user_id, message)


    def tell_error(self, user_id):
        """Отправляет сообщение при вводе команды FINISH"""

        message = "Возникла ошибка, напишите разработчику, чтобы он ее исправил"
        self.send_message(user_id, message)


    def tell_find_city(self, user_id, name_us):
        """Отправляет сообщение о необходимости выбора города"""

        message = f'{name_us} укажи название страны, а затем название города. Например, Россия Москва или ' \
              f'Белоруссия Брест.'
        self.send_message(user_id, message)


    def tell_something(self, user_id, name_us):
        """Функция ответчает на невалидные запросы пользователя, который уже пользовался Чат Ботом"""

        mess_1 = f'{name_us} привет! Давненько не пользовался нашим ботом. Напоминаю все начинается с командой START'
        mess_2 = f'Рад видеть тебя {name_us}! Основные команды START, FINISH, HELP'
        mess_3 = f'Рад что решил ещё раз поговорить со мной! Давай найдем тебе пару, дай команду START'
        mess_4 = f'Наверное что-то пошло не так давай еще раз начнем с команды START'
        messages = [mess_1, mess_2, mess_3, mess_4]
        index = random.randint(0, 3)
        message = messages[index]
        self.send_message(user_id, message)


bot = LongPollBot()
bot.do_listen()

