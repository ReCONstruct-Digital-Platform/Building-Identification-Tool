from django import template

from buildings.models.newmodels import Building, Survey

register = template.Library()


@register.filter
def get_attr(obj, attr):
    return getattr(obj, attr)


@register.filter
def has_attr(obj, attr):
    return hasattr(obj, attr)


@register.filter
def get_dict_item(dictionary: dict, key):
    return dictionary.get(key)


@register.filter
def get_bldg_field(building: Building, key):
    if "attrs__" in key:
        return building.attrs[key.replace("attrs__", "")]
    return getattr(building, key)


@register.filter
def sub_lists(l1: list, l2: list):
    r = [o for o in l1 if o not in l2]
    return r


@register.filter
def get_responses_for_survey(building: Building, survey: Survey):
    return building.get_responses_for_survey(survey)


@register.filter
def join_if_list(input):
    if isinstance(input, list):
        return ", ".join(input)
    return input
