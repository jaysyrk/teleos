from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import os

Terms = Tuple[str, ...]


@dataclass
class Fact:
    terms: Terms


@dataclass
class Condition:
    terms: Terms
    negated: bool = False


@dataclass
class Rule:
    head: Terms
    conditions: List[Condition]


@dataclass
class Query:
    terms: Terms
    kind: str


@dataclass
class Assert:
    terms: Terms
    expect: bool = True


@dataclass
class _Import:
    path: str


@dataclass
class KnowledgeBase:
    facts: List[Fact] = field(default_factory=list)
    rules: List[Rule] = field(default_factory=list)
    queries: List[Query] = field(default_factory=list)
    asserts: List[Assert] = field(default_factory=list)


def _parse_terms(text: str) -> Terms:
    return tuple(text.strip().split())


def _parse_conditions(text: str) -> List[Condition]:
    parts = [p.strip() for p in text.split(" and ")]
    result: List[Condition] = []
    for p in parts:
        if not p:
            continue
        if p.lower().startswith("not "):
            result.append(Condition(terms=_parse_terms(p[4:]), negated=True))
        else:
            result.append(Condition(terms=_parse_terms(p), negated=False))
    return result


def parse_line(line: str) -> Optional[object]:
    line = line.strip()

    if not line or line.startswith("#"):
        return None

    if ":" not in line:
        return None

    keyword, _, rest = line.partition(":")
    keyword = keyword.strip().lower()
    rest = rest.strip()

    if keyword == "fact":
        return Fact(terms=_parse_terms(rest))

    elif keyword == "rule":
        if " then " not in rest:
            raise ValueError(f"Rule is missing 'then': {line!r}")
        body = rest
        if body.lower().startswith("if "):
            body = body[3:]
        cond_text, _, head_text = body.partition(" then ")
        return Rule(
            head=_parse_terms(head_text),
            conditions=_parse_conditions(cond_text),
        )

    elif keyword == "ask":
        return Query(terms=_parse_terms(rest), kind="ask")

    elif keyword == "why":
        return Query(terms=_parse_terms(rest), kind="why")

    elif keyword == "all":
        return Query(terms=_parse_terms(rest), kind="all")

    elif keyword == "assert":
        negated = rest.lower().startswith("not ")
        body = rest[4:].strip() if negated else rest
        return Assert(terms=_parse_terms(body), expect=not negated)

    elif keyword == "assert not":
        return Assert(terms=_parse_terms(rest), expect=False)

    elif keyword == "import":
        return _Import(path=rest)

    else:
        raise ValueError(
            f"Unknown keyword {keyword!r}. Expected: fact, rule, ask, why, all, assert, assert not, import"
        )


def _load(lines, base_dir: str = "") -> KnowledgeBase:
    kb = KnowledgeBase()
    for lineno, line in enumerate(lines, 1):
        try:
            item = parse_line(line)
        except ValueError as e:
            raise ValueError(f"Line {lineno}: {e}") from e
        if isinstance(item, Fact):
            kb.facts.append(item)
        elif isinstance(item, Rule):
            kb.rules.append(item)
        elif isinstance(item, Query):
            kb.queries.append(item)
        elif isinstance(item, Assert):
            kb.asserts.append(item)
        elif isinstance(item, _Import):
            import_path = item.path if os.path.isabs(item.path) else os.path.join(base_dir, item.path)
            imported = parse_file(import_path)
            kb.facts.extend(imported.facts)
            kb.rules.extend(imported.rules)
            kb.asserts.extend(imported.asserts)
    return kb


def parse_file(path: str) -> KnowledgeBase:
    base_dir = os.path.dirname(os.path.abspath(path))
    with open(path, "r", encoding="utf-8") as f:
        return _load(f, base_dir=base_dir)


def parse_string(text: str, base_dir: str = "") -> KnowledgeBase:
    return _load(text.splitlines(), base_dir=base_dir)
