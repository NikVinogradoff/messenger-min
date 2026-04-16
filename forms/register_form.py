from wtforms.fields.simple import StringField, EmailField, PasswordField, SubmitField
from wtforms.validators import DataRequired

from forms.login_form import LoginForm


class RegisterForm(LoginForm):
    surname = StringField("Фамилия")
    name = StringField("Имя")
    email = EmailField("Почта", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    check_password = PasswordField("Повторите введённый пароль", validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')
