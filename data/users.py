from sqlalchemy import Column, Integer, String, Boolean
from flask_login import UserMixin
from hashlib import md5

from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase
from .user_channel_moderators import UserChannelModerator


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    surname = Column(String)
    name = Column(String)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    is_deleted = Column(Boolean, default=False)
    is_moderator = Column(Boolean, default=False)

    chats = relationship("Chat", secondary="user_chat_association", back_populates="members")
    created_chats = relationship("Chat", back_populates="creator")
    moderated_chats = relationship("Chat", secondary="user_channel_moderators", back_populates="moderators")

    def __repr__(self):
        return f"{self.id} {self.surname} {self.name} {self.email}"

    def hash_password(self, password):
        self.hashed_password = md5(password.encode()).hexdigest()

    def check_password(self, password):
        return self.hashed_password == md5(password.encode()).hexdigest()
