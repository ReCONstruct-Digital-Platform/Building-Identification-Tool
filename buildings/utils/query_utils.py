from dataclasses import dataclass

from django.db.models import Q
from functools import reduce

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


class QParser(object):

  @classmethod
  def parse_query(cls, query: dict) -> Q:
    """
    Parse a querybuilder query JSON into an aggregate Q object
    """
    rules = query['rules']
    rules_q_objects = cls.parse_rules(rules)
    condition = query['condition'].upper()

    return reduce(CONDITION_LAMBDAS[condition], rules_q_objects)


  @classmethod
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

        operator: Op = OPERATORS[rule_operator]
        rule_q = Q(**{
          f"{rule['field']}__{operator.text}": rule['value']
        })

        if operator.negated:
          q_objects.append(~rule_q)
        else:
          q_objects.append(rule_q)

    return q_objects
