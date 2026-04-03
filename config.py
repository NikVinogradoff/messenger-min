from flask import Flask, render_template
from flask_restful import Api
from werkzeug.utils import redirect

from data import db_session
from data.users import User

from forms.login_form import LoginForm
from forms.register_form import RegisterForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from resources.users_resource import UsersResource, UsersListResource

app = Flask(__name__)
api = Api(app)
api.add_resource(UsersResource, '/api/users/<int:user_id>')
api.add_resource(UsersListResource, '/api/users/')

app.config["SECRET_KEY"] = "password123"

login_manager = LoginManager()
login_manager.init_app(app)
