# The state survives multiple HTTP reads and can be reversed in the fixture.
POST {{base}}/api/skills/toggle-fixture/disable?scope=global
Content-Type: application/json
{}
HTTP 200
[Asserts]
jsonpath "$.disable" == true

GET {{base}}/api/skills/toggle-fixture?scope=global
HTTP 200
[Asserts]
jsonpath "$.disabled" == 1

POST {{base}}/api/skills/toggle-fixture/enable?scope=global
Content-Type: application/json
{}
HTTP 200
[Asserts]
jsonpath "$.enable" == true

GET {{base}}/api/skills/toggle-fixture?scope=global
HTTP 200
[Asserts]
jsonpath "$.disabled" == 0
