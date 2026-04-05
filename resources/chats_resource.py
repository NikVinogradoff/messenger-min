import json

from flask import jsonify
from flask_login import current_user

from data import db_session
from flask_restful import abort, Resource, reqparse
from data.chats import Chat
from data.users import User

parser = reqparse.RequestParser()
parser.add_argument('title', required=True, type=str)
parser.add_argument('creator_id', required=True, type=int)
parser.add_argument('avatar_url', type=str)
parser.add_argument('member_ids', type=int, action='append', default=[])
parser.add_argument('is_public', type=bool, default=False)


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
            'creator_id': chat.creator_id,
            'members_count': len(chat.members),
            'is_public': chat.is_public
        })

    def delete(self, chat_id):
        abort_if_chat_not_found(chat_id)
        session = db_session.create_session()
        chat = session.query(Chat).get(chat_id)
        if current_user.id != chat.creator_id:
            abort(403, message="Только создатель может удалить чат")
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
        if 'member_ids' in args and args['member_ids']:
            new_member_ids = set(args['member_ids'])
            users_to_add = session.query(User).filter(User.id.in_(new_member_ids)).all()
            user_map = {user.id: user for user in users_to_add}
            not_found = new_member_ids - set(user_map.keys())
            if not_found:
                abort(400, message=f"Пользователи не найдены: {list(not_found)}")
            creator = session.query(User).get(chat.creator_id)
            new_members = [user_map[uid] for uid in new_member_ids]
            if creator not in new_members:
                new_members.append(creator)
            chat.members = new_members
        elif 'member_ids' in args and args['member_ids'] == []:
            creator = session.query(User).get(chat.creator_id)
            chat.members = [creator]
        if 'is_public' in args:
            chat.is_public = args['is_public']
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
                    'creator_id': chat.creator_id,
                    'title': chat.title,
                    'avatar_url': chat.avatar_url,
                    'json_url': chat.json_url,
                    'members_count': len(chat.members),
                    'is_public': chat.is_public
                }
                for chat in chats
            ]
        })

    def post(self):
        args = parser.parse_args()
        session = db_session.create_session()
        creator = session.query(User).get(args['creator_id'])
        if not creator:
            abort(400, message="Создатель не найден")
        new_chat = Chat(
            title=args['title'],
            creator_id=args['creator_id'],
            avatar_url=args['avatar_url'] or None,
            is_public=args['is_public']
        )
        new_chat.members.append(creator)
        member_ids = args['member_ids']
        if member_ids:
            users_to_add = session.query(User).filter(User.id.in_(member_ids)).all()
            for user in users_to_add:
                if user not in new_chat.members:
                    new_chat.members.append(user)
            found_ids = {u.id for u in users_to_add}
            not_found = set(member_ids) - found_ids
            if not_found:
                print(f"Предупреждение: пользователи не найдены: {not_found}")
        session.add(new_chat)
        session.flush()
        new_chat.json_url = f'chat_{new_chat.id}'
        with open(f"chats_jsons/chat_{new_chat.id}.json", "w") as chat_json:
            json.dump({}, chat_json)
        session.commit()
        return jsonify({'id': new_chat.id})
