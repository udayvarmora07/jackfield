# Document

How a skill's own text is shown: rendered for reading (`sm-doc`), or exactly as the file holds it (`sm-filetext`).

- **Rendered** (`<div class="sm-doc">`): Markdown shown as a calm reading page — `doc` body (15/25.5), `title-doc` section headings (19/600), lists, inline `code` and code blocks. Keep it under about 760px wide. The skill's name is the page title, so the file's own top heading is not repeated.
- **File text** (`<pre class="sm-filetext">`): every character of SKILL.md, header included, in `file-text` mono — so people can see what the agent really reads. Pair the two with a Segmented switch ("Read / File text").

Mono is allowed here because this is file content, not interface text. Never put interface words, buttons or explanations in mono.
