# The lightweight library response preserves the full record's identity.
GET {{base}}/api/skills?scope=global&body=0&q=library-fixture
HTTP 200
[Asserts]
jsonpath "$[0].name" == "library-fixture"
jsonpath "$[0].body" not exists

GET {{base}}/api/skills/library-fixture?scope=global
HTTP 200
[Asserts]
jsonpath "$.name" == "library-fixture"
jsonpath "$.body" contains "Synthetic body."
