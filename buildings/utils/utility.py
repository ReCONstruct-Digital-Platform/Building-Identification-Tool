
from django.http import QueryDict


def print_query_dict(data: QueryDict):
    print('QueryDict: {')
    for l in data.lists():
        print(f'\t{l[0]}: {l[1]},')
    print('}')

