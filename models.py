import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UserInfo(Base):
    """
    Для того чтобы хранить информацию о пользователях, которые использовали наш Бот. (кто, когда, мужчины или женщины)
    также для постоянных пользователей сценарий текста немного другой.
    """
    __tablename__ = "users_info"
    id = sq.Column(sq.Integer, primary_key=True)
    first_name = sq.Column(sq.String(length=100))
    last_name = sq.Column(sq.String(length=100), nullable=True)
    user_id = sq.Column(sq.Integer, unique=True)
    sex = sq.Column(sq.String(length=15))
    date_using = sq.Column(sq.DateTime)

    def __str__(self):
        return f'id - {self.user_id}, name -{self.first_name}'


class BlackList(Base):
    """
    Для внесения пользователей в черный список. Связь один ко многим
    """
    __tablename__ = "black_list"
    id = sq.Column(sq.Integer, primary_key=True)
    users_id = sq.Column(sq.Integer, sq.ForeignKey("users_info.user_id"), nullable=False)
    block_user_id = sq.Column(sq.Integer)

    def __str__(self):
        return f'id - {self.id}, black_list - {self.main_user_id}'


class ShowingUser(Base):
    """Для хранения параметров поиска"""

    __tablename__ = "showing_user"
    id = sq.Column(sq.Integer, primary_key=True)
    users_id = sq.Column(sq.Integer, sq.ForeignKey("users_info.user_id"), nullable=False)
    show_user_id = sq.Column(sq.Integer)


    def __str__(self):
        return f'user_id - {self.user_id}'


def create_tables(engine):
    Base.metadata.drop_all(engine)  # для удаления таблиц
    Base.metadata.create_all(engine)  # для создания таблиц
