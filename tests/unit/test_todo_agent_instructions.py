from __future__ import annotations

import ast
from pathlib import Path


def _get_module_constant_string(module_path: str, constant_name: str) -> str:
    tree = ast.parse(Path(module_path).read_text(encoding="utf-8"))

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == constant_name:
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value

    raise AssertionError(f"Could not find string constant {constant_name!r} in {module_path}")


def test_create_instructions_include_description_argument() -> None:
    instructions = _get_module_constant_string(
        "src/agents/todo_agent.py", "TODO_AGENT_INSTRUCTIONS"
    )

    assert "Description Extraction" in instructions
    assert "call create_todo with extracted: title, description (optional)" in instructions

