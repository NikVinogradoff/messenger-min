from hashlib import md5
import os

from dotenv import load_dotenv
from flask import jsonify, request

from data import db_session
from flask_restful import abort, Resource, reqparse
from data.users import User

parser = reqparse.RequestParser()
parser.add_argument('surname', required=True, type=str)
parser.add_argument('name', required=True, type=str)
parser.add_argument('email', required=True, type=str)
parser.add_argument('hashed_password', required=True, type=str)

load_dotenv(".env")
APIKEY = os.environ["API_KEY"]


def abort_if_user_not_found(user_id):
    session = db_session.create_session()
    user = session.query(User).get(user_id)
    if not user:
        abort(404, message=f"User {user_id} not found")
    if user.is_deleted:
        abort(410, message=f"User {user_id} is deleted")


class UsersResource(Resource):
    def get(self, user_id):
        apikey = request.args.get("apikey")
        if apikey != APIKEY:
            abort(400, message="invalid apikey")
        abort_if_user_not_found(user_id)
        session = db_session.create_session()
        user = session.query(User).get(user_id)
        return jsonify(user.to_dict(only=(
            "id", "surname", "name", "email", "hashed_password"
        )))

    def delete(self, user_id):
        apikey = request.args.get("apikey")
        if apikey != APIKEY:
            abort(400, message="invalid apikey")
        abort_if_user_not_found(user_id)
        session = db_session.create_session()
        users = session.query(User).get(user_id)
        users.is_deleted = True
        session.commit()
        return jsonify({'success': 'ok'})

    def put(self, user_id):
        apikey = request.args.get("apikey")
        if apikey != APIKEY:
            abort(400, message="invalid apikey")
        abort_if_user_not_found(user_id)
        args = parser.parse_args()
        session = db_session.create_session()
        user = session.query(User).get(user_id)
        user.surname = args['surname']
        user.name = args['name']
        user.email = args['email']
        user.hashed_password=md5(args['hashed_password'].encode()).hexdigest()
        session.commit()
        return jsonify({'success': 'ok'})


class UsersListResource(Resource):
    def get(self):
        apikey = request.args.get("apikey")
        if apikey != APIKEY:
            abort(400, message="invalid apikey")
        session = db_session.create_session()
        users = session.query(User).all()
        return jsonify({
            "users": [
                user.to_dict(only=("id", "surname", "name", "email", "hashed_password")) for user in users
            ]
        })

    def post(self):
        apikey = request.args.get("apikey")
        if apikey != APIKEY:
            abort(400, message="invalid apikey")
        args = parser.parse_args()
        session = db_session.create_session()
        users = User(
            surname=args['surname'],
            name=args['name'],
            email=args['email'],
            hashed_password=md5(args['hashed_password'].encode()).hexdigest()
        )
        session.add(users)
        session.commit()
        return jsonify({'id': users.id})
