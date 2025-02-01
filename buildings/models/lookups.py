from pprint import pformat
from django.db.models import Field
from django.db.models import Lookup
from django.db.models.lookups import BuiltinLookup

# From https://github.com/primal100/django_postgres_extensions/blob/bb1edc2cbf194fe571a605595a898b2528918301/django_postgres_extensions/models/lookups.py#L22


class BaseAnyStringLookupMixin(Lookup):

    # jsonb_to_int_array is a custom function that needs to exist in the DB
    # TODO: Create a migration for it
    operators = {
        "any_str_in": "&& %s",
        "any_str_like": "like %s",
    }

    def get_rhs_op(self, _, rhs):
        return self.operators[self.lookup_name] % rhs

    def as_postgresql(self, compiler, connection):
        # Change the order of LHS and RHS for any() queries
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        rhs = self.get_rhs_op(None, rhs)

        params = lhs_params + list(rhs_params)

        if self.lookup_name == "any_str_in":
            lhs = "jsonb_to_text_array(%s)" % lhs
            result = "%s %s" % (lhs, rhs), params

        elif self.lookup_name == "any_str_like":
            result = """exists (
                select from unnest(jsonb_to_text_array(%s)) elem 
                where elem %s )""" % (lhs, rhs), params
        
        # print(f"Result: {pformat(result)}")
        return result

class AnyStringLookupMixin(BaseAnyStringLookupMixin, BuiltinLookup):
    db_func = "any_str"

@Field.register_lookup
class AnyString(AnyStringLookupMixin, BuiltinLookup):
    lookup_name = "any_str_in"

@Field.register_lookup
class AnyStringLike(AnyStringLookupMixin, BuiltinLookup):
    lookup_name = "any_str_like"

class BaseAnyIntLookupMixin(Lookup):

    # jsonb_to_int_array is a custom function that needs to exist in the DB
    # TODO: Create a migration for it
    operators = {
        "any_int": "= any(jsonb_to_int_array(%s))",
        "any_int_exact": "= any(jsonb_to_int_array(%s))",
        # These are inverted since we're asking if the RHS is gt the LHS here
        "any_int_gt": "< any(jsonb_to_int_array(%s))",
        "any_int_gte": "<= any(jsonb_to_int_array(%s))",
        "any_int_lt": "> any(jsonb_to_int_array(%s))",
        "any_int_lte": ">= any(jsonb_to_int_array(%s))",
        # For range operations
        "any_int_range": "@> any(jsonb_to_int_array(%s))",
    }

    def get_rhs_op(self, _, rhs):
        return self.operators[self.lookup_name] % rhs

    def as_postgresql(self, compiler, connection):
        # Change the order of LHS and RHS for any() queries
        lhs, lhs_params = self.process_rhs(compiler, connection)
        rhs, rhs_params = self.process_lhs(compiler, connection)

        rhs = self.get_rhs_op(None, rhs)

        if self.lookup_name == "any_int_range":
            # lhs_params is a list of tuples containing the range
            lhs = "int4range(%s, %s, '[]')"
            lhs_params = [lhs_params[0][0], lhs_params[0][1]]
        
        params = lhs_params + list(rhs_params)

        result = "%s %s" % (lhs, rhs), params
        # print(f"Result: {pformat(result)}")
        return result


class AnyIntLookupMixin(BaseAnyIntLookupMixin, BuiltinLookup):
    db_func = "any_int"


@Field.register_lookup
class Any(AnyIntLookupMixin, BuiltinLookup):
    lookup_name = "any_int"

@Field.register_lookup
class AnyExact(AnyIntLookupMixin, BuiltinLookup):
    lookup_name = "any_int_exact"


@Field.register_lookup
class AnyGreaterThan(AnyIntLookupMixin, BuiltinLookup):
    lookup_name = "any_int_gt"


@Field.register_lookup
class AnyGreaterThanOrEqual(AnyIntLookupMixin, BuiltinLookup):
    lookup_name = "any_int_gte"


@Field.register_lookup
class AnyLessThan(AnyIntLookupMixin, BuiltinLookup):
    lookup_name = "any_int_lt"


@Field.register_lookup
class AnyLessThanOrEqual(AnyIntLookupMixin, BuiltinLookup):
    lookup_name = "any_int_lte"

@Field.register_lookup
class AnyIntRange(AnyIntLookupMixin, BuiltinLookup):
    lookup_name = "any_int_range"