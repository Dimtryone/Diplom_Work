from baseBot import BaseBot
from database import DataBase
import vk_api
import random
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


class LongPollBot(BaseBot, DataBase):
    """
    Класс чат бота, который постояннно слушает и определяет поведение пользователя и соответственно отвечает ему.
    """

    COMMANDS = ["CHANGE", "START", "FINISH", "HELP", "В ЧЕРНЫЙ СПИСОК", "БОЛЬШЕ ФОТО", "ДАЛЬШЕ"]
    KEYBOARDS = ["МУЖЧИНА", "ЖЕНЩИНА", "НЕ ЖЕНАТ/НЕ ЗАМУЖЕМ", "В АКТИВНОМ ПОИСКЕ", "ВСЁ СЛОЖНО", "НЕ УКАЗАНО"]
    COUNTRIES = ['РОССИЯ', 'БЕЛОРУССИЯ', 'УКРАИНА', 'РОС', 'РОСИЯ', 'БЕЛ', 'БЕЛОРУСИЯ', 'УКР']
    AGIES = ["ОТ 18 ДО 21", "ОТ 22 ДО 25", "ОТ 30 ДО 35", "ОТ 36 ДО 40", "ОТ 41 ДО 50", "ОТ 50 ДО 65"]
    RELATION_ID = {1: 'не женат/не замужем', 2: 'есть друг/есть подруга', 3: 'помолвлен/помолвлена',
                   4: 'женат/замужем', 5: 'всё сложно', 6: 'в активном поиске', 7: 'влюблён/влюблена',
                   8: 'в гражданском браке', 0: 'не указано'}

    def __init__(self):
        super(BaseBot, self).__init__()
        super(LongPollBot, self).__init__()
        super(DataBase, self).__init__()
        self.longpoll = VkLongPoll(self.vk_session)
        self.PEOPLE_FOUND = {}
        self.info_about_user = {}
        self.timestamp_id = 0
        self.timestamp_person = []
        self.check_user_in_Base = False
        self.param_for_search_people = {}

    def do_listen(self):
        """
        Прослушивание чата и определение пожеланий пользователя
        """

        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                text = event.text.upper()
                user_id = event.user_id
                if self.info_about_user == {}:
                    self.info_about_user = self.get_info_user(user_id)
                    name_us = self.info_about_user.get('first_name')
                else:
                    name_us = self.info_about_user.get('first_name')
                if self.param_for_search_people == {}:
                    self.save_param_for_search_people(self.info_about_user)
                if self.check_user_in_Base == False:
                    self.check_user_in_Base = self.check_user_in_UserInfo(user_id)
                    if self.check_user_in_Base == False:
                        self.tell_hello(user_id, name_us)
                        self.save_database(self.info_about_user)
                    else:
                        self.update_time_use(user_id)
                if self.check_user_in_Base == True and text.isdigit() == False and text not in self.COMMANDS and \
                    text not in self.KEYBOARDS and text not in self.AGIES and text.split()[0] not in self.COUNTRIES:
                        self.tell_something(user_id, name_us)
                if text == "FINISH":
                    self.tell_goodbye(user_id)
                if text == "HELP":
                    self.tell_help(user_id)
                if self.check_user_in_Base == True and text == "CHANGE":
                    self.tell_change(user_id, name_us)
                if self.check_user_in_Base == True and (text == "МУЖЧИНА" or text == "ЖЕНЩИНА"):
                    self.change_sex_for_search(user_id, text)
                if self.check_user_in_Base == True  and text in ["НЕ ЖЕНАТ/НЕ ЗАМУЖЕМ", "В АКТИВНОМ ПОИСКЕ", "ВСЁ СЛОЖНО", "НЕ УКАЗАНО"]:
                    self.change_status_for_search(text, user_id, name_us)
                if self.check_user_in_Base == True and text.split()[0] in self.COUNTRIES:
                    city_id = self.find_city(text, user_id)
                    if city_id == False:
                        self.tell_not_found_city(user_id, name_us)
                    if type(city_id) == int:
                        self.change_city_for_search(city_id, user_id, name_us)
                if self.param_for_search_people['city'] == 0 and text.isdigit():
                    self.change_city_for_search(text, user_id, name_us)
                if self.check_user_in_Base == True and text in self.AGIES:
                    flag = self.change_age_for_search(text)
                    if flag == True:
                        if self.find_people(user_id):
                            self.show_people(user_id)
                        else:
                            self.tell_error(user_id)
                    else:
                        self.tell_error(user_id)
                if self.param_for_search_people != {} and text == 'START':
                    if self.find_people(user_id):
                        self.show_people(user_id)
                    else:
                        self.tell_error(user_id)
                if self.check_user_in_Base == True and text == "БОЛЬШЕ ФОТО" and self.timestamp_person != []:
                    self.show_more_photos(user_id)
                if self.check_user_in_Base == True and text == "ДАЛЬШЕ" and len(self.PEOPLE_FOUND) > 0:
                    self.show_people(user_id)
                if self.check_user_in_Base == True and text == "В ЧЕРНЫЙ СПИСОК" and self.timestamp_id != '':
                    self.set_black_list(block_user_id=self.timestamp_id, user_id=user_id)

    def save_param_for_search_people(self, info_user):
        """Сохранение параметров для поиска людей, считанных со страницы пользователя."""

        sex = info_user.get('sex')
        self.param_for_search_people['sex'] = sex
        age_from = info_user.get('age_from')
        age_to = info_user.get('age_to')
        self.param_for_search_people['age_from'] = age_from
        self.param_for_search_people['age_to'] = age_to
        city_id = info_user.get('city')
        self.param_for_search_people['city'] = city_id
        relation_for_search = info_user.get('relation_status')
        self.param_for_search_people['relation_status'] = relation_for_search


    def change_age_for_search(self, text):
        """Изменение параметра поиска возраст. API VK: age_from, age_to"""

        text = text.split()
        age_from = int(text[1])
        age_to = int(text[3])
        try:
            self.param_for_search_people['age_from'] = age_from
            self.param_for_search_people['age_to'] = age_to
            return True
        except Exception as error:
            return False


    def change_sex_for_search(self, user_id, text):
        """Сохранение в БД параметра поиска пол второй половины"""

        if text == "МУЖЧИНА":
            sex = 2
        if text == "ЖЕНЩИНА":
            sex = 1
        self.param_for_search_people['sex'] = sex
        self.tell_choice_status(user_id)


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


    def change_status_for_search(self, text, user_id, name_us) :
        """Сохранение параметра поиска статус"""

        status_id = {"НЕ ЖЕНАТ/НЕ ЗАМУЖЕМ": 1, "ВСЁ СЛОЖНО": 5, "В АКТИВНОМ ПОИСКЕ": 6, "НЕ УКАЗАНО": 0}
        status = status_id[text]
        self.param_for_search_people['status'] = status
        self.tell_find_city(user_id, name_us)

    def tell_find_city(self, user_id, name_us):
        """Отправляет сообщение о необходимости выбора города"""

        message = f'{name_us} укажи название страны, а затем название города. Например, Россия Москва или ' \
                  f'Белоруссия Брест.'
        self.send_message(user_id, message)


    def find_city(self, text, user_id):
        """Определяет идентификатор города из БД VK"""

        self.param_for_search_people['city'] == 0
        text = text.split()
        q = ' '.join(text[1:])
        countries = {'РОССИЯ': 1, 'БЕЛОРУССИЯ': 3, 'УКРАИНА': 2, 'РОС': 1, 'БЕЛ': 3, 'УКР': 2, 'РОСИЯ': 1,
                     'БЕЛОРУСИЯ': 3}
        country_id = countries[text[0]]
        param = {'country_id': country_id, 'q': q}
        with vk_api.VkRequestsPool(self.app_session.get_api()) as pool:
            request = pool.method('database.getCities', param)
        if request.error == True:
            return False
        else:
            city = request.result
            count = city['count']
            if count == 1:
                return city['items'][0]['id']
            elif count == 0:
                return False
            else:
                message = f'Результат поиска выдал {count} городов с похожим названием. Внимательно изучите список ниже и пришлите' \
                          ' сообщение с номером ID необходимого города, Например, "113056".'
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
                    if country == None and region == None and area == None:
                        message = f'id города {title}: {id}, регион и область отсутствует'
                        self.send_message(user_id, message)
                    else:
                        continue
                return True


    def change_city_for_search(self, city_id, user_id, name_us):
        """"Изменяет город, когда пользователь решит изменить кретерии поиска"""

        city_id = int(city_id)
        self.param_for_search_people['city'] = city_id
        message = f'{name_us} город для поиска изменен.'
        self.send_message(user_id, message)
        self.get_age(user_id, name_us)


    def get_age(self, user_id, name_us):
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
        self.send_message(user_id, f"{name_us} Выбирай возраст и переходи к поиску", keyboard=keyboard)


    def find_people(self, user_id):
        """Функция ищет людей по заданным параметрам."""

        city_id = int(self.param_for_search_people['city'])
        sex = int(self.param_for_search_people['sex'])
        age_from = int(self.param_for_search_people['age_from'])
        age_to = int(self.param_for_search_people['age_to'])
        status = int(self.param_for_search_people['relation_status'])
        fields = {'has_photo': 1, 'education': 'education', 'about': 'about', 'bdate': 'bdate'}
        param = {'city': city_id, 'sex': sex, 'age_from': age_from, 'age_to': age_to, 'status': status, 'offset': '20',
                 'fields': fields}
        with vk_api.VkRequestsPool(self.app_session.get_api()) as pool:
            request = pool.method('users.search', param)
        if request.error == True:
            message = "Ошибка поиска в VK"
            self.send_message(user_id, message)
            return False
        else:
            people = request.result
            self.PEOPLE_FOUND = {}
            for item in people['items']:
                if item.get('can_access_closed') == True:
                    first_name = item.get('first_name')
                    last_name = item.get('last_name')
                    university_name = item.get('university_name', 'Информации об университете нет')
                    faculty_name = item.get('faculty_name', 'Информации о факультете нет')
                    about = item.get('about', 'Информации о себе нет')
                    id = item.get('id')
                    url_person = 'https://vk.com/id' + str(id)
                    bdate = item.get('bdate')
                    self.PEOPLE_FOUND[id] = [first_name, last_name, university_name, faculty_name, about, bdate, url_person]
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
                result_link_photos = []
                if photos['count'] > 2:
                    links_photos = {}
                    likes = []
                    for item in photos['items']:
                        like = item['likes']['count']
                        likes.append(like)
                        id_photo = item["id"]
                        link_photo = f'https://vk.com/id{key}?z=photo{key}_{id_photo}%2Fphotos{key}'
                        links_photos[like] = link_photo
                    likes.sort(reverse=True)
                    index = 0
                    for i in range(3):
                        link = links_photos[likes[index]]
                        result_link_photos.append(link)
                        index += 1
                else:
                    for item in photos['items']:
                        id_photo = item["id"]
                        link_photo = f'https://vk.com/id{key}?z=photo{key}_{id_photo}%2Fphotos{key}'
                        result_link_photos.append(link_photo)
            value.append(result_link_photos)
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
        if self.check_person_in_black_list(user_id, self.timestamp_id) and self.check_in_swowing_list(user_id, self.timestamp_id):
            first_name = person[0]
            last_name = person[1]
            university_name = person[2]
            faculty_name = person[3]
            about = person[4]
            url_person = person[6]
            bdate = person[5]
            message = f'{first_name} {last_name} ссылка на профиль {url_person} \n дата рождения {bdate} \n ' \
                      f'о себе: {about}\n университет {university_name}\n факультет {faculty_name}'
            keyboard = VkKeyboard()
            keyboard.add_button(label="Дальше", color=VkKeyboardColor.PRIMARY)
            keyboard.add_button(label="Больше фото", color=VkKeyboardColor.POSITIVE)
            keyboard.add_line()
            keyboard.add_button(label="В черный список", color=VkKeyboardColor.NEGATIVE)
            keyboard = keyboard.get_keyboard()
            self.send_message(user_id, message, keyboard=keyboard)
            self.add_person_in_ShowingUser(user_id, self.timestamp_id)
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
        photos = person[7]
        for photo in photos:
            message = f'{photo}'
            self.send_message(user_id, message)


    def get_keyboard_start_finish_help(self, change=None):
        """Для получения популярных кнопок"""

        if change == None:
            keyboard = VkKeyboard()
            keyboard.add_button(label="START", color=VkKeyboardColor.PRIMARY)
            keyboard.add_button(label="HELP", color=VkKeyboardColor.PRIMARY)
            keyboard.add_line()
            keyboard.add_button(label="FINISH", color=VkKeyboardColor.NEGATIVE)
            keyboard = keyboard.get_keyboard()
            return keyboard
        if change == True:
            keyboard = VkKeyboard()
            keyboard.add_button(label="START", color=VkKeyboardColor.PRIMARY)
            keyboard.add_button(label="CHANGE", color=VkKeyboardColor.PRIMARY)
            keyboard.add_line()
            keyboard.add_button(label="HELP", color=VkKeyboardColor.PRIMARY)
            keyboard.add_button(label="FINISH", color=VkKeyboardColor.NEGATIVE)
            keyboard = keyboard.get_keyboard()
            return keyboard


    def tell_hello(self, user_id, name_us):
        """
        Сказать приветственное слово, когда пользователь впервые в чат боте
        :param user_id:
        :return:
        """
        keyboard = self.get_keyboard_start_finish_help(change=True)
        sex = self.param_for_search_people.get('sex')
        if sex == 1:
            sex_forsearch = 'женщина'
        elif sex == 2:
            sex_forsearch = 'мужчина'
        else:
            sex_forsearch = 'не установлен пол, можете задать параметр вручную'
        age_from = self.param_for_search_people.get('age_from')
        if age_from == 0:
            age_from = "не установлен, задайте параметр вручную"
        title_for_search = self.param_for_search_people.get('city')
        if title_for_search == '':
            title_for_search = "ваш город не определен, можете задать параметр поиска вручную"
        relation_id = self.param_for_search_people.get('relation_status')
        relation_for_search = self.RELATION_ID.get(relation_id)

        start_message = f'Привет {name_us} я учебный Чат Бот. Создан, чтобы найти для тебя вторую половину твоей мечты! ' \
                        f'Исходя из информации на твоей странице сформирован параметр поиска. Ты можешь задать параметры ' \
                        f'в ручную, следуй за командами.'
        self.send_message(user_id, start_message)
        start_message_2 = f'Параметры для поиска твоей половины: \n пол - {sex_forsearch} \n возраст - с {age_from} \n' \
                          f'город - {title_for_search},\n  семейный статус {relation_for_search} \nТы можешь изменить их' \
                          f' с помощью команды CHANGE.'
        self.send_message(user_id, start_message_2)
        self.send_message(user_id, "START - перейти к поиску, CHANGE - изменить праметры поиска, HELP - отобразит список"
                                   "доступных команд, а FINISH - завершит работу Бота.", keyboard=keyboard)


    def tell_change(self, user_id, name_us):
        """
        Начать работу с пользователем
        :param user_id: id пользователя
        :param name_us: Имя пользователя
        :return:
        """

        message = f'{name_us} мой учебный чат бот поможе найти тебе вторую половину. Заполни парметры, после ты сможешь ' \
                  f'выполнить поиск по ВК.'
        self.send_message(user_id, message)
        message = f'Для этого, {name_us}, тебе придется задать параметры для поиска.'
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
                  "заинтересовали, не будут повторяться. \n\tБот старается искать человека и по общим интересам, например, " \
                  "музыка, хобби и прочее.\n\n\tВ любой момент вы можете ввести команду FINISH и остановить Бот.\n\n " \
                  "Доступные команды: START, FINISH  \n\n В любой момент вы можете изменить критерии поиска. Для этого " \
                  "нужно снова ввести команду CHANGE. Поиск осуществляется только по странам России, Украины и Белоруссии."
        self.send_message(user_id, message)
        keyboard = self.get_keyboard_start_finish_help()
        self.send_message(user_id, "Выбирай команду", keyboard=keyboard)


    def tell_goodbye(self, user_id):
        """Отправляет сообщение при вводе команды FINISH"""

        message = "Буду снова рад видеть тебя"
        self.send_message(user_id, message)


    def tell_not_found_city(self, user_id, name_us):
        """Отправляет сообщение пользователю о неудачном поиске города"""

        message = f'{name_us} Данный город не найден в базе VK. повторите команду. ' \
                  f'Первым словом должна быть указана страна, а потом "город". Например, Россия Москва.'
        self.send_message(user_id, message)

    def tell_error(self, user_id):
        """Отправляет сообщение при вводе команды FINISH"""

        message = "Возникла ошибка, напишите разработчику, чтобы он ее исправил"
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
        keyboard = self.get_keyboard_start_finish_help()
        self.send_message(user_id, "Выбирай команду", keyboard=keyboard)


bot = LongPollBot()
bot.do_listen()
