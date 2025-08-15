from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateTimeField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from datetime import timezone, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///feeding.db'
db = SQLAlchemy(app)


# --- Модели ---
class Feeding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

# --- Формы ---
class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class EditFeedingForm(FlaskForm):
    timestamp = DateTimeField('Время кормления', validators=[DataRequired()], format='%Y-%m-%dT%H:%M')
    submit = SubmitField('Сохранить')

# --- Авторизация ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash("Пользователь с таким логином уже существует")
            return redirect(url_for('register'))
        
        new_user = User(
            username=form.username.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(new_user)
        db.session.commit()

        # Автоматический вход после регистрации
        session['user_id'] = new_user.id

        flash("Регистрация прошла успешно! Вы вошли в систему.")
        return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            flash("Неверный логин или пароль")
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
@login_required
def add():
    from datetime import datetime
    ts_str = request.form.get('timestamp')
    timestamp = datetime.strptime(ts_str, '%Y-%m-%dT%H:%M') if ts_str else datetime.now()
    feeding = Feeding(timestamp=timestamp)
    db.session.add(feeding)
    db.session.commit()
    return redirect(url_for('index'))

# --- Главная страница ---
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    # if request.method == 'POST':
    #     feeding = Feeding()
    #     db.session.add(feeding)
    #     db.session.commit()
    #     return redirect(url_for('index'))

    feedings = Feeding.query.order_by(Feeding.id.desc()).all()
    grouped = {}
    for f in feedings:
        date_str = f.timestamp.strftime("%d.%m.%Y")
        grouped.setdefault(date_str, []).append(f)

    edit_form = EditFeedingForm()
    return render_template('index.html', grouped=grouped, edit_form=edit_form)

# --- Редактирование записи ---
@app.route('/edit/<int:id>', methods=['POST'])
@login_required
def edit(id):
    feeding = Feeding.query.get_or_404(id)
    form = EditFeedingForm()
    print(form.timestamp)
    if form.validate_on_submit():
        feeding.timestamp = form.timestamp.data
        db.session.commit()
        flash('Запись обновлена!')
    return redirect(url_for('index'))

# --- Удаление записи ---
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    feeding = Feeding.query.get_or_404(id)
    db.session.delete(feeding)
    db.session.commit()
    flash('Запись удалена!')
    return redirect(url_for('index'))

@app.template_filter('datetime_rus')
def datetime_rus(value):
    return value.strftime('%d.%m.%Y %H:%M') if value else ''



# --- Инициализация базы ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password_hash=generate_password_hash("password"))
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
