
from django.db.models import Q
from django.test import TestCase
from buildings.utils.query_utils import QParser

data = {
  "query": {
    "condition": "AND",
    "rules": [
      {
        "id": "1",
        "field": "my_field",
        "type": "string",
        "input": "text",
        "operator": "equal",
        "value": "blabla"
      },
      {
        "id": "2",
        "field": "my_second_field",
        "type": "integer",
        "input": "number",
        "operator": "not_equal",
        "value": 4
      },
      {
        "condition": "OR",
        "rules": [
          {
            "id": "1",
            "field": "my_third_field",
            "type": "string",
            "input": "text",
            "operator": "equal",
            "value": "as"
          },
          {
            "id": "2",
            "field": "my_fourth_field",
            "type": "integer",
            "input": "number",
            "operator": "equal",
            "value": 1
          }
        ]
      }
    ],
    "valid": True
  }
}

class QParserTest(TestCase):

  def test_query_builder_parser(self):
    result = QParser.parse_query(data['query'])
    print(result)
    assert isinstance(result, Q)


