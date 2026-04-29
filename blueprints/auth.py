import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from PIL import Image
from flask import render_template, Blueprint, request
from flask_login import login_user, login_required, logout_user, current_user
from random import randint
from werkzeug.utils import redirect

from data import db_session
from data.chats import Chat
from data.users import User
from forms.forgot_password_form import ForgotPasswordForm
from forms.login_form import LoginForm
from forms.register_form import RegisterForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def send_email(email, text, theme=""):
    sender_email = "minthemessenger@gmail.com"
    receiver_email = email
    password = os.environ["MAIL_PASSWORD"] # pkna dcxg xiif ukqd

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = theme
    body = str(text)
    message.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, password)
    server.send_message(message)
    server.quit()


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
        if not user:
            return render_template("login.html", form=login_form, message="Пользователь не существует",
                                   title="Авторизация")
        return render_template("login.html", form=login_form, message="Неверные почта или пароль",
                               title="Авторизация")
    return render_template("login.html", form=login_form, title="Авторизация")


@auth_bp.route("/forgot_password", methods=['GET', 'POST'])
def forgot_password(): # stage: 1 - ввод почты; 2 - ввод кода с почты; 3 - смена пароля
    fp_form = ForgotPasswordForm()
    code = ""
    if request.method == 'POST':
        stage = int(request.form.get('stage'))
        if stage == 1:
            email = fp_form.email.data
            session = db_session.create_session()
            users = session.query(User).filter(
                email == User.email
            ).all()
            if not users:
                return render_template("forgot_password.html", title="Забыли пароль", stage=1,
                                       form=fp_form, email=None, returning=False,
                                       message="Пользователя с такой почтой не существует")
            code = str(randint(1, 1000000)).rjust(6, '0')
            text = f"Код подтверждения для вашего аккаунта: {code}"
            try:
                send_email(email, text, theme="Код подтверждения")
            except Exception as e:
                print(e)
                return render_template("forgot_password.html", title="Забыли пароль", stage=1,
                                       form=fp_form, email=email, returning=False,
                                       message="Введена несуществующая почта")
        else:
            email = request.form.get('email')
        if stage == 2:
            if str(request.form.get('code')) != str(fp_form.code.data):
                return render_template("forgot_password.html", title="Забыли пароль", stage=2,
                                       form=fp_form, email=email, code=request.form.get('code'), returning=False,
                                       message="Неверный код подтверждения")
        if stage == 3:
            if fp_form.password.data != fp_form.check_password.data:
                return render_template("forgot_password.html", title="Забыли пароль", stage=3,
                                       form=fp_form, email=email, code=code, returning=False,
                                       message="Новый пароль не совпадает с повторно введённым")
            session = db_session.create_session()
            user = session.query(User).filter(
                email == User.email
            ).first()
            user.hash_password(fp_form.password.data)
            session.merge(user)
            session.commit()
            login_user(user, remember=fp_form.remember_me.data)
            return redirect("/main_page")
        stage += 1
    elif current_user.is_authenticated:
        stage = 2
        session = db_session.create_session()
        user = session.merge(current_user)
        email = user.email
        code = str(randint(1, 1000000)).rjust(6, '0')
        text = f"Код подтверждения для вашего аккаунта: {code}"
        try:
            send_email(email, text, theme="Код подтверждения")
        except Exception as e:
            print(e)
            return render_template("forgot_password.html", title="Забыли пароль", stage=2,
                                   form=fp_form, email=email, returning=True,
                                   message="Вашей почты не существует")
    else:
        stage = 1
        email = None
    return render_template("forgot_password.html", title="Забыли пароль", stage=stage, form=fp_form,
                           email=email, returning=False, code=code)


@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    reg_form = RegisterForm()
    if reg_form.validate_on_submit():
        session = db_session.create_session()
        users = session.query(User).filter(
            reg_form.email.data == User.email
        ).all()
        if users:
            return render_template("register.html", form=reg_form, title="Регистрация",
                                   message="Пользователь с такой почтой уже существует")
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