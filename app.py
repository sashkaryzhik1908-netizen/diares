import json
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, request, flash
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
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required
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
    return db.session.get(User, int(user_id))


# ___модели___
class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    template = db.Column(db.Text, nullable=False)

    variables = db.relationship(
        "TemplateVariable",
        backref="category",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Category {self.name}>"


class TemplateVariable(db.Model):
    __tablename__ = "template_variable"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("category.id"),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False, unique=False)
    label = db.Column(db.String(150), nullable=False)
    field_type = db.Column(db.String(30), nullable=False)
    required = db.Column(db.Boolean, default=False, nullable=False)

    options = db.relationship(
        "VariableOption",
        backref="variable",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "category_id",
            "name",
            name="unique_category_variable",
        ),
    )


class VariableOption(db.Model):
    __tablename__ = "variable_option"

    id = db.Column(db.Integer, primary_key=True)
    variable_id = db.Column(
        db.Integer,
        db.ForeignKey("template_variable.id"),
        nullable=False,
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


class Diary(db.Model):
    __tablename__ = "diary"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    entries = db.relationship(
        "DiaryEntry",
        backref="diary",
        cascade="all, delete-orphan",
        order_by="DiaryEntry.category_id",
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
    syndromes = db.Column(db.Text, nullable=False, default="")
    form_data = db.Column(db.Text, nullable=False, default="{}")

    category = db.relationship("Category")

    __table_args__ = (
        db.UniqueConstraint(
            "diary_id",
            "category_id",
            name="unique_diary_category",
        ),
    )


class TherapyPurpose(db.Model):
    __tablename__ = "therapy_purpose"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    output_value = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)


class TherapyGroup(db.Model):
    """Группа препаратов с общей целью терапии."""

    __tablename__ = "therapy_group"

    id = db.Column(db.Integer, primary_key=True)

    diary_id = db.Column(
        db.Integer,
        db.ForeignKey("diary.id"),
        nullable=False,
    )

    purpose_id = db.Column(
        db.Integer,
        db.ForeignKey("therapy_purpose.id"),
        nullable=False,
    )

    position = db.Column(db.Integer, nullable=False)

    purpose = db.relationship("TherapyPurpose")

    diary = db.relationship(
        "Diary",
        backref=db.backref(
            "therapy_groups",
            cascade="all, delete-orphan",
            order_by="TherapyGroup.position",
        ),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "diary_id",
            "purpose_id",
            name="unique_diary_therapy_purpose",
        ),
    )


class TherapyMedication(db.Model):
    """Справочник препаратов."""

    __tablename__ = "therapy_medication"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)


# __формы___
class RegisterForm(FlaskForm):
    username = StringField(
        "Имя пользователя",
        validators=[DataRequired()],
    )
    password = PasswordField(
        "Пароль",
        validators=[
            DataRequired(),
            EqualTo("confirm", message="Пароли должны совпадать"),
        ],
    )
    confirm = PasswordField(
        "Подтвердите пароль",
        validators=[DataRequired()],
    )
    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    username = StringField(
        "Имя пользователя",
        validators=[DataRequired()],
    )
    password = PasswordField(
        "Пароль",
        validators=[DataRequired()],
    )
    submit = SubmitField("Войти")


class CategoryForm(FlaskForm):
    name = StringField(
        "Введите название категории",
        validators=[DataRequired()],
    )
    slug = StringField(
        "Введите техническое название категории",
        validators=[DataRequired()],
    )
    template = TextAreaField(
        "Шаблон категории",
        validators=[DataRequired()],
    )
    submit = SubmitField("Сохранить изменения")


class TemplateVariableForm(FlaskForm):
    name = StringField(
        "Техническое имя",
        validators=[DataRequired()],
    )
    label = StringField(
        "Название поля",
        validators=[DataRequired()],
    )
    field_type = SelectField(
        "Тип поля",
        choices=[
            ("select", "Один вариант"),
            ("multiselect", "Несколько вариантов"),
            ("text", "Текст"),
            ("number", "Число"),
            ("date", "Дата"),
        ],
    )
    required = BooleanField("Обязательное поле")
    submit = SubmitField("Сохранить")


class VariableOptionForm(FlaskForm):
    value = StringField(
        "Значение",
        validators=[DataRequired()],
    )
    output_value = StringField(
        "Выводимое значение",
        validators=[DataRequired()],
    )
    order = IntegerField(
        "Порядок отображения",
        validators=[DataRequired()],
    )
    submit = SubmitField("Сохранить")


