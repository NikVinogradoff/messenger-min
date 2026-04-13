from .db_session import SqlAlchemyBase
import sqlalchemy


class UserChannelModerator(SqlAlchemyBase):
    __tablename__ = 'user_channel_moderators'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False)
    chat_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("chats.id"), nullable=False)