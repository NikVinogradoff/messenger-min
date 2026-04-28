from wtforms.fields.numeric import IntegerField
from wtforms.fields.simple import EmailField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired

from forms.login_form import LoginForm


class ForgotPasswordForm(LoginForm):
    email = EmailField("Почта", validators=[DataRequired()])
    code = IntegerField("Код подтверждения", validators=[DataRequired()])
    password = PasswordField("Новый пароль", validators=[DataRequired()])
    check_password = PasswordField("Повторите введённый пароль", validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Продолжить')
