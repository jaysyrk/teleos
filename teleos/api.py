"""
teleos/api.py

Clean public API for using Teleos as a Python library.

    import teleos

    engine = teleos.load("rules.teleos")

    engine.ask("alice can access document")   # → True / False
    engine.why("alice can access document")   # → explanation string
    engine.all("FOOD is safe for alice")      # → ["sushi", "salad"]
    engine.add_fact("dave is admin")          # → add a fact at runtime
"""

from typing import Dict, List, Union

from .engine import Engine, is_variable, apply_sub
from .parser import _parse_terms, parse_file, parse_string, parse_line, Rule, Assert


class Teleos:
    """A loaded Teleos knowledge base, ready to query.

    Create one with:
        teleos.load("path/to/rules.teleos")   # from a file
        teleos.loads("fact: sky is blue ...")  # from a string
    """

    def __init__(self, engine: Engine, asserts=None):
        self._engine = engine
        self._asserts: List[Assert] = asserts or []

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str) -> "Teleos":
        """Load a .teleos file from disk."""
        kb = parse_file(path)
        return cls(Engine(kb), asserts=kb.asserts)

    @classmethod
    def loads(cls, text: str) -> "Teleos":
        """Load a .teleos knowledge base from a string."""
        kb = parse_string(text)
        return cls(Engine(kb), asserts=kb.asserts)

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def ask(self, query: str) -> bool:
        """Return True if the query can be proven.

        Example:
            engine.ask("alice can access document")  # → True
        """
        terms = _parse_terms(query)
        return self._engine.ask(terms)

    def why(self, query: str) -> str:
        """Return a human-readable proof (or explanation of failure).

        Example:
            engine.why("alice can access document")
            # → "'alice can access document' — proven because: ..."
        """
        terms = _parse_terms(query)
        return self._engine.why(terms)

    def all(self, query: str) -> Union[List[str], List[Dict[str, str]]]:
        """Return all solutions to a query containing variables.

        - One variable  → list of strings
        - Many variables → list of dicts mapping variable name to value
        - No variables   → [True] if provable, [] if not

        Examples:
            engine.all("FOOD is safe for alice")
            # → ["sushi", "salad"]

            engine.all("X can access Y")
            # → [{"X": "alice", "Y": "document"}, ...]
        """
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

    # ------------------------------------------------------------------
    # Dynamic updates
    # ------------------------------------------------------------------

    def add_fact(self, fact: str) -> None:
        """Add a fact to the knowledge base at runtime.

        Example:
            engine.add_fact("dave is admin")
        """
        self._engine.add_fact(_parse_terms(fact))

    def add_rule(self, rule_text: str) -> None:
        """Add a rule to the knowledge base at runtime.

        The text should be the part after 'rule:', e.g.:
            engine.add_rule("if X is admin then X can access Y")
        """
        item = parse_line(f"rule: {rule_text}")
        if not isinstance(item, Rule):
            raise ValueError(f"Could not parse as a rule: {rule_text!r}")
        self._engine.add_rule(item)

    def test(self) -> dict:
        """Run all assert: statements loaded from the knowledge base file.

        Returns a dict with keys 'passed', 'failed', and 'results' (list of dicts).

        Example::

            engine = teleos.load("rules.teleos")
            report = engine.test()
            # → {"passed": 3, "failed": 1, "results": [...]}
        """
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

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def facts(self) -> List[str]:
        """Return all current facts as readable strings."""
        return [" ".join(f) for f in self._engine.facts]

    def rules(self) -> List[str]:
        """Return all current rules as readable strings."""
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


# ------------------------------------------------------------------
# Module-level convenience functions
# ------------------------------------------------------------------

def load(path: str) -> Teleos:
    """Load a .teleos file and return a queryable Teleos engine.

    Example:
        import teleos
        engine = teleos.load("rules.teleos")
        engine.ask("alice can access document")
    """
    return Teleos.load(path)


def loads(text: str) -> Teleos:
    """Load a .teleos knowledge base from a string.

    Example:
        import teleos
        engine = teleos.loads('''
            fact: sky is blue
            ask: sky is blue
        ''')
        engine.ask("sky is blue")  # → True
    """
    return Teleos.loads(text)
