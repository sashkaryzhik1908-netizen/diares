import json
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    IntegerField,
    TextAreaField,
    SubmitField,
    SelectField,
    BooleanField,
    PasswordField,
)
from flask_login import UserMixin, LoginManager, login_user, logout_user
from wtforms.validators import DataRequired, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "your_secret_key"

db = SQLAlchemy(app)

migrations = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ___модели___
class Category(db.Model):
    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    template = db.Column(db.Text, nullable=False)
    variables = db.relationship(
        "TemplateVariable", backref="category", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Category {self.name}>"


class TemplateVariable(db.Model):
    __tablename__ = "template_variable"
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=False)
    label = db.Column(db.String(150), nullable=False)
    field_type = db.Column(db.String(30), nullable=False)
    required = db.Column(db.Boolean, default=False, nullable=False)
    options = db.relationship(
        "VariableOption", backref="variable", cascade="all, delete-orphan"
    )
    __table_args__ = (
        db.UniqueConstraint("category_id", "name", name="unique_category_variable"),
    )


class VariableOption(db.Model):
    __tablename__ = "variable_option"
    id = db.Column(db.Integer, primary_key=True)
    variable_id = db.Column(
        db.Integer, db.ForeignKey("template_variable.id"), nullable=False
    )
    value = db.Column(db.String(255), nullable=False)
    output_value = db.Column(db.String(255), nullable=False)
    order = db.Column(db.Integer, nullable=False)


class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(500), nullable=False)
    is_admin = db.Column(db.Boolean, default=True, nullable=False)


class Drug(db.Model):
    __tablename__ = "drug"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(122), nullable=False)
    type = db.Column(db.String(122), nullable=False)
    purpose = db.Column(db.String(122), nullable=False)
    variables = db.relationship(
        "DrugVariable", backref="drug", cascade="all, delete-orphan"
    )


class DrugVariable(db.Model):
    __tablename__ = "drug_variable"
    id = db.Column(db.Integer, primary_key=True)
    drug_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=False)
    label = db.Column(db.String(150), nullable=False)
    field_type = db.Column(db.String(30), nullable=False)
    required = db.Column(db.Boolean, default=False, nullable=False)
    options = db.relationship(
        "DrugOption", backref="variable", cascade="all, delete-orphan"
    )
    __table_args__ = (
        db.UniqueConstraint("drug_id", "name", name="unique_drug_variable"),
    )


class DrugOption(db.Model):
    __tablename__ = "drug_option"
    id = db.Column(db.Integer, primary_key=True)
    variable_id = db.Column(
        db.Integer, db.ForeignKey("drug_variable.id"), nullable=False
    )
    value = db.Column(db.String(255), nullable=False)
    output_value = db.Column(db.String(255), nullable=False)
    order = db.Column(db.Integer, nullable=False)


# __формы___
class RegisterForm(FlaskForm):
    username = StringField("Имя пользователя", validators=[DataRequired()])
    password = PasswordField(
        "Пароль",
        validators=[
            DataRequired(),
            EqualTo("confirm", message="Пароли должны совпадать"),
        ],
    )
    confirm = PasswordField("Подтвердите пароль", validators=[DataRequired()])
    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    username = StringField("Имя пользователя", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти")


class DrugForm(FlaskForm):
    name = StringField("Название медикамента", validators=[DataRequired()])
    type = SelectField(
        "Путь введения",
        choices=[
            "внутримышечно",
            "внутривенно",
            "в зонд",
            "перорально",
            "подкожно",
            "внутривенно, путем микроструйной перфузинной подачи",
            "на перфузоре",
        ],
    )
    purpose = StringField("С целью")
    submit = SubmitField("Добавить")


class CategoryForm(FlaskForm):
    name = SelectField(
        "Выберите категорию",
        choices=[],
        validators=[DataRequired()],
    )
    template = TextAreaField(
        "Шаблон категории",
        validators=[DataRequired()],
    )
    submit = SubmitField("Сохранить изменения")


class DrugVariableForm(FlaskForm):
    name = StringField("Техническое имя", validators=[DataRequired()])
    label = StringField("Название поля", validators=[DataRequired()])
    field_type = SelectField(
        "Тип поля",
        choices=[
            ("select", "Один вариант"),
            ("multiselect", "Несколько вариантов"),
            ("text", "Текст"),
            ("number", "Число"),
        ],
    )
    required = BooleanField("Обязательное поле")
    submit = SubmitField("Сохранить")


class TemplateVariableForm(FlaskForm):
    name = StringField("Техническое имя", validators=[DataRequired()])
    label = StringField("Название поля", validators=[DataRequired()])
    field_type = SelectField(
        "Тип поля",
        choices=[
            ("select", "Один вариант"),
            ("multiselect", "Несколько вариантов"),
            ("text", "Текст"),
            ("number", "Число"),
        ],
    )
    required = BooleanField("Обязательное поле")
    submit = SubmitField("Сохранить")


class VariableOptionForm(FlaskForm):
    value = StringField("Значение", validators=[DataRequired()])
    output_value = StringField("Выводимое значение", validators=[DataRequired()])
    order = IntegerField("Порядок отображения", validators=[DataRequired()])
    submit = SubmitField("Сохранить")


class Diary(db.Model):
    __tablename__ = "diary"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    entries = db.relationship(
        "DiaryEntry",
        backref="diary",
        cascade="all, delete-orphan",
        order_by="DiaryEntry.position",
    )


class DiaryEntry(db.Model):
    __tablename__ = "diary_entry"

    id = db.Column(db.Integer, primary_key=True)

    diary_id = db.Column(
        db.Integer,
        db.ForeignKey("diary.id"),
        nullable=False,
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("category.id"),
        nullable=False,
    )

    text = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, nullable=False)

    category = db.relationship("Category")

    __table_args__ = (
        db.UniqueConstraint(
            "diary_id",
            "category_id",
            name="unique_diary_category",
        ),
    )


