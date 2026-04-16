import json

from PIL import Image
from flask import render_template, Blueprint
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.utils import redirect

from data import db_session
from data.chats import Chat
from data.users import User
from forms.login_form import LoginForm
from forms.register_form import RegisterForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/main_page")
    login_form = LoginForm()
    if login_form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(
            User.email == login_form.email.data
        ).first()
        if user and user.check_password(login_form.password.data):
            login_user(user, remember=login_form.remember_me.data)
            return redirect("/main_page")
        return render_template("login.html", form=login_form, message="Пользователь не существует", title="Авторизация")
    return render_template("login.html", form=login_form, title="Авторизация")


@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    reg_form = RegisterForm()
    if reg_form.validate_on_submit():
        session = db_session.create_session()
        guy = User(
            surname=reg_form.surname.data,
            name=reg_form.name.data,
            email=reg_form.email.data
        )
        guy.hash_password(reg_form.password.data)
        if reg_form.password.data != reg_form.check_password.data:
            return render_template("register.html", form=reg_form, title="Регистрация",
                                   message="Новый пароль не совпадает с повторно введённым")
        session.add(guy)
        session.commit()
        login_user(guy, remember=reg_form.remember_me.data)
        im = Image.open('static/img/min_logo.png')
        im.save(f"static/img/avatars/user_{guy.id}.png")
        saved_messages = Chat(
            title="Избранное",
            creator_id=guy.id,
            avatar_url="img/saved_messages_icon.png",
            is_public=False,
            is_group=False
        )
        session.add(saved_messages)
        session.commit()
        saved_messages.json_url = f"chat_{saved_messages.id}"
        saved_messages.members.append(guy)
        session.commit()
        with open(f"chats_jsons/chat_{saved_messages.id}.json", "w", encoding='utf-8') as saved_json:
            json.dump({}, saved_json)
        with open(f"users_settings/user_{guy.id}_settings.json", "w", encoding='utf-8') as style_json:
            json.dump({"text_size": 10, "messages_roundness": 2, "avatars_roundness": 5}, style_json)
        return redirect("/main_page")
    return render_template("register.html", form=reg_form, title="Регистрация")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")