class TherapyPurposeForm(FlaskForm):
    name = StringField(
        "Название цели терапии",
        validators=[DataRequired()],
    )
    output_value = StringField(
        "Отображаемое значение",
        validators=[DataRequired()],
    )
    order = IntegerField(
        "Порядок отображения",
        validators=[DataRequired()],
    )
    submit = SubmitField("Сохранить")


class TherapyMedicationForm(FlaskForm):
    name = StringField(
        "Название препарата",
        validators=[DataRequired()],
    )
    submit = SubmitField("Сохранить")


# __маршруты___


# Регистрация
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("Такое имя пользователя уже занято.", "warning")
            return render_template("register.html", form=form)

        user = User(
            username=username,
            password=generate_password_hash(password),
        )

        db.session.add(user)
        db.session.commit()

        flash("Регистрация успешно завершена.", "success")
        return redirect(url_for("index"))

    return render_template("register.html", form=form)


# Вход
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Вы успешно вошли в систему.", "success")
            return redirect(url_for("index"))

        flash("Неверное имя пользователя или пароль.", "danger")

    return render_template("login.html", form=form)


# Выход
@app.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("index"))


# Главная страница
@app.route("/")
def index():
    return render_template("index.html")


# Добавление категории / изменение шаблона
@app.route("/categories/add", methods=["GET", "POST"])
@login_required
def add_category():
    form = CategoryForm()

    if form.validate_on_submit():
        last_order = db.session.query(db.func.max(Category.order)).scalar() or 0

        category = Category(
            name=form.name.data,
            slug=form.slug.data,
            order=last_order + 1,
            template=form.template.data,
        )

        db.session.add(category)
        db.session.commit()

        flash("Шаблон категории успешно сохранён.", "success")

        return redirect(url_for("view_category", category_id=category.id))

    return render_template("add_category.html", form=form)


# Редактирование категории
@app.route("/categories/edit/<int:category_id>", methods=["GET", "POST"])
@login_required
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)

    form = CategoryForm(obj=category)

    if form.validate_on_submit():
        category.name = form.name.data
        category.slug = form.slug.data
        category.template = form.template.data

        db.session.commit()

        flash("Шаблон категории успешно изменён.", "success")

        return redirect(url_for("view_category", category_id=category.id))

    return render_template(
        "add_category.html",
        form=form,
        category=category,
    )


# Удаление категории
@app.route("/categories/delete/<int:category_id>", methods=["POST"])
@login_required
def del_category(category_id):
    category = Category.query.get_or_404(category_id)

    db.session.delete(category)
    db.session.commit()

    flash("Категория удалена.", "success")

    return redirect(url_for("list_categories"))


# Добавление переменной
@app.route("/categories/<int:category_id>/add_variable", methods=["GET", "POST"])
@login_required
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

        flash("Переменная успешно добавлена.", "success")
        return redirect(url_for("view_category", category_id=category.id))

    return render_template(
        "add_variable.html",
        form=form,
        category=category,
    )


# Редактирование переменной
@app.route("/categories/edit_variable/<int:variable_id>", methods=["GET", "POST"])
@login_required
def edit_variable(variable_id):
    variable = TemplateVariable.query.get_or_404(variable_id)
    form = TemplateVariableForm(obj=variable)

    if form.validate_on_submit():
        variable.name = form.name.data
        variable.label = form.label.data
        variable.field_type = form.field_type.data
        variable.required = form.required.data

        db.session.commit()

        flash("Переменная успешно изменена.", "success")
        return redirect(url_for("view_category", category_id=variable.category_id))

    return render_template(
        "add_variable.html",
        form=form,
        variable=variable,
    )


# Удаление переменной
@app.route("/categories/del_variable/<int:variable_id>", methods=["POST"])
@login_required
def del_variable(variable_id):
    variable = TemplateVariable.query.get_or_404(variable_id)

    category_id = variable.category_id

    db.session.delete(variable)
    db.session.commit()

    flash("Переменная удалена.", "success")
    return redirect(url_for("view_category", category_id=category_id))


# Добавление варианта
@app.route("/variables/<int:variable_id>/add_option", methods=["GET", "POST"])
@login_required
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

        flash("Вариант успешно добавлен.", "success")
        return redirect(url_for("view_category", category_id=variable.category_id))

    return render_template(
        "add_option.html",
        form=form,
        variable=variable,
    )


