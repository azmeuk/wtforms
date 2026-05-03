from tests.common import DummyPostData
from wtforms.fields import ButtonField
from wtforms.form import Form


class F(Form):
    a = ButtonField("Label")
    b = ButtonField("Save", default="save")
    c = ButtonField("Delete", render_kw={"formaction": "/delete", "value": "delete"})


def test_button_field():
    assert F().a() == '<button id="a" name="a" type="submit" value="">Label</button>'


def test_button_field_default_value():
    form = F()
    assert form.b.data is None
    assert (
        form.b() == '<button id="b" name="b" type="submit" value="save">Save</button>'
    )


def test_button_field_render_kw():
    assert F().c() == (
        '<button formaction="/delete" id="c" name="c" type="submit"'
        ' value="delete">Delete</button>'
    )


def test_button_field_label_override():
    assert F().a(label="Override") == (
        '<button id="a" name="a" type="submit" value="">Override</button>'
    )


def test_button_field_with_postdata():
    form = F(DummyPostData(a="save-add"))
    assert form.a.raw_data == ["save-add"]
    assert form.a.data == "save-add"


def test_button_field_with_empty_value():
    form = F(DummyPostData(a=""))
    assert form.a.raw_data == [""]
    assert form.a.data == ""


def test_button_field_not_pressed():
    form = F(DummyPostData(other="x"))
    assert form.a.raw_data == []
    assert form.a.data is None
