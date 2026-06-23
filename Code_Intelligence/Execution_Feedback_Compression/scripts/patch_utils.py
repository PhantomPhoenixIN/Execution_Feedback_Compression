"""Utilities for compact line-oriented repair patches."""

from __future__ import annotations


class PatchError(ValueError):
    """Raised when a generated patch cannot be parsed or applied."""


def code_lines(code: str) -> list[str]:
    return code.splitlines()


def make_patch_text(diffs: list[dict], fixed_code: str) -> str:
    fixed = code_lines(fixed_code)
    chunks = []
    for diff in diffs:
        op = diff.get("change")
        # The source dataset stores line spans as one-based, end-exclusive
        # positions. The generated patch format uses zero-based, end-exclusive
        # positions so Python list slicing can apply it directly.
        start = max(0, int(diff.get("i1", 1)) - 1)
        end = max(start, int(diff.get("i2", start + 1)) - 1)
        j1 = max(0, int(diff.get("j1", 1)) - 1)
        j2 = max(j1, int(diff.get("j2", j1 + 1)) - 1)
        if op not in {"replace", "insert", "delete"}:
            continue
        chunks.append(f"@@ {op} {start} {end}")
        if op != "delete":
            chunks.extend(fixed[j1:j2])
        chunks.append("@@ end")
    return "\n".join(chunks).strip()


def parse_patch_text(text: str) -> list[dict]:
    lines = text.replace("\r\n", "\n").split("\n")
    hunks = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        parts = line.split()
        if len(parts) != 4 or parts[0] != "@@" or parts[1] not in {"replace", "insert", "delete"}:
            raise PatchError(f"invalid hunk header: {line[:80]}")
        try:
            start = int(parts[2])
            end = int(parts[3])
        except ValueError as exc:
            raise PatchError(f"invalid hunk span: {line[:80]}") from exc
        index += 1
        replacement = []
        while index < len(lines) and lines[index].strip() != "@@ end":
            replacement.append(lines[index])
            index += 1
        if index >= len(lines):
            raise PatchError("missing @@ end")
        index += 1
        hunks.append({"op": parts[1], "start": start, "end": end, "lines": replacement})
    if not hunks:
        raise PatchError("empty patch")
    return hunks


def apply_patch_text(code: str, patch_text: str) -> str:
    lines = code_lines(code)
    hunks = parse_patch_text(patch_text)
    for hunk in sorted(hunks, key=lambda item: item["start"], reverse=True):
        start = hunk["start"]
        end = hunk["end"]
        if start < 0 or end < start or end > len(lines):
            raise PatchError(f"span out of bounds: {start} {end}")
        op = hunk["op"]
        replacement = hunk["lines"]
        if op == "insert" and start != end:
            raise PatchError(f"insert span must be empty: {start} {end}")
        if op == "delete" and replacement:
            raise PatchError("delete hunk cannot contain replacement lines")
        lines[start:end] = replacement
    return "\n".join(lines) + ("\n" if lines else "")
