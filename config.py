from flask import Flask, render_template, request, url_for
from flask_restful import Api, abort
import os
from werkzeug.utils import redirect, secure_filename
from waitress import serve

from data import db_session
from data.users import User
from data.chats import Chat

from forms.login_form import LoginForm
from forms.register_form import RegisterForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from resources.chats_resource import ChatsResource, ChatsListResource
from resources.users_resource import UsersResource, UsersListResource

import datetime

import json

from PIL import Image

app = Flask(__name__)
api = Api(app)
api.add_resource(UsersResource, '/api/users/<int:user_id>')
api.add_resource(UsersListResource, '/api/users/')
api.add_resource(ChatsResource, '/api/chats/<int:chat_id>')
api.add_resource(ChatsListResource, '/api/chats/')

app.config["SECRET_KEY"] = "password123"

login_manager = LoginManager()
login_manager.init_app(app)
