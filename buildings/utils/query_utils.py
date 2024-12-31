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

OPERATORS = {
    # We could use the contains json operator for this, as it can use indexes
    # If top-level field, use exact
    # If JSON attrs field, use contains and reshape value as JSON object
    "equal": Op("exact"),
    "not_equal": Op("exact", True),
    "less": Op("lt"),
    "greater": Op("gt"),
    "less_or_equal": Op("lte"),
    "greater_or_equal": Op("gte"),
    "contains": Op("contains"),
    "not_contains": Op("contains", True),
    "is_null": Op("isnull"),
    "is_not_null": Op("isnull", True),
    "ends_with": Op("endswith"),
    "begins_with": Op("startswith"),
    "not_ends_with": Op("endswith", True),
    "not_begins_with": Op("startswith", True),
    "in": Op("in"),
    "not_in": Op("not_in", True),
    # Special cases
    "between": Op("range"),
    "not_between": Op("range", True),
}

CONDITION_LAMBDAS = {"OR": lambda a, b: a | b, "AND": lambda a, b: a & b}


class QParser(object):

    def __init__(self, schema, json_field_name="attrs"):
        self.schema = schema
        self.json_field_name = json_field_name
        self.top_level_fields = self._get_top_level_fields(schema)

    def _get_top_level_fields(self, fields):
        top_level_fields = set()
        for field in fields:
            if field["field"].startswith(self.json_field_name):
                continue
            top_level_fields.add(field["field"])
        return top_level_fields

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

    def get_q_args(self, rule: dict, operator: Op) -> dict:
        field = rule["field"]

        # Gather values for special operators
        if operator.text == "null":
            value = True
        elif operator.text == "range":
            value = (rule["value"][0], rule["value"][1])
        else:
            value = rule["value"]

        # Top-level fields are column fields in SQL
        if field in self.top_level_fields:
            return {f"{field}__{operator.text}": value}
        # Non top-level fields are JSON attributes
        else:
            # Optimization for JSON exact lookups that can use a GIN index
            if operator.text == "equal":
                json_field, json_inner_field = field.split("_")
                return {f"{json_field}__contains": {json_inner_field: rule["value"]}}
            else:
                return {f"{field}__{operator.text}": value}

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
                rule_operator = rule["operator"]

                if rule_operator not in OPERATORS:
                    raise NotImplementedError

                operator = OPERATORS[rule_operator]

                q_args = self.get_q_args(rule, operator)
                rule_q = Q(**q_args)

                if operator.negated:
                    q_objects.append(~rule_q)
                else:
                    q_objects.append(rule_q)

        return q_objects
