from flask import Flask, render_template, redirect, url_for
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
)
from wtforms.validators import DataRequired


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "your_secret_key"

db = SQLAlchemy(app)

migrations = Migrate(app, db)


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


class Complaints(db.Model):
    __tablename__ = "complaints"
    id = db.Column(db.Integer, primary_key=True)


class Condition(db.Model):
    __tablename__ = "condition"
    id = db.Column(db.Integer, primary_key=True)


class Consciousness(db.Model):
    __tablename__ = "consciousness"
    id = db.Column(db.Integer, primary_key=True)


class Neurological(db.Model):
    __tablename__ = "neurological"
    id = db.Column(db.Integer, primary_key=True)


class Skin(db.Model):
    __tablename__ = "skin"
    id = db.Column(db.Integer, primary_key=True)


class Respiration(db.Model):
    __tablename__ = "respiration"
    id = db.Column(db.Integer, primary_key=True)


class Cardiovascular(db.Model):
    __tablename__ = "cardiovascular"
    id = db.Column(db.Integer, primary_key=True)


class Digestion(db.Model):
    __tablename__ = "digestion"
    id = db.Column(db.Integer, primary_key=True)


class Genitourinary(db.Model):
    __tablename__ = "genitourinary"
    id = db.Column(db.Integer, primary_key=True)


class LocalStatus(db.Model):
    __tablename__ = "local_status"
    id = db.Column(db.Integer, primary_key=True)


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


class VariableOption(db.Model):
    __tablename__ = "variable_option"
    id = db.Column(db.Integer, primary_key=True)
    variable_id = db.Column(
        db.Integer, db.ForeignKey("template_variable.id"), nullable=False
    )
    value = db.Column(db.String(255), nullable=False)
    output_value = db.Column(db.String(255), nullable=False)
    order = db.Column(db.Integer, nullable=False)


# __формы___
class CategoryForm(FlaskForm):
    name = StringField("Название категории кириллицей", validators=[DataRequired()])
    slug = StringField("Slug категории латиницей", validators=[DataRequired()])
    order = IntegerField("Порядок отображения", validators=[DataRequired()])
    template = TextAreaField("Шаблон категории", validators=[DataRequired()])
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


# __маршруты___
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/categories/add", methods=["GET", "POST"])
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            slug=form.slug.data,
            order=form.order.data,
            template=form.template.data,
        )
        db.session.add(category)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("add_category.html", form=form)


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


@app.route("/categories")
def list_categories():
    categories = Category.query.all()
    return render_template("list_categories.html", categories=categories)


@app.route("/categories/<int:category_id>")
def view_category(category_id):
    category = Category.query.get_or_404(category_id)
    return render_template("view_category.html", category=category)


if __name__ == "__main__":
    app.run(debug=True)
