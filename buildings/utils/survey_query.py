from dataclasses import dataclass
from pprint import pformat

from django.db.models import Q, Value
from functools import reduce

"""
Inspired by 
https://hg.sr.ht/~ocurero/sqlalchemy-querybuilder/browse/sqlalchemy_querybuilder/sqlalchemy_querybuilder.py
"""


@dataclass
class Op:
    text: str
    negated: bool = False


# Different operators for different types
OPERATORS = {
    "integer": {
        "equal": Op("any_int"),
        "not_equal": Op("any_int", True),
        # For integer fields
        "less": Op("any_int_lt"),
        "greater": Op("any_int_gt"),
        "less_or_equal": Op("any_int_lte"),
        "greater_or_equal": Op("any_int_gte"),
        # Special cases
        "between": Op("any_int_range"),
        "not_between": Op("any_int_range", True),
        "is_null": Op("contains"),
        "is_not_null": Op("contains", True),
    },
        "boolean": {
        "in": Op("contains"),
        "is_null": Op("contains"),
        "is_not_null": Op("contains", True),
    },
    "string": {
        # For in/not_in - Can be overwritten by parser below when there is a single value
        "in": Op("any_str_in"),
        "not_in": Op("any_str_in", True),
        # 
        "is_null": Op("contains"),
        "is_not_null": Op("contains", True),
        # For string comparisons
        "ends_with": Op("any_str_like"),
        "begins_with": Op("any_str_like"),
        "not_ends_with": Op("any_str_like", True),
        "not_begins_with": Op("any_str_like", True),
        "contains": Op("any_str_like"),
        "not_contains": Op("any_str_like", True),
    }
}

CONDITION_LAMBDAS = {"OR": lambda a, b: a | b, "AND": lambda a, b: a & b}


class SurveyQParser(object):
    """
    For surveys, there is only JSON data.
    We run these queries on JSON objects of key->array of various types
    """

    def __init__(self, json_field_name="response_data"):
        self.json_field_name = json_field_name

    def parse_query(self, query: dict) -> Q:
        """
        Parse a querybuilder query JSON into an aggregate Q object
        """
        if "query" in query:
            query = query["query"]
        rules = query["rules"]
        rules_q_objects = self.parse_rules(rules)
        condition = query["condition"].upper()

        return reduce(CONDITION_LAMBDAS[condition], rules_q_objects)

    def get_q(self, rule: dict) -> dict:

        field = rule["id"]
        type = rule["type"]
        rule_operator = rule["operator"]

        try:
            operator: Op = OPERATORS[type][rule_operator]
        except KeyError:
            raise NotImplementedError(f"{rule_operator} not implemented for type {type}")

        if type in ['integer', 'boolean']:
            # Gather values for special cases
            if rule_operator == "is_null":
                value = Value('null')
            elif operator.text == "range":
                value = (rule["value"][0], rule["value"][1])
            else:
                value = rule["value"]

        elif type == "string":
            # Rewrite the in operator's text if there is a single value
            if rule_operator == 'in' and len(rule['value']) == 1:
                operator.text = 'contains'
            
            # If arrays contains null
            if rule_operator == "is_null":
                value = Value('null')
            # Add the wildcard character to the value for string lookups
            elif "contains" in rule_operator:
                value = f"%{rule['value']}%"
            elif "begins" in rule_operator:
                value = f"{rule['value']}%"
            elif "end" in rule_operator:
                value = f"%{rule['value']}"
            else:
                value = rule["value"]

        else:
            raise NotImplementedError(f"Unkown type {type}")


        q_args = {f"{self.json_field_name}__{field}__{operator.text}": value}

        print(f"Rule {rule} generated Q: {q_args}")
        
        if operator.negated:
            return ~Q(**q_args)
        return Q(**q_args)

    def parse_rules(self, rules: list) -> list[Q]:
        """
        Returns a list of Q objects to be merged at a higher level using a condition
        """
        q_objects = []

        for rule in rules:
            # If a condition is present, we are processing a subquery
            # Recursively parse its rules into Q objects and combine them
            # using the condition
            if "condition" in rule:
                subquery_q_objects = self.parse_rules(rule["rules"])
                subquery_condition = rule["condition"]
                q_objects.append(
                    reduce(CONDITION_LAMBDAS[subquery_condition], subquery_q_objects)
                )

            # If there is no 'condition' field in the current object, we are processing a simple rule
            # Make a Q object for it and append to the list of Q objects at the current level
            else:
                rule_q = self.get_q(rule)

                q_objects.append(rule_q)

        return q_objects