# __маршруты___
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Проверяем, существует ли пользователь
        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            return render_template(
                "register.html", form=form, error="Такое имя пользователя уже занято"
            )

        # Создаём нового пользователя
        user = User(username=username, password=generate_password_hash(password))

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("index"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("index"))
        else:
            return render_template(
                "login.html", form=form, error="Неверное имя пользователя или пароль"
            )

    return render_template("login.html", form=form)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/categories/add", methods=["GET", "POST"])
def add_category():
    form = CategoryForm()

    categories = Category.query.order_by(Category.order).all()

    form.name.choices = [(str(c.id), c.name) for c in categories]

    if form.validate_on_submit():
        category = Category.query.get_or_404(int(form.name.data))
        category.template = form.template.data

        db.session.commit()

        return redirect(url_for("view_category", category_id=category.id))

    return render_template("add_category.html", form=form)


@app.route("/categories/edit/<int:category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    categories = Category.query.order_by(Category.order).all()
    category = Category.query.get_or_404(category_id)

    form = CategoryForm(obj=category)

    form.name.choices = [(str(c.id), c.name) for c in categories]

    if request.method == "GET":
        form.name.data = str(category.id)
        form.template.data = category.template

    if form.validate_on_submit():
        selected_category = Category.query.get_or_404(int(form.name.data))

        selected_category.template = form.template.data

        db.session.commit()

        return redirect(url_for("list_categories", category_id=selected_category.id))

    return render_template("add_category.html", form=form, category=category)


@app.route("/categories/<int:category_id>/add_variable", methods=["GET", "POST"])
def add_variable(category_id):
    category = Category.query.get_or_404(category_id)
    form = TemplateVariableForm()
    if form.validate_on_submit():
        variable = TemplateVariable(
            category_id=category.id,
            name=form.name.data,
            label=form.label.data,
            field_type=form.field_type.data,
            required=form.required.data,
        )
        db.session.add(variable)
        db.session.commit()
        return redirect(url_for("view_category", category_id=category.id))
    return render_template("add_variable.html", form=form, category=category)


@app.route("/categories/edit_variable/<int:variable_id>", methods=["GET", "POST"])
def edit_variable(variable_id):
    variable = TemplateVariable.query.get_or_404(variable_id)
    form = TemplateVariableForm(obj=variable)
    if form.validate_on_submit():
        variable.name = form.name.data
        variable.label = form.label.data
        variable.field_type = form.field_type.data
        variable.required = form.required.data
        db.session.commit()
        return redirect(url_for("view_category", category_id=variable.category_id))
    return render_template("add_variable.html", form=form, variable=variable)


@app.route("/categories/del_variable/<int:variable_id>", methods=["POST"])
def del_variable(variable_id):
    variable = TemplateVariable.query.get_or_404(variable_id)

    category_id = variable.category_id

    db.session.delete(variable)
    db.session.commit()

    return redirect(url_for("view_category", category_id=category_id))


@app.route("/variables/<int:variable_id>/add_option", methods=["GET", "POST"])
def add_option(variable_id):
    variable = TemplateVariable.query.get_or_404(variable_id)
    form = VariableOptionForm()
    if form.validate_on_submit():
        option = VariableOption(
            variable_id=variable.id,
            value=form.value.data,
            output_value=form.output_value.data,
            order=form.order.data,
        )
        db.session.add(option)
        db.session.commit()
        return redirect(url_for("view_category", category_id=variable.category_id))
    return render_template("add_option.html", form=form, variable=variable)


@app.route(
    "/variables/<int:variable_id>/options/<int:option_id>/edit", methods=["GET", "POST"]
)
def edit_option(variable_id, option_id):
    variable = TemplateVariable.query.get_or_404(variable_id)
    option = VariableOption.query.filter_by(
        id=option_id, variable_id=variable_id
    ).first_or_404()

    form = VariableOptionForm(obj=option)

    if form.validate_on_submit():
        option.value = form.value.data
        option.output_value = form.output_value.data
        option.order = form.order.data

        db.session.commit()

        return redirect(url_for("list_options", variable_id=variable.id))

    return render_template(
        "add_option.html", form=form, variable=variable, option=option
    )


@app.route(
    "/variables/<int:variable_id>/options/<int:option_id>/delete",
    methods=["GET", "POST"],
)
def delete_option(variable_id, option_id):
    variable = TemplateVariable.query.get_or_404(variable_id)
    option = VariableOption.query.filter_by(
        id=option_id, variable_id=variable_id
    ).first_or_404()

    db.session.delete(option)
    db.session.commit()

    return redirect(url_for("list_options", variable_id=variable.id))


@app.route("/categories")
def list_categories():
    categories = Category.query.all()
    return render_template("list_categories.html", categories=categories)


@app.route("/categories/<int:category_id>")
def view_category(category_id):
    category = Category.query.get_or_404(category_id)
    variables = TemplateVariable.query.filter_by(category_id=category.id).all()
    return render_template("view_category.html", category=category, variables=variables)


@app.route(
    "/diaries/<int:diary_id>/categories/<int:category_id>/fill",
    methods=["GET", "POST"],
)
def fill_category(diary_id, category_id):
    diary = Diary.query.get_or_404(diary_id)
    category = Category.query.get_or_404(category_id)

    values = {}
    errors = []
    generated_text = None

    if request.method == "POST":
        for variable in category.variables:
            if variable.field_type == "multiselect":
                selected_ids = request.form.get(variable.name, "").split(",")

                options = {
                    str(option.id): option.output_value for option in variable.options
                }

                values[variable.name] = ", ".join(
                    options[option_id]
                    for option_id in selected_ids
                    if option_id in options
                )

            elif variable.field_type == "select":
                selected = request.form.get(variable.name)

                option = next(
                    (option for option in variable.options if option.value == selected),
                    None,
                )

                values[variable.name] = option.output_value if option else ""

            else:
                values[variable.name] = request.form.get(variable.name, "").strip()

            if variable.required and not values[variable.name]:
                errors.append(f"Заполните поле «{variable.label}».")
        if category.slug == "complaints":
            custom_complaints = request.form.get("custom_complaints", "").strip()

            if custom_complaints:
                values["custom_complaints"] = f", {custom_complaints}"
            else:
                values["custom_complaints"] = ""

        if not errors:
            generated_text = app.jinja_env.from_string(category.template).render(
                **values
            )

            # Проверяем, есть ли категория в этом дневнике
            entry = DiaryEntry.query.filter_by(
                diary_id=diary.id,
                category_id=category.id,
            ).first()

            if entry:
                # Обновляем существующий текст
                entry.text = generated_text

            else:
                # Создаём новую запись
                entry = DiaryEntry(
                    diary_id=diary.id,
                    category_id=category.id,
                    text=generated_text,
                    position=len(diary.entries),
                )

                db.session.add(entry)

            db.session.commit()

            return redirect(url_for("view_diary", diary_id=diary.id))

    return render_template(
        "fill_category.html",
        category=category,
        diary=diary,
        values=values,
        errors=errors,
        generated_text=generated_text,
    )


@app.route("/diaries")
def list_diaries():
    diaries = Diary.query.order_by(Diary.created_at.desc()).all()
    return render_template("diaries.html", diaries=diaries)


@app.route("/categories/<int:variable_id>/options")
def list_options(variable_id):
    variable = TemplateVariable.query.get_or_404(variable_id)
    options = VariableOption.query.filter_by(variable_id=variable_id).all()
    return render_template("list_options.html", options=options, variable=variable)


@app.route("/diaries/create", methods=["POST"])
def create_diary():
    diary = Diary()

    db.session.add(diary)
    db.session.commit()

    return redirect(url_for("view_diary", diary_id=diary.id))


@app.route("/diaries/<int:diary_id>")
def view_diary(diary_id):
    diary = Diary.query.get_or_404(diary_id)

    categories = Category.query.order_by(Category.order).all()

    return render_template(
        "view_diary.html",
        diary=diary,
        categories=categories,
    )


@app.route("/diaries/<int:diary_id>/delete", methods=["POST"])
def delete_diary(diary_id):
    diary = Diary.query.get_or_404(diary_id)

    db.session.delete(diary)
    db.session.commit()

    return redirect(url_for("list_diaries"))


@app.route("/add_drugs", methods=["GET", "POST"])
def add_drugs():
    form = DrugForm()

    if form.validate_on_submit():
        drug = Drug(name=form.name.data, type=form.type.data, purpose=form.purpose.data)

        db.session.add(drug)
        db.session.commit()
        return redirect(url_for("index"))

    return render_template("add_drugs.html", form=form)


if __name__ == "__main__":
    app.run(debug=True)
