from flask import jsonify

from data import db_session
from flask_restful import abort, Resource, reqparse
from data.chats import Chat

parser = reqparse.RequestParser()
parser.add_argument('title', required=True, type=str)
parser.add_argument('avatar_url', type=str)
parser.add_argument('json_url', type=str)


def abort_if_chat_not_found(chat_id):
    session = db_session.create_session()
    chat = session.query(Chat).get(chat_id)
    if not chat:
        abort(404, message=f"Chat {chat_id} not found")
    if chat.is_deleted:
        abort(410, message=f"Chat {chat_id} is deleted")


class ChatsResource(Resource):
    def get(self, chat_id):
        abort_if_chat_not_found(chat_id)
        session = db_session.create_session()
        chat = session.query(Chat).get(chat_id)
        return jsonify({
            'id': chat.id,
            'title': chat.title,
            'avatar_url': chat.avatar_url,
            'json_url': chat.json_url,
            'members_count': len(chat.members)
        })

    def delete(self, chat_id):
        abort_if_chat_not_found(chat_id)
        session = db_session.create_session()
        chat = session.query(Chat).get(chat_id)
        chat.is_deleted = True
        session.commit()
        return jsonify({'success': 'ok'})

    def put(self, chat_id):
        abort_if_chat_not_found(chat_id)
        args = parser.parse_args()
        session = db_session.create_session()
        chat = session.query(Chat).get(chat_id)

        chat.title = args['title']
        if args['avatar_url']:
            chat.avatar_url = args['avatar_url']
        if args['json_url']:
            chat.json_url = args['json_url']

        session.commit()
        return jsonify({'success': 'ok'})


class ChatsListResource(Resource):
    def get(self):
        session = db_session.create_session()
        chats = session.query(Chat).all()
        return jsonify({
            'chats': [
                {
                    'id': chat.id,
                    'title': chat.title,
                    'avatar_url': chat.avatar_url,
                    'json_url': chat.json_url,
                    'members_count': len(chat.members)
                }
                for chat in chats
            ]
        })

    def post(self):
        args = parser.parse_args()
        session = db_session.create_session()

        new_chat = Chat(
            title=args['title'],
            avatar_url=args['avatar_url'] or None,
            json_url=args['json_url'] or None
        )
        session.add(new_chat)
        session.commit()
        return jsonify({'id': new_chat.id})
