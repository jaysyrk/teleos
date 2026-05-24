from typing import Dict, List, Union

from .engine import Engine, is_variable, apply_sub
from .parser import _parse_terms, parse_file, parse_string, parse_line, Rule, Assert


class Teleos:

    def __init__(self, engine: Engine, asserts=None):
        self._engine = engine
        self._asserts: List[Assert] = asserts or []

    @classmethod
    def load(cls, path: str) -> "Teleos":
        kb = parse_file(path)
        return cls(Engine(kb), asserts=kb.asserts)

    @classmethod
    def loads(cls, text: str) -> "Teleos":
        kb = parse_string(text)
        return cls(Engine(kb), asserts=kb.asserts)

    def ask(self, query: str) -> bool:
        terms = _parse_terms(query)
        return self._engine.ask(terms)

    def why(self, query: str) -> str:
        terms = _parse_terms(query)
        return self._engine.why(terms)

    def all(self, query: str) -> Union[List[str], List[Dict[str, str]]]:
        terms = _parse_terms(query)
        solutions = self._engine.all_solutions(terms)
        variables = [t for t in terms if is_variable(t)]

        if not variables:
            return [True] if solutions else []

        result = []
        for sol in solutions:
            binding = {
                orig: resolved
                for orig, resolved in zip(terms, sol)
                if is_variable(orig)
            }
            result.append(binding)

        if len(variables) == 1:
            var = variables[0]
            return [b[var] for b in result]

        return result

    def add_fact(self, fact: str) -> None:
        self._engine.add_fact(_parse_terms(fact))

    def add_rule(self, rule_text: str) -> None:
        item = parse_line(f"rule: {rule_text}")
        if not isinstance(item, Rule):
            raise ValueError(f"Could not parse as a rule: {rule_text!r}")
        self._engine.add_rule(item)

    def test(self) -> dict:
        results = []
        for assertion in self._asserts:
            goal_str = " ".join(assertion.terms)
            actual = self._engine.ask(assertion.terms)
            passed = actual == assertion.expect
            results.append({
                "goal": goal_str,
                "expected": assertion.expect,
                "actual": actual,
                "passed": passed,
                "why": self._engine.why(assertion.terms) if not passed else None,
            })
        passed_count = sum(1 for r in results if r["passed"])
        return {
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "results": results,
        }

    def facts(self) -> List[str]:
        return [" ".join(f) for f in self._engine.facts]

    def rules(self) -> List[str]:
        result = []
        for rule in self._engine.rules:
            conds = []
            for c in rule.conditions:
                text = " ".join(c.terms)
                conds.append(f"not {text}" if c.negated else text)
            head = " ".join(rule.head)
            result.append("if " + " and ".join(conds) + " then " + head)
        return result

    def __repr__(self) -> str:
        return (
            f"<Teleos {len(self._engine.facts)} facts, "
            f"{len(self._engine.rules)} rules>"
        )


def load(path: str) -> Teleos:
    return Teleos.load(path)


def loads(text: str) -> Teleos:
    return Teleos.loads(text)
