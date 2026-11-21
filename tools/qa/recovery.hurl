# A scoped restore of the skill named purge must leave another skill in trash.
DELETE {{base}}/api/skills/recovery-fixture?scope=global
HTTP 200
[Asserts]
jsonpath "$.action" == "trashed"

DELETE {{base}}/api/skills/purge?scope=global
HTTP 200
[Asserts]
jsonpath "$.action" == "trashed"

GET {{base}}/api/trash?scope=global
HTTP 200
[Asserts]
jsonpath "$" count == 2
jsonpath "$[?(@.name == 'purge')]" exists

POST {{base}}/api/trash/purge?scope=global
Content-Type: application/json
{}
HTTP 200
[Asserts]
jsonpath "$.name" == "purge"
jsonpath "$.restored_from" exists

GET {{base}}/api/skills/purge?scope=global
HTTP 200
[Asserts]
jsonpath "$.body" contains "Recovered fixture."

GET {{base}}/api/trash?scope=global
HTTP 200
[Asserts]
jsonpath "$" count == 1
jsonpath "$[0].name" == "recovery-fixture"
