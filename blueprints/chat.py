import datetime
import json
import os

from flask import render_template, request, url_for, Blueprint, Flask
from flask_login import login_required, current_user
from flask_restful import abort
from werkzeug.utils import redirect, secure_filename

from data import db_session
from data.chats import Chat
from data.users import User

chat_app = Flask("__main__")

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


