import json
import os

from flask import render_template, request, Blueprint, Flask
from flask_login import login_required, current_user
from flask_restful import abort
from werkzeug.utils import redirect

from data import db_session
from data.chats import Chat
from data.users import User

channel_app = Flask("__main__")

channel_bp = Blueprint('channel', __name__, url_prefix='/channel')


