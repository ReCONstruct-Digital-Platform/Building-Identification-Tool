from dataclasses import dataclass

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


DATASET_OPERATORS = {
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


class DatasetQParser(object):

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
        # Will catch None and empty dict query
        if not query:
            return Q()
        
        if "query" in query:
            query = query["query"]
        rules = query["rules"]
        rules_q_objects = self.parse_rules(rules)
        condition = query["condition"].upper()

        return reduce(CONDITION_LAMBDAS[condition], rules_q_objects)

    def get_q_args(self, rule: dict, operator: Op) -> dict:
        field = rule["field"]

        # Gather values for special operators
        if operator.text == "isnull":
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
            # Special case to check null in JSON field
            elif operator.text == "isnull":
                return {f"{field}": Value("null")}
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

                if rule_operator not in DATASET_OPERATORS:
                    raise NotImplementedError

                operator = DATASET_OPERATORS[rule_operator]

                q_args = self.get_q_args(rule, operator)
                rule_q = Q(**q_args)

                if operator.negated:
                    q_objects.append(~rule_q)
                else:
                    q_objects.append(rule_q)

        return q_objects


# For survey queries, we have different operators for different types
SURVEY_OPERATORS = {
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
        "is_null": Op("contains"),
        "is_not_null": Op("contains", True),
        # For string comparisons
        "ends_with": Op("any_str_like"),
        "begins_with": Op("any_str_like"),
        "not_ends_with": Op("any_str_like", True),
        "not_begins_with": Op("any_str_like", True),
        "contains": Op("any_str_like"),
        "not_contains": Op("any_str_like", True),
    },
}


class SurveyQParser(object):
    """
    For surveys, there is only JSON data.
    We run these queries on JSON objects of key->array of various types
    """

    def __init__(self, prefix="response_data"):

        if prefix:
            self.prefix = prefix + "__"
        else:
            self.prefix = ""

    def parse_query(self, query: dict) -> Q:
        """
        Parse a querybuilder query JSON into an aggregate Q object
        """
        if not query:
            return Q()

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
            operator: Op = SURVEY_OPERATORS[type][rule_operator]
        except KeyError:
            if type not in SURVEY_OPERATORS:
                raise NotImplementedError(f"Unknown type {type}")
            # else key error must have been at the operator level
            raise NotImplementedError(
                f"{rule_operator} not implemented for type {type}"
            )

        if type in ["integer", "boolean"]:
            # Gather values for special cases
            if rule_operator in ["is_null", "is_not_null"]:
                value = Value("null")
            elif operator.text == "range":
                value = (rule["value"][0], rule["value"][1])
            else:
                value = rule["value"]

        elif type == "string":

            # Replace the "in" operators to contains if there is a single value
            if rule_operator in ["in", "not_in"] and len(rule["value"]) == 1:
                operator = Op("contains", operator.negated)

            # If arrays contains null
            if rule_operator in ["is_null", "is_not_null"]:
                value = Value("null")
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

        q_args = {f"{self.prefix}{field}__{operator.text}": value}

        # print(f"Rule {rule} generated Q: {q_args}")

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
