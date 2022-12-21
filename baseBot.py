import os
import vk_api
import random
from datetime import date


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
        if self.vk_session is not None:  # and self.app_session is not None:
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
            token_dict['ID_APP'] = parametrs[4]
            token_dict['TOKEN_APP'] = parametrs[17]
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

        token_dict = self.get_tokens()
        self.token_app  = token_dict['TOKEN_APP']
        try:
            self.app_session = vk_api.VkApi(token=self.token_app)
            return self.app_session
        except Exception or vk_api.AuthError as error_msg:
            print('error AuthError')

    def send_message(self, user_id, message, keyboard=None, attachment=None):
        """
         Отправка сообщения от лица авторизованного пользователя
         :param user_id: уникальный идентификатор получателя сообщения
         :param message: текст отправляемого сообщения
         :param  keyboard: клавиатура с кнопкой выбора, например, вначале общения это кнопка START и FINISH
         :param attachment: параметр для отправки медиа файлов в сообщении <type><owner_id>_<media_id> photo1072_16644
         """

        if not self.authorized:
            print("Please check your Token")
            return
        if keyboard != None:
            param = {"user_id": user_id, "message": message, "random_id": random.randint(1, 10000),
                     "keyboard": keyboard}
        if keyboard == None and attachment == None:
            param = {"user_id": user_id, "message": message, "random_id": random.randint(1, 10000)}
        if attachment != None:
            param = {"user_id": user_id, "message": message, "random_id": random.randint(1, 10000),
                     "attachment": attachment}

        try:
            self.vk_session.method("messages.send", param)
            print(f"Сообщение отправлено для ID {user_id} с текстом: {message}")
        except Exception as error:
            print("Failed to send massage")

    def get_info_user(self, user_id):
        """
        Получение информации о пользователе и формирование первичных параметров для поиска
        """
        fields = ['bdate', 'relation', 'sex', 'city', 'status']
        param = {'user_ids': user_id, 'fields': fields, 'name_case': 'nom'}
        with vk_api.VkRequestsPool(self.vk_session) as pool:
            request = pool.method('users.get', param)
        if request.error == True:
            return False
        else:
            request = request.result
            first_name = request[0].get('first_name')
            last_name = request[0].get('last_name')
            status = request[0].get('status')
            cities = request[0].get('city')
            if cities != None:
                title_city = cities.get('title')
                city_id = cities.get('id')
            else:
                title_city = ''
                city_id = 0
            bdate = request[0].get('bdate')
            relation = request[0].get('relation')
            if relation in [2, 3, 4, 5, 7] or relation == '':
                relation_for_search = 6
            else:
                relation_for_search = relation

            if bdate != None:
                datetoday = date.today()
                year = datetoday.year
                bdate = bdate.split('.')
                age = year - int(bdate[-1])
                if age < 23:
                    age_from = 18
                    age_to = 24
                else:
                    age_from = age - 5
                    age_to = age + 4
            else:
                age_from = 0
                age_to = 0
            sex_user = request[0].get('sex')
            if sex_user == 1:
                sex_forsearch = 2
            if sex_user == 2:
                sex_forsearch = 1
            if sex_user is None or sex_user == 0:
                sex_forsearch = 0
            answer = {'user_id': user_id, 'first_name': first_name, 'last_name': last_name, 'title_city': title_city,
                      'city': city_id,'sex_user': sex_user, 'sex': sex_forsearch, 'age_from': age_from, 'age_to': age_to,
                      'relation_status': relation_for_search, 'status': status}
            return answer



