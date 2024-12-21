from dataclasses import dataclass

from django.db.models import Q
from functools import reduce
from typing import Callable

"""
Inspired by 
https://hg.sr.ht/~ocurero/sqlalchemy-querybuilder/browse/sqlalchemy_querybuilder/sqlalchemy_querybuilder.py
"""

@dataclass
class Op:
  text: str
  negated: bool = False

# TODO: See date functions
# Will need the schema of attributes ot know when datetime
# https://docs.djangoproject.com/en/5.1/ref/models/querysets/#date


OPERATORS = {
  # We could use the contains json operator for this, as it can use indexes
  # If top-level field, use exact
  # If JSON attrs field, use contains and reshape value as JSON object
  'equal': Op('exact'),
  'not_equal': Op('exact', True),
  'less': Op('lt'),
  'greater': Op('gt'),
  'less_or_equal': Op('lte'),
  'greater_or_equal': Op('gte'),
  'in': Op('in'),
  'not_in': Op('in', True),
  'ends_with': Op('endswith'),
  'begins_with': Op('startswith'),
  'contains': Op('contains'),
  'not_contains': Op('contains', True),
  'is_null': Op('isnull'),
  'is_not_null': Op('isnull', True),
  'not_ends_with': Op('endswith', True),
  'not_begins_with': Op('startswith', True),
  # 'is_empty': lambda f: f.__eq__(''),
  # 'is_not_empty': lambda f: f.__ne__(''),
  # 'between': lambda f, a: f.between(a[0], a[1])
}

CONDITION_LAMBDAS = {
  'OR': lambda a, b: a | b,
  'AND': lambda a, b: a & b
}

TOP_LEVEL_FIELDS = {"address", "muni"}


class QParser(object):

  def __init__(self, schema, top_level_fields, json_field_name = "attrs"):
    self.schema = schema
    self.top_level_fields = set(top_level_fields)
    self.json_field_name = json_field_name

  def parse_query(self, query: dict) -> Q:
    """
    Parse a querybuilder query JSON into an aggregate Q object
    """
    rules = query['rules']
    rules_q_objects = self.parse_rules(rules)
    condition = query['condition'].upper()

    return reduce(CONDITION_LAMBDAS[condition], rules_q_objects)

  def get_q_args(self, rule, operator) -> dict:
    field = rule['field']
    if field in TOP_LEVEL_FIELDS:
      return {
        f"{field}__{operator.text}": rule['value']
      }
    else:
      # Else JSON, with a special case for equal
      if operator.text == "equal":
        json_field, json_inner_field = field.split("_")
        # Optimization to use any GIN indexes
        return {
          f"{json_field}__contains": {json_inner_field: rule['value']}
        }
      else:
        return {
          f"{field}__{operator.text}": rule['value']
        }


    return {}


  def parse_rules(cls, rules: list) -> list[Q]:
    """
    Returns a list of Q objects to be merged at a higher level using the condition
    """
    q_objects = []

    for rule in rules:

      # If a condition is present, we are processing a subquery
      # Recursively parse its rules into Q objects and combine them
      # using the condition
      if 'condition' in rule:
        subquery_q_objects = cls.parse_rules(rule['rules'])
        subquery_condition = rule['condition']
        q_objects.append(
          reduce(CONDITION_LAMBDAS[subquery_condition], subquery_q_objects)
        )

      # If there is no 'condition' field in the current object, we are processing a simple rule
      # Make a Q objects for it and append to the list of Qs
      else:
        rule_operator = rule['operator']

        if rule_operator not in OPERATORS:
          raise NotImplementedError

        q_args = cls.get_q_args(rule, rule_operator)
        rule_q = Q(**q_args)

        if operator.negated:
          q_objects.append(~rule_q)
        else:
          q_objects.append(rule_q)

    return q_objects
