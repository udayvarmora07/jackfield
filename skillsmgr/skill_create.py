"""Canonical text for skill creation and its read-only form preview."""

from .errors import StoreError
from .frontmatter import dump_frontmatter
from .validator import MAX_COMPATIBILITY, MAX_DESCRIPTION, validate_skill_name


def new_skill_fields(name: str, description: str, compatibility: str | None) -> tuple[str, str]:
    try:
        name = validate_skill_name(name.strip())
    except ValueError as exc:
        raise StoreError(str(exc)) from exc
    description = (description or "").strip()
    if not description:
        raise StoreError("description is required")
    if len(description) > MAX_DESCRIPTION:
        raise StoreError(f"description exceeds {MAX_DESCRIPTION} characters")
    if compatibility and len(compatibility) > MAX_COMPATIBILITY:
        raise StoreError(f"compatibility exceeds {MAX_COMPATIBILITY} characters")
    return name, description


def new_skill_document(
    name: str, description: str, *, license=None, category=None, compatibility=None,
    version=None, allowed_tools=None, metadata_extra=None, body=None, normalize_tools=False,
) -> str:
    data = {"name": name, "description": description}
    for key, value in (("license", license), ("compatibility", compatibility), ("version", version)):
        if value:
            data[key] = value
    if allowed_tools:
        if isinstance(allowed_tools, str):
            allowed_tools = allowed_tools.strip()
        elif normalize_tools and isinstance(allowed_tools, (list, tuple)):
            allowed_tools = [tool.strip() for tool in allowed_tools if str(tool).strip()]
        data["allowed-tools"] = allowed_tools
    metadata = dict(metadata_extra or {})
    if category:
        metadata["category"] = category
    if metadata:
        data["metadata"] = metadata
    if body is None:
        body = f"# {name}\n"
    if not body.endswith("\n"):
        body += "\n"
    return dump_frontmatter(data) + body
