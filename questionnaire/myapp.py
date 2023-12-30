# Основной файл с Python-кодом веб-приложения
from flask import Flask, render_template, request, redirect, url_for  # Flask — микро-фреймворк для создания
# веб-приложений на Python
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy  # специальный модуль flask-sqlalchemy позволяет работать с базой данных
import matplotlib
import matplotlib.pyplot as plt  # matplotlib — библиотека для визуализации данных

matplotlib.use('agg')  # чтобы избежать UserWarning: Starting a Matplotlib GUI outside of the main thread will likely
# fail (https://stackoverflow.com/questions/69924881/userwarning-starting-a-matplotlib-gui-outside-of-the-main-thread
# -will-likely-fa)

app = Flask(__name__)  # instance Flaskа
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'sqlite:///questionnaire.db'  # подключение БД
# (sqlite:/// - это тип базы)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # чтобы нормально работать с изменениями в базе (коммиты и
# обновления информации, если такие есть)

db = SQLAlchemy(app)  # указываем базе приложение


# Создаём классы отдельно для каждой таблицы
class Users(db.Model):
    __tablename__ = 'users'  # имя таблицы
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # имя колонки = специальный тип (тип данных,
    # первичный ключ, автоинкремент)
    age = db.Column(db.Integer)
    level_of_education = db.Column(db.Text)
    specialization = db.Column(db.Text)


class Answers(db.Model):
    __tablename__ = 'answers'
    answer_id = db.Column("answer_id", db.Integer, primary_key=True)
    q1 = db.Column("q1", db.Text)
    q2 = db.Column("q2", db.Text)
    q3 = db.Column("q3", db.Text)
    q4 = db.Column("q4", db.Text)


@app.route('/')  # декоратор
def index():
    return render_template("index.html")  # порождение HTML по шаблону index.html


@app.route('/questionnaire')
def question_page():
    return render_template(  # порождение HTML по шаблону questionnaire.html
        'questionnaire.html',
    )


@app.route('/results', methods=['get'])
def answer_process():
    if not request.args:  # request.args для использования данных из формы (словарь параметров)
        return redirect(url_for('/'))  # если нет ответов, то перенаправляем на главную
    age = request.args.get('age')  # метод get возвращает None, если ключа нет в словаре, и не вызывает ошибку
    level_of_education = request.args.get('level_of_education')
    specialization = request.args.get('specialization')
    if Users.query.first() is None:  # учитываем, что таблица users может быть пустой
        last_user = 0
    else:
        last_user = Users.query.all()[-1].user_id
    # Создаём профиль пользователя
    user = Users(
        user_id=last_user + 1,
        age=int(age),
        level_of_education=level_of_education,
        specialization=specialization
    )
    db.session.add(user)  # добавляем в БД
    db.session.commit()  # сохраняем
    db.session.refresh(user)  # получаем последнюю версию БД с добавленным юзером
    # Достаём ответы пользователя
    q1 = request.args.get('generation')
    q2 = request.args.get('culture_of_speech')
    q3 = request.args.get('stylistic_coloring')
    q4 = request.args.get('intellectual_speech')
    # Привязываем ответы к пользователю
    answer = Answers(answer_id=user.user_id, q1=q1, q2=q2, q3=q3, q4=q4)
    db.session.add(answer)  # добавляем в БД
    db.session.commit()  # сохраняем
    return redirect(url_for("statistics"))  # перенаправление на страницу со статистикой


@app.route('/statistics')
def statistics():
    # Создаём словарь, куда будем записывать всю статистику
    all_info = {'total_num_of_respondents': Users.query.count(),  # общее число опрошенных
                'age_max': db.session.query(func.max(Users.age)).scalar(),  # максимальный возраст информантов
                'age_min': db.session.query(func.min(Users.age)).scalar(),  # минимальный возраст информантов
                'age_mean': round(db.session.query(func.avg(Users.age)).scalar())}  # средний возраст информантов,
    # округлённый до ближайшего целого
    # Распределение информантов по уровню образования
    level_of_education_counts = db.session.query(
        Users.level_of_education, func.count(Users.level_of_education)).group_by(Users.level_of_education).all()
    # По данным опроса генерируем график (круговую диаграмму (pie chart)), отражающий распределение информантов по
    # уровню образования
    labels = [
        'школьник' if item[0] == 'school_pupil'
        else 'студент' if item[0] == 'student'
        else 'высшее' if item[0] == 'higher_education'
        else 'среднее общее' if item[0] == 'secondary_education'
        else 'среднее специальное' if item[0] == 'specialized_secondary_education'
        else 'научная степень'
        for item in level_of_education_counts
    ]
    sizes = [item[1] for item in level_of_education_counts]
    plt.pie(sizes, labels=labels, autopct='%.2f')
    plt.title('Распределение информантов по уровню образования')
    # Сохраняем график в папку static как картинку через plt.savefig()
    plt.savefig('static/level_of_education_distribution.png')
    plt.clf()  # для очистки текущего графика (чтобы labels предыдущей диаграммы не накладывались на новые)
    # Самый частый ответ на вопрос 1
    most_popular_q1_answer = db.session.query(Answers.q1, func.count(Answers.q1)).group_by(Answers.q1). \
        order_by(func.count(Answers.q1).desc()).first()
    all_info['most_popular_q1_answer'] = most_popular_q1_answer[0]
    # Процентная доля давших самый частый ответ на вопрос 1
    all_info['most_popular_q1_answer_percentage'] = round((most_popular_q1_answer[1] /
                                                           all_info['total_num_of_respondents']) * 100, 2)
    return render_template('statistics.html', all_info=all_info)  # порождение HTML по шаблону statistics.html с
    # передачей переменной all_info


if __name__ == '__main__':
    app.run()
