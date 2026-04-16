from flask_wtf import FlaskForm
from wtforms.fields.simple import PasswordField, SubmitField
from wtforms.validators import DataRequired


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Введите текущий пароль', validators=[DataRequired()])
    new_password = PasswordField('Введите новый пароль', validators=[DataRequired()])
    submit = SubmitField('Сменить')
