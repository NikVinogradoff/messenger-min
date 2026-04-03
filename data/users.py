from sqlalchemy import Column, Integer, String
from flask_login import UserMixin
from hashlib import md5

from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    surname = Column(String)
    name = Column(String)
    email = Column(String)
    hashed_password = Column(String)
    username = Column(String, unique=True)

    def __repr__(self):
        return f"<Colonist> {self.id} {self.surname} {self.name}"

    def hash_password(self, password):
        self.hashed_password = md5(password.encode()).hexdigest()

    def check_password(self, password):
        return self.hashed_password == md5(password.encode()).hexdigest()
