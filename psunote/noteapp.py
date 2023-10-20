import flask
from sqlalchemy import func

import models
import forms


app = flask.Flask(__name__)
app.config["SECRET_KEY"] = "This is secret key"
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "postgresql://coe:CoEpasswd@localhost:5433/coedb"

models.init_app(app)


@app.route("/")
def index():
    db = models.db
    notes = db.session.execute(
        db.select(models.Note).order_by(models.Note.title)
    ).scalars()
    return flask.render_template(
        "index.html",
        notes=notes,
    )


@app.route("/notes/create", methods=["GET", "POST"])
def notes_create():
    form = forms.NoteForm()
    if not form.validate_on_submit():
        print("error", form.errors)
        return flask.render_template(
            "notes-create.html",
            form=form,
        )
    note = models.Note()
    form.populate_obj(note)
    note.tags = []

    db = models.db
    for tag_name in form.tags.data:
        if tag_name != '':
            tag = (
                db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name))
                .scalars()
                .first()
            )

            if not tag:
                tag = models.Tag(name=tag_name)
                db.session.add(tag)

            note.tags.append(tag)

    db.session.add(note)
    db.session.commit()

    return flask.redirect(flask.url_for("index"))

@app.route("/notes/delete/<int:note_id>", methods=["GET"])
def notes_delete(note_id):
    db = models.db
    note = db.session.query(models.Note).get(note_id)

    if note:
        db.session.delete(note)
        db.session.commit()

    return flask.redirect(flask.url_for("index"))

@app.route("/notes/edit/<int:note_id>", methods=["GET", "POST"])
def notes_edit(note_id):
    db = models.db
    note = db.session.query(models.Note).get(note_id)
    current_tags = note.tags

    fillform = ""
    for tn in current_tags:
        fillform += tn.name + ", "

    form = forms.NoteForm(obj=note)

    if form.validate_on_submit():
        note.title = form.title.data
        note.description = form.description.data

        note_tags = []
        for tag_name in form.tags.data:
            if tag_name != '':
                tag = (
                    db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name))
                    .scalars()
                    .first()
                )
                if not tag:
                    tag = models.Tag(name=tag_name)
                    db.session.add(tag)

                note_tags.append(tag)

        note.tags = note_tags
        note.updated_date = func.now()

        db.session.commit()
        return flask.redirect(flask.url_for("index"))

    return flask.render_template("notes-edit.html", form=form, note=note, fillform=fillform)


@app.route("/tags/<tag_name>")
def tags_view(tag_name):
    db = models.db
    tag = (
        db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name))
        .scalars()
        .first()
    )
    notes = db.session.execute(
        db.select(models.Note).where(models.Note.tags.any(id=tag.id))
    ).scalars()

    return flask.render_template(
        "tags-view.html",
        tag_name=tag_name,
        notes=notes,
    )


@app.route("/tags/manage")
def tags_manage():
    db = models.db
    tags = db.session.query(models.Tag).order_by(models.Tag.name).all()
    return flask.render_template("tags-management.html", tags=tags)

@app.route("/tags/edit/<int:tag_id>", methods=["GET", "POST"])
def tags_edit(tag_id):
    db = models.db
    
    tag = db.session.query(models.Tag).get(tag_id)
    form = forms.TagForm()
    if form.validate_on_submit():
        check_tag = db.session.query(models.Tag).filter(models.Tag.name == form.name.data).first()
        if not check_tag or (check_tag.name == tag.name):
            tag.name = form.name.data
            db.session.commit()
            return flask.redirect(flask.url_for("tags_manage"))
        else:
            flask.flash('Tag name "' + check_tag.name + '" already exists.')

    return flask.render_template("tags-edit.html", form=form, tag=tag)

@app.route("/tags/delete/<int:tag_id>", methods=["GET"])
def tags_delete(tag_id):
    db = models.db
    tag = db.session.query(models.Tag).get(tag_id)
    notes_with_tag = db.session.query(models.Note).filter(models.Note.tags.any(id=tag_id)).all()

    if tag:
        if notes_with_tag:
            fillform = ""
            for note in notes_with_tag:
                fillform += f'"{note.title}"'
            return flask.render_template("confirm_delete_tag.html", tag=tag, fillform=fillform)
        else:
            db.session.delete(tag)
            db.session.commit()
    
    return flask.redirect(flask.url_for("tags_manage"))


@app.route("/tags/confirm_delete/<int:tag_id>", methods=["GET"])
def tags_confirm_delete(tag_id):
    db = models.db
    tag = db.session.query(models.Tag).get(tag_id)
    notes_with_tag = db.session.query(models.Note).filter(models.Note.tags.any(id=tag_id)).all()
    for note in notes_with_tag:
        note.tags.remove(tag)
    db.session.delete(tag)
    db.session.commit()
    return flask.redirect(flask.url_for("tags_manage"))


if __name__ == "__main__":
    app.run(debug=True)
