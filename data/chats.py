from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase

user_chat_association = Table(
    'user_chat_association',
    SqlAlchemyBase.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('chat_id', Integer, ForeignKey('chats.id'))
)


class Chat(SqlAlchemyBase):
    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    members = relationship("User", secondary=user_chat_association, back_populates="chats")
    avatar_url = Column(String, default=None, nullable=True)

    def __repr__(self):
        return f"<Chat> {self.id} '{self.title}'"