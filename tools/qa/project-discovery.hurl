# The Workspaces observation and the scoped Library agree on the project.
GET {{base}}/api/workspaces
[QueryStringParams]
project: {{project}}
HTTP 200
[Asserts]
jsonpath "$.project.status" == "accepted"
jsonpath "$.project.skills_roots[?(@.relative == '.gemini/skills')].exists" == true
jsonpath "$.project.skills_roots[?(@.relative == '.commandcode/skills')].exists" == true

GET {{base}}/api/skills?scope=project-gemini
HTTP 200
[Asserts]
jsonpath "$[0].name" == "gemini-fixture"

GET {{base}}/api/skills/command-fixture?scope=project-commandcode
HTTP 200
[Asserts]
jsonpath "$.name" == "command-fixture"

GET {{base}}/api/doctor
[QueryStringParams]
project: {{project}}
explain: gemini
skill: direct-fixture
HTTP 200
[Asserts]
jsonpath "$.explain.skills['direct-fixture'].winner.read_only" == true
jsonpath "$.explain.skills['direct-fixture'].winner.path" endsWith "SKILL.md"
