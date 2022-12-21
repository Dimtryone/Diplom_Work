import os
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from models import create_tables, UserInfo, BlackList, ShowingUser


class DataBase:


    def __init__(self):

        self.token_dict_DB = self.get_tokens_DB()
        self.username = self.token_dict_DB['username']
        self.password_BD = self.token_dict_DB['password_BD']
        self.name_BD = self.token_dict_DB['name_BD']
        self.name_host = self.token_dict_DB['name_host']
        self.num_host = self.token_dict_DB['num_host']
        self.sex_id = {1: "женский", 2: "мужской", 3: "пол не указан"}


    def get_tokens_DB(self):
        """
        Извлечение паролей и токенов
        :return: словарь паролей и токенов
        """
        path = os.getenv('HOME') + '//Documents//Diplom_netology//tokens.txt'
        with open(path, 'r', encoding='utf-8') as file:
            parametrs = list(map(str.strip, file.readlines()))
            token_dict = {}
            token_dict['username'] = parametrs[8]
            token_dict['password_BD'] = parametrs[9]
            token_dict['name_BD'] = parametrs[10]
            token_dict['name_host'] = parametrs[11]
            token_dict['num_host'] = parametrs[12]
        return token_dict


    def get_session_DB(self):

        DSN = f"postgresql://{self.username}:{self.password_BD}@{self.name_host}:{self.num_host}/{self.name_BD}"
        engine = sqlalchemy.create_engine(DSN, echo=True, future=True)
        Session = sessionmaker(bind=engine)
        session = Session()
        #create_tables(engine)  # следует отключить после первого запуска
        return session


    def save_database(self, request):
        """
         Сохранение данных о пользователе в таблицу UserInfo, занесене user_id  в ValueSearch
         уникальность по user_id. Позволяет определять сколько раз пользователь использовал наш бот. А также
         определять тип первичного сообщения (для постоянного пользователя и для нового разные сообщения)
        :param request:
         :return: False/True
         """

        session = self.get_session_DB()
        first_name = request.get('first_name')
        last_name = request.get('last_name')
        user_id = request.get('user_id')
        sex = request.get('sex_user')
        datetime_now = datetime.now()

        user = UserInfo(first_name=first_name, last_name=last_name, user_id=user_id, sex=sex, date_using=datetime_now)
        session.add_all([user])
        try:
            session.commit()
            return True
        except Exception as error:
            return False
        finally:
            session.close()


    def update_time_use(self, user_id):
        """Для фиксации последнего времени пользования Ботом"""

        session = self.get_session_DB()
        datetime_now = datetime.now()

        session.query(UserInfo).filter(UserInfo.user_id == user_id).update({"date_using": datetime_now},
                                                                             synchronize_session='fetch')
        try:
            session.commit()
        except Exception as error:
            print("Не получилось обновить время пользования Ботом, проверьте подключение к БД")
        finally:
            session.close()


    def check_user_in_UserInfo(self, user_id):
        """Функция проверяет есть ли id в черном списке"""

        session = self.get_session_DB()
        try:
            query = session.query(UserInfo.user_id).filter(UserInfo.user_id == user_id)
        except Exception as error:
            print('не получилось узнать user_id. Проблема с БД.')
            return False
        finally:
            session.close()
        result = query.all()
        if result == []:
            return False
        else:
            for answer in result:
                if answer[0] == user_id:
                    return True
                else:
                    return False

    def set_black_list(self, block_user_id, user_id):
        """Функция помещает id пользователя в таблицу с черным списком"""

        session = self.get_session_DB()
        value = BlackList(block_user_id = block_user_id,
                          users_id=session.query(UserInfo.user_id).filter(UserInfo.user_id == user_id))
        session.add_all([value])
        try:
            session.commit()
            return True
        except Exception as error:
            print('Не удалось добавить в черный список')
            return False
        finally:
            session.close()


    def add_person_in_ShowingUser(self, user_id, show_user_id):
        """Добавление в БД id страниц, которые показывались пользователю"""

        session = self.get_session_DB()
        value = ShowingUser(show_user_id=show_user_id,
                          users_id=session.query(UserInfo.user_id).filter(UserInfo.user_id == user_id))
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
            return False
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


    def check_in_swowing_list(self, user_id, show_user_id):
        """Функция проверяет показывали ли ранее этого человека"""

        session = self.get_session_DB()
        try:
            query = session.query(ShowingUser.show_user_id).filter(ShowingUser.users_id == user_id)
        except Exception as error:
            print('не получилось узнать user name. Проблема с БД.')
            return False
        finally:
            session.close()
        result = query.all()
        if result == []:
            return True
        else:
            for answer in result:
                if answer == show_user_id:
                    return False
                else:
                    return True