# Редактирование варианта
@app.route(
    "/variables/<int:variable_id>/options/<int:option_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_option(variable_id, option_id):
    variable = TemplateVariable.query.get_or_404(variable_id)

    option = VariableOption.query.filter_by(
        id=option_id,
        variable_id=variable_id,
    ).first_or_404()

    form = VariableOptionForm(obj=option)

    if form.validate_on_submit():
        option.value = form.value.data
        option.output_value = form.output_value.data
        option.order = form.order.data

        db.session.commit()

        flash("Вариант успешно изменён.", "success")
        return redirect(url_for("list_options", variable_id=variable.id))

    return render_template(
        "add_option.html",
        form=form,
        variable=variable,
        option=option,
    )


# Удаление варианта
@app.route(
    "/variables/<int:variable_id>/options/<int:option_id>/delete",
    methods=["POST"],
)
@login_required
def delete_option(variable_id, option_id):
    variable = TemplateVariable.query.get_or_404(variable_id)

    option = VariableOption.query.filter_by(
        id=option_id,
        variable_id=variable_id,
    ).first_or_404()

    db.session.delete(option)
    db.session.commit()

    flash("Вариант удалён.", "success")
    return redirect(url_for("list_options", variable_id=variable.id))


# Список категорий
@app.route("/categories")
@login_required
def list_categories():
    categories = Category.query.order_by(Category.order).all()

    return render_template(
        "list_categories.html",
        categories=categories,
    )


# Просмотр категории
@app.route("/categories/<int:category_id>")
@login_required
def view_category(category_id):
    category = Category.query.get_or_404(category_id)

    variables = (
        TemplateVariable.query.filter_by(category_id=category.id)
        .order_by(TemplateVariable.id)
        .all()
    )

    return render_template(
        "view_category.html",
        category=category,
        variables=variables,
    )


# Список вариантов переменной
@app.route("/categories/<int:variable_id>/options")
@login_required
def list_options(variable_id):
    variable = TemplateVariable.query.get_or_404(variable_id)

    options = (
        VariableOption.query.filter_by(variable_id=variable_id)
        .order_by(VariableOption.order)
        .all()
    )

    return render_template(
        "list_options.html",
        options=options,
        variable=variable,
    )


# Заполнение категории в дневнике
@app.route(
    "/diaries/<int:diary_id>/categories/<int:category_id>/fill",
    methods=["GET", "POST"],
)
def fill_category(diary_id, category_id):
    diary = Diary.query.get_or_404(diary_id)
    category = Category.query.get_or_404(category_id)

    entry = DiaryEntry.query.filter_by(
        diary_id=diary.id,
        category_id=category.id,
    ).first()

    # Загружаем ранее сохранённые данные формы
    form_data = json.loads(entry.form_data) if entry and entry.form_data else {}

    values = {}
    errors = []
    generated_text = None

    variables = (
        TemplateVariable.query.filter_by(category_id=category.id)
        .order_by(TemplateVariable.id)
        .all()
    )

    purposes = TherapyPurpose.query.order_by(
        TherapyPurpose.order,
        TherapyPurpose.id,
    ).all()

    medications = TherapyMedication.query.order_by(
        TherapyMedication.name,
    ).all()

    if request.method == "POST":
        # Сохраняем все отправленные поля формы
        form_data = request.form.to_dict(flat=False)

        if category.slug == "prescriptions":
            allowed_methods = {
                "внутривенно",
                "внутривенно капельно",
                "внутривенно, путём микроструйной перфузионной подачи",
                "внутримышечно",
                "подкожно",
                "перорально",
                "через назогастральный зонд",
                "ингаляционно",
                "наружно",
            }

            allowed_frequencies = {
                *(f"{number} р/д" for number in range(1, 11)),
                "непрерывно",
            }

            # Получаем индексы групп назначений
            group_indexes = sorted(
                {
                    key[len("purpose_id[") : -1]
                    for key in request.form.keys()
                    if key.startswith("purpose_id[")
                    and key.endswith("]")
                    and key[len("purpose_id[") : -1].isdigit()
                },
                key=int,
            )

            if not group_indexes:
                errors.append("Добавьте хотя бы одно назначение.")

            # Получаем все ID целей терапии
            purpose_ids_int = [
                int(request.form.get(f"purpose_id[{index}]", ""))
                for index in group_indexes
                if request.form.get(
                    f"purpose_id[{index}]",
                    "",
                ).isdigit()
            ]

            # Получаем все ID препаратов
            medication_ids_int = []

            for index in group_indexes:
                medication_ids = request.form.getlist(f"medication_id[{index}][]")

                medication_ids_int.extend(
                    int(value) for value in medication_ids if value.isdigit()
                )

            purposes_dict = {
                purpose.id: purpose
                for purpose in TherapyPurpose.query.filter(
                    TherapyPurpose.id.in_(purpose_ids_int)
                ).all()
            }

            medications_dict = {
                medication.id: medication
                for medication in TherapyMedication.query.filter(
                    TherapyMedication.id.in_(medication_ids_int)
                ).all()
            }

            groups = []

            for index in group_indexes:
                # Цель терапии
                purpose_id = request.form.get(
                    f"purpose_id[{index}]",
                    "",
                )

                if not purpose_id.isdigit() or int(purpose_id) not in purposes_dict:
                    errors.append("Выберите корректную цель терапии.")
                    continue

                purpose = purposes_dict[int(purpose_id)]

                # Препараты и дозировки
                medication_ids = request.form.getlist(f"medication_id[{index}][]")

                doses = request.form.getlist(f"dose[{index}][]")

                if not medication_ids:
                    errors.append("Добавьте хотя бы один препарат.")
                    continue

                if len(medication_ids) != len(doses):
                    errors.append(
                        "Количество препаратов не совпадает " "с количеством дозировок."
                    )
                    continue

                medication_parts = []
                group_valid = True

                for medication_id, dose in zip(
                    medication_ids,
                    doses,
                ):
                    dose = dose.strip()

                    if (
                        not medication_id.isdigit()
                        or int(medication_id) not in medications_dict
                    ):
                        errors.append("Выберите корректный препарат.")
                        group_valid = False
                        continue

                    if not dose:
                        errors.append("Укажите дозу каждого препарата.")
                        group_valid = False
                        continue

                    medication = medications_dict[int(medication_id)]

                    medication_parts.append(f"{medication.name} {dose}")

                if not group_valid:
                    continue

                # Общий способ введения
                method = request.form.get(
                    f"administration_method[{index}]",
                    "",
                )

                if method not in allowed_methods:
                    errors.append("Выберите корректный способ введения.")
                    continue

                # Общая кратность
                frequency = request.form.get(
                    f"frequency[{index}]",
                    "",
                )

                if frequency not in allowed_frequencies:
                    errors.append("Выберите корректную кратность.")
                    continue

                # Общая дата начала
                start_date = request.form.get(
                    f"start_date[{index}]",
                    "",
                ).strip()

                formatted_date = ""

                if start_date:
                    try:
                        formatted_date = datetime.strptime(
                            start_date,
                            "%Y-%m-%d",
                        ).strftime("%d.%m.%Y")

                    except ValueError:
                        errors.append("Укажите корректную дату начала.")
                        continue

                # Объединяем препараты знаком +
                medications_text = " + ".join(medication_parts)

                # Общие параметры добавляем один раз
                group_text = f"{medications_text} {method} {frequency}"

                if formatted_date:
                    group_text += f" (с {formatted_date})"

                groups.append(
                    {
                        "name": purpose.output_value,
                        "text": group_text,
                    }
                )

            # Формируем итоговый текст
            if not errors:
                lines = [
                    "В плане интенсивной терапии:",
                    "",
                ]

                for number, group in enumerate(groups, start=1):
                    lines.append(f"{number}. {group['name']}: {group['text']}.")

                    if number < len(groups):
                        lines.append("")

                generated_text = "\n".join(lines).strip()

        else:
            for variable in variables:
                if variable.field_type == "multiselect":
                    selected_ids = request.form.get(
                        variable.name,
                        "",
                    ).split(",")

                    selected_options = VariableOption.query.filter(
                        VariableOption.variable_id == variable.id,
                        VariableOption.id.in_(
                            [
                                int(option_id)
                                for option_id in selected_ids
                                if option_id.isdigit()
                            ]
                        ),
                    ).all()

                    options = {str(option.id): option for option in selected_options}

                    values[variable.name] = ", ".join(
                        options[option_id].output_value
                        for option_id in selected_ids
                        if option_id in options
                    )

                    if variable.name == "reasons":
                        values["syndromes"] = [
                            options[option_id].value
                            for option_id in selected_ids
                            if option_id in options
                        ]

                elif variable.field_type == "select":
                    selected = request.form.get(variable.name)

                    option = next(
                        (
                            option
                            for option in variable.options
                            if option.value == selected
                        ),
                        None,
                    )

                    values[variable.name] = option.output_value if option else ""

                elif variable.field_type == "date":
                    date_value = request.form.get(
                        variable.name,
                        "",
                    ).strip()

                    if date_value:
                        values[variable.name] = datetime.strptime(
                            date_value,
                            "%Y-%m-%d",
                        ).strftime("%d.%m.%Y")
                    else:
                        values[variable.name] = ""

                else:
                    values[variable.name] = request.form.get(
                        variable.name,
                        "",
                    ).strip()

                if variable.required and not values[variable.name]:
                    errors.append(f"Заполните поле «{variable.label}».")

            if category.slug == "complaints":
                custom_complaints = request.form.get(
                    "custom_complaints",
                    "",
                ).strip()

                if custom_complaints:
                    values["custom_complaints"] = f", {custom_complaints}"
                else:
                    values["custom_complaints"] = ""

        if not errors:
            if generated_text is None:
                generated_text = app.jinja_env.from_string(category.template).render(
                    **values
                )

            syndromes = ", ".join(values.get("syndromes", []))

            if entry:
                entry.text = generated_text

                if category.slug == "condition":
                    entry.syndromes = syndromes

                entry.form_data = json.dumps(
                    form_data,
                    ensure_ascii=False,
                )

            else:
                last_position = max(
                    (item.position for item in diary.entries),
                    default=-1,
                )

                entry = DiaryEntry(
                    diary_id=diary.id,
                    category_id=category.id,
                    text=generated_text,
                    position=last_position + 1,
                    syndromes=(syndromes if category.slug == "condition" else ""),
                    form_data=json.dumps(
                        form_data,
                        ensure_ascii=False,
                    ),
                )

                db.session.add(entry)

            db.session.commit()

            flash(
                "Раздел дневника успешно сохранён.",
                "success",
            )

            return redirect(url_for("view_diary", diary_id=diary.id))

        else:
            flash(
                "Не удалось сохранить раздел. Проверьте обязательные поля.",
                "warning",
            )

    return render_template(
        "fill_category.html",
        category=category,
        diary=diary,
        values=values,
        variables=variables,
        errors=errors,
        generated_text=generated_text,
        purposes=purposes,
        medications=medications,
        form_data=form_data,
    )


# Список дневников
@app.route("/diaries")
def list_diaries():
    diaries = Diary.query.order_by(Diary.created_at.desc()).all()

    return render_template(
        "diaries.html",
        diaries=diaries,
    )


# Создание дневника
@app.route("/diaries/create", methods=["POST"])
def create_diary():
    diary = Diary()

    db.session.add(diary)
    db.session.commit()

    flash("Новый дневник создан.", "success")
    return redirect(url_for("view_diary", diary_id=diary.id))


# Просмотр дневника
@app.route("/diaries/<int:diary_id>")
def view_diary(diary_id):
    diary = Diary.query.get_or_404(diary_id)

    diary.entries.sort(key=lambda entry: entry.category.order)

    categories = Category.query.order_by(Category.order).all()

    condition_entry = next(
        (entry for entry in diary.entries if entry.category.slug == "condition"),
        None,
    )

    syndromes = (
        condition_entry.syndromes.split(", ")
        if condition_entry and condition_entry.syndromes
        else []
    )

    return render_template(
        "view_diary.html",
        diary=diary,
        categories=categories,
        syndromes=syndromes,
    )


# Удаление дневника
@app.route("/diaries/<int:diary_id>/delete", methods=["POST"])
def delete_diary(diary_id):
    diary = Diary.query.get_or_404(diary_id)

    db.session.delete(diary)
    db.session.commit()

    flash("Дневник удалён.", "success")
    return redirect(url_for("list_diaries"))


# Список целей терапии
@app.route("/therapy/purposes")
@login_required
def list_therapy_purposes():
    purposes = TherapyPurpose.query.order_by(
        TherapyPurpose.order,
        TherapyPurpose.id,
    ).all()

    delete_form = FlaskForm()

    return render_template(
        "therapy_purposes.html",
        purposes=purposes,
        delete_form=delete_form,
    )


# Добавление цели терапии
@app.route("/therapy/purposes/add", methods=["GET", "POST"])
@login_required
def add_therapy_purpose():
    form = TherapyPurposeForm()

    if form.validate_on_submit():
        name = form.name.data.strip()

        existing_purpose = TherapyPurpose.query.filter_by(
            name=name,
        ).first()

        if existing_purpose:
            flash("Такая цель терапии уже существует.", "warning")

            return render_template(
                "add_therapy_purpose.html",
                form=form,
            )

        purpose = TherapyPurpose(
            name=name,
            output_value=form.output_value.data.strip(),
            order=form.order.data,
        )

        db.session.add(purpose)
        db.session.commit()

        flash("Цель терапии добавлена.", "success")
        return redirect(url_for("list_therapy_purposes"))

    return render_template(
        "add_therapy_purpose.html",
        form=form,
    )


# Редактирование цели терапии
@app.route(
    "/therapy/purposes/<int:purpose_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_therapy_purpose(purpose_id):
    purpose = TherapyPurpose.query.get_or_404(purpose_id)
    form = TherapyPurposeForm(obj=purpose)

    if form.validate_on_submit():
        name = form.name.data.strip()

        existing_purpose = TherapyPurpose.query.filter(
            TherapyPurpose.name == name,
            TherapyPurpose.id != purpose.id,
        ).first()

        if existing_purpose:
            flash("Такая цель терапии уже существует.", "warning")

            return render_template(
                "edit_therapy_purpose.html",
                form=form,
                purpose=purpose,
            )

        purpose.name = name
        purpose.output_value = form.output_value.data.strip()
        purpose.order = form.order.data

        db.session.commit()

        flash("Цель терапии успешно изменена.", "success")
        return redirect(url_for("list_therapy_purposes"))

    return render_template(
        "edit_therapy_purpose.html",
        form=form,
        purpose=purpose,
    )


# Удаление цели терапии
@app.route(
    "/therapy/purposes/<int:purpose_id>/delete",
    methods=["POST"],
)
@login_required
def delete_therapy_purpose(purpose_id):
    purpose = TherapyPurpose.query.get_or_404(purpose_id)

    therapy_group = TherapyGroup.query.filter_by(
        purpose_id=purpose.id,
    ).first()

    if therapy_group:
        flash(
            "Нельзя удалить цель терапии, которая используется в дневнике.",
            "warning",
        )
        return redirect(url_for("list_therapy_purposes"))

    db.session.delete(purpose)
    db.session.commit()

    flash("Цель терапии удалена.", "success")
    return redirect(url_for("list_therapy_purposes"))


# Список препаратов
@app.route("/therapy/medications")
@login_required
def list_therapy_medications():
    medications = TherapyMedication.query.order_by(TherapyMedication.name).all()
    delete_form = FlaskForm()

    return render_template(
        "therapy_medications.html",
        medications=medications,
        delete_form=delete_form,
    )


# Добавление препарата
@app.route("/therapy/medications/add", methods=["GET", "POST"])
@login_required
def add_therapy_medication():
    form = TherapyMedicationForm()

    if form.validate_on_submit():
        name = form.name.data.strip()

        existing_medication = TherapyMedication.query.filter_by(
            name=name,
        ).first()

        if existing_medication:
            flash(
                "Такой препарат уже есть в справочнике.",
                "warning",
            )

            return render_template(
                "add_therapy_medication.html",
                form=form,
            )

        medication = TherapyMedication(name=name)

        db.session.add(medication)
        db.session.commit()

        flash("Препарат успешно добавлен.", "success")
        return redirect(url_for("list_therapy_medications"))

    return render_template(
        "add_therapy_medication.html",
        form=form,
    )


# Редактирование препарата
@app.route(
    "/therapy/medications/<int:medication_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_therapy_medication(medication_id):
    medication = TherapyMedication.query.get_or_404(medication_id)
    form = TherapyMedicationForm(obj=medication)

    if form.validate_on_submit():
        name = form.name.data.strip()

        existing_medication = TherapyMedication.query.filter(
            TherapyMedication.name == name,
            TherapyMedication.id != medication.id,
        ).first()

        if existing_medication:
            flash(
                "Такой препарат уже есть в справочнике.",
                "warning",
            )

            return render_template(
                "edit_therapy_medication.html",
                form=form,
                medication=medication,
            )

        medication.name = name

        db.session.commit()

        flash("Название препарата изменено.", "success")
        return redirect(url_for("list_therapy_medications"))

    return render_template(
        "edit_therapy_medication.html",
        form=form,
        medication=medication,
    )


# Удаление препарата
@app.route(
    "/therapy/medications/<int:medication_id>/delete",
    methods=["POST"],
)
@login_required
def delete_therapy_medication(medication_id):
    medication = TherapyMedication.query.get_or_404(medication_id)

    db.session.delete(medication)
    db.session.commit()

    flash("Препарат удалён из справочника.", "success")
    return redirect(url_for("list_therapy_medications"))


if __name__ == "__main__":
    app.run(debug=True)
