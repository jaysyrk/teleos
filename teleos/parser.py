"""
teleos/parser.py

Reads .teleos files and turns them into Python data structures.

A .teleos file has three kinds of lines:
  fact: sky is blue
  rule: if X is a bird and X has wings then X can fly
  ask:  eagle can fly
  why:  eagle can fly

Variables are ALL UPPERCASE (X, Y, ANIMAL).
Everything else is a constant (eagle, is, a, bird, ...).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import os

# A Terms is a tuple of words, e.g. ("eagle", "is", "a", "bird")
Terms = Tuple[str, ...]


@dataclass
class Fact:
    """A thing that is simply true. e.g. 'eagle is a bird'"""
    terms: Terms


@dataclass
class Condition:
    """One condition inside a rule. Set negated=True for 'not X is Y' conditions."""
    terms: Terms
    negated: bool = False


@dataclass
class Rule:
    """IF [conditions] THEN [head]. e.g. if X is a bird and X has wings then X can fly"""
    head: Terms
    conditions: List[Condition]


@dataclass
class Query:
    """A question to ask the engine. kind is 'ask' or 'why'."""
    terms: Terms
    kind: str  # "ask" or "why"


@dataclass
class Assert:
    """An assertion to verify during 'teleos test'. expect=True means the goal must be provable."""
    terms: Terms
    expect: bool = True  # True = must be provable, False = must NOT be provable


@dataclass
class _Import:
    """Internal sentinel returned by parse_line for import: lines."""
    path: str


@dataclass
class KnowledgeBase:
    """Everything parsed from a .teleos file."""
    facts: List[Fact] = field(default_factory=list)
    rules: List[Rule] = field(default_factory=list)
    queries: List[Query] = field(default_factory=list)
    asserts: List[Assert] = field(default_factory=list)


def _parse_terms(text: str) -> Terms:
    return tuple(text.strip().split())


def _parse_conditions(text: str) -> List[Condition]:
    """Split 'X is hot and not X is wet' into a list of Condition objects.

    Conditions starting with 'not ' become negated=True.
    """
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
    """Parse a single line. Returns a Fact, Rule, Query, or None."""
    line = line.strip()

    # Blank lines and comments
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
        # "assert: alice can access document"      → expect True
        # "assert: not charlie can access document" → expect False
        negated = rest.lower().startswith("not ")
        body = rest[4:].strip() if negated else rest
        return Assert(terms=_parse_terms(body), expect=not negated)

    elif keyword == "assert not":
        # "assert not: charlie can access document" → expect False
        return Assert(terms=_parse_terms(rest), expect=False)

    elif keyword == "import":
        # "import: base-rules.teleos" — handled at load time, not here
        # Return a sentinel so _load can resolve the path
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
            # Resolve relative to the current file's directory
            import_path = item.path if os.path.isabs(item.path) else os.path.join(base_dir, item.path)
            imported = parse_file(import_path)
            # Merge facts, rules, asserts — but NOT queries (keep queries local)
            kb.facts.extend(imported.facts)
            kb.rules.extend(imported.rules)
            kb.asserts.extend(imported.asserts)
    return kb


def parse_file(path: str) -> KnowledgeBase:
    """Read a .teleos file from disk and return a KnowledgeBase."""
    base_dir = os.path.dirname(os.path.abspath(path))
    with open(path, "r", encoding="utf-8") as f:
        return _load(f, base_dir=base_dir)


def parse_string(text: str, base_dir: str = "") -> KnowledgeBase:
    """Parse a .teleos string directly (useful for embedding Teleos in code)."""
    return _load(text.splitlines(), base_dir=base_dir)
