import warnings
from dataclasses import dataclass
from typing import Optional

from wtforms import widgets
from wtforms.fields.core import Field
from wtforms.validators import ValidationError

__all__ = (
    "SelectField",
    "Choice",
    "SelectMultipleField",
    "RadioField",
)


@dataclass
class Choice:
    """
    A dataclass that represents available choices for
    :class:`RadioField`, :class:`SelectField` and :class:`SelectMultipleField`

    :param value:
        The value that will be send in the request.
    :param label:
        The label of the option.
    :param render_kw:
        A dict containing HTML attributes that will be rendered
        with the option.
    :param optgroup:
        The `<optgroup>` HTML tag in which the option will be
        rendered.
    """

    value: str
    label: Optional[str] = None
    render_kw: Optional[dict] = None
    optgroup: Optional[str] = None
    _selected: bool = False

    @classmethod
    def from_input(cls, input, optgroup=None):
        if isinstance(input, Choice):
            if optgroup:
                input.optgroup = optgroup
            return input

        if isinstance(input, str):
            return Choice(value=input, optgroup=optgroup)

        if isinstance(input, tuple):
            warnings.warn(
                "Passing SelectField choices as tuples is deprecated and will be "
                "removed in wtforms 3.3. Please use Choice instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return Choice(*input, optgroup=optgroup)


class SelectFieldBase(Field):
    option_widget = widgets.Option()

    """
    Base class for fields which can be iterated to produce options.

    This isn't a field, but an abstract base class for fields which want to
    provide this functionality.
    """

    def __init__(self, label=None, validators=None, option_widget=None, **kwargs):
        super().__init__(label, validators, **kwargs)

        if option_widget is not None:
            self.option_widget = option_widget

    def iter_choices(self):
        """
        Provides data for choice widget rendering. Must return a sequence or
        iterable of Choice.
        """
        raise NotImplementedError()

    def __iter__(self):
        opts = dict(
            widget=self.option_widget,
            validators=self.validators,
            name=self.name,
            render_kw=self.render_kw,
            _form=None,
            _meta=self.meta,
        )
        for i, choice in enumerate(self.iter_choices()):
            opt = self._Option(
                id="%s-%d" % (self.id, i), label=choice.label or choice.value, **opts
            )
            opt.choice = choice
            opt.checked = choice._selected
            opt.process(None, choice.value)
            yield opt

    def choices_from_input(self, choices):
        if callable(choices):
            choices = choices()

        if choices is None:
            return None

        if isinstance(choices, dict):
            warnings.warn(
                "Passing SelectField choices in a dict deprecated and will be removed "
                "in wtforms 3.3. Please pass a list of Choice objects with a "
                "custom optgroup attribute instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            print(
                [
                    Choice.from_input(input, optgroup)
                    for optgroup, inputs in choices.items()
                    for input in inputs
                ]
            )

            return [
                Choice.from_input(input, optgroup)
                for optgroup, inputs in choices.items()
                for input in inputs
            ]

        return [Choice.from_input(input) for input in choices]

    class _Option(Field):
        def _value(self):
            return str(self.data)


class SelectField(SelectFieldBase):
    widget = widgets.Select()

    def __init__(
        self,
        label=None,
        validators=None,
        coerce=str,
        choices=None,
        validate_choice=True,
        **kwargs,
    ):
        super().__init__(label, validators, **kwargs)
        self.coerce = coerce
        self.choices = self.choices_from_input(choices)
        self.validate_choice = validate_choice

    def iter_choices(self):
        choices = self.choices_from_input(self.choices) or []
        for choice in choices:
            choice._selected = self.coerce(choice.value) == self.data
        return choices

    def process_data(self, value):
        try:
            # If value is None, don't coerce to a value
            self.data = self.coerce(value) if value is not None else None
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        try:
            self.data = self.coerce(valuelist[0])
        except ValueError as exc:
            raise ValueError(self.gettext("Invalid Choice: could not coerce.")) from exc

    def pre_validate(self, form):
        if self.choices is None:
            raise TypeError(self.gettext("Choices cannot be None."))

        if not self.validate_choice:
            return

        if not any(choice._selected for choice in self.iter_choices()):
            raise ValidationError(self.gettext("Not a valid choice."))


class SelectMultipleField(SelectField):
    """
    No different from a normal select field, except this one can take (and
    validate) multiple choices.  You'll need to specify the HTML `size`
    attribute to the select field when rendering.
    """

    widget = widgets.Select(multiple=True)

    def iter_choices(self):
        choices = self.choices_from_input(self.choices) or []
        if self.data:
            for choice in choices:
                choice._selected = self.coerce(choice.value) in self.data
        return choices

    def process_data(self, value):
        try:
            self.data = list(self.coerce(v) for v in value)
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        try:
            self.data = list(self.coerce(x) for x in valuelist)
        except ValueError as exc:
            raise ValueError(
                self.gettext(
                    "Invalid choice(s): one or more data inputs could not be coerced."
                )
            ) from exc

    def pre_validate(self, form):
        if self.choices is None:
            raise TypeError(self.gettext("Choices cannot be None."))

        if not self.validate_choice or not self.data:
            return

        acceptable = {self.coerce(choice.value) for choice in self.iter_choices()}
        if any(d not in acceptable for d in self.data):
            unacceptable = [str(d) for d in set(self.data) - acceptable]
            raise ValidationError(
                self.ngettext(
                    "'%(value)s' is not a valid choice for this field.",
                    "'%(value)s' are not valid choices for this field.",
                    len(unacceptable),
                )
                % dict(value="', '".join(unacceptable))
            )


class RadioField(SelectField):
    """
    Like a SelectField, except displays a list of radio buttons.

    Iterating the field will produce subfields (each containing a label as
    well) in order to allow custom rendering of the individual radio fields.
    """

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()
