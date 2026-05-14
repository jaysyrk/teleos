"""
teleos/engine.py

The logic brain of Teleos.

Uses BACKWARD CHAINING — instead of going forward from all facts,
we start from your question and work backwards:

  "Can eagle fly?"
    → Is there a rule whose conclusion matches "X can fly"?
    → Yes: "if X is a bird and X has wings then X can fly"
    → Set X = eagle. Now prove: "eagle is a bird" AND "eagle has wings"
    → Both are facts. Done. TRUE.

This naturally builds a proof tree so we can answer "why?" too.

VARIABLES are all-uppercase terms (X, Y, ANIMAL).
Everything else is a constant (eagle, is, a, bird...).
"""

from typing import Dict, Iterator, List, Optional, Tuple
import operator as _op

from .parser import Condition, KnowledgeBase, Rule, Terms

Substitution = Dict[str, str]

# Built-in numeric comparison operators.
# A condition matching (LEFT, OP, RIGHT) where OP is in this dict is evaluated
# directly as a number comparison instead of being looked up in facts/rules.
_COMPARISON_OPS = {
    ">": _op.gt,
    "<": _op.lt,
    ">=": _op.ge,
    "<=": _op.le,
    "=": _op.eq,
    "!=": _op.ne,
}


# ---------------------------------------------------------------------------
# Variable helpers
# ---------------------------------------------------------------------------

def is_variable(term: str) -> bool:
    """Return True if this term is a variable (ALL CAPS, letters only).

    We also strip the '$N' suffix that rename_vars adds, so renamed
    variables like 'X$0' are still recognised as variables.
    """
    base = term.split("$")[0]
    return bool(base) and base.isalpha() and base.isupper()


def resolve(term: str, sub: Substitution) -> str:
    """Follow a chain of variable substitutions to find the concrete value."""
    seen: set = set()
    while term in sub and term not in seen:
        seen.add(term)
        term = sub[term]
    return term


def apply_sub(terms: Terms, sub: Substitution) -> Terms:
    """Replace every variable in `terms` with its value from `sub`."""
    return tuple(resolve(t, sub) for t in terms)


def unify(t1: Terms, t2: Terms, sub: Substitution) -> Optional[Substitution]:
    """Try to match two term sequences, extending substitution `sub`.

    Returns a new substitution if successful, or None if impossible.
    Example:
      unify(("X", "is", "a", "bird"), ("eagle", "is", "a", "bird"), {})
      → {"X": "eagle"}
    """
    if len(t1) != len(t2):
        return None
    result = dict(sub)
    for a, b in zip(t1, t2):
        a = resolve(a, result)
        b = resolve(b, result)
        if a == b:
            continue
        elif is_variable(a):
            result[a] = b
        elif is_variable(b):
            result[b] = a
        else:
            return None  # Two different constants — no match
    return result


def rename_vars(terms: Terms, tag: int) -> Terms:
    """Add a unique tag to every variable so rules don't clash with each other.

    e.g. rename_vars(("X", "is", "a", "bird"), 2) → ("X$2", "is", "a", "bird")
    """
    return tuple(f"{t}${tag}" if is_variable(t) else t for t in terms)


def rename_condition(cond: Condition, tag: int) -> Condition:
    """Rename variables inside a condition's terms."""
    return Condition(terms=rename_vars(cond.terms, tag), negated=cond.negated)


# ---------------------------------------------------------------------------
# Proof tree — used by `why:`
# ---------------------------------------------------------------------------

class ProofNode:
    """One node in the explanation tree."""

    def __init__(self, conclusion: Terms, reason: str, children: List["ProofNode"] = None):
        self.conclusion = conclusion
        self.reason = reason        # "fact" or "rule"
        self.children: List[ProofNode] = children or []

    def explain(self, depth: int = 0) -> str:
        pad = "  " * depth
        text = " ".join(self.conclusion)
        if self.reason == "fact":
            return f"{pad}'{text}' — known fact"
        if self.reason == "negation":
            return f"{pad}'not {text}' — cannot be proven (closed-world)"
        if self.reason == "comparison":
            return f"{pad}'{text}' — numeric comparison"
        lines = [f"{pad}'{text}' — proven because:"]
        for child in self.children:
            lines.append(child.explain(depth + 1))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class Engine:
    """The Teleos inference engine.

    Usage:
        from teleos import parse_file, Engine
        kb = parse_file("rules.teleos")
        engine = Engine(kb)
        engine.ask(("eagle", "can", "fly"))  # True
        print(engine.why(("eagle", "can", "fly")))
    """

    MAX_DEPTH = 30  # prevent infinite loops from circular rules

    def __init__(self, kb: KnowledgeBase):
        self.facts: List[Terms] = [f.terms for f in kb.facts]
        self.rules: List[Rule] = list(kb.rules)
        self._counter = 0  # unique tag per rule application

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ask(self, goal: Terms) -> bool:
        """Return True if `goal` can be proven from the current knowledge base."""
        return self._prove(goal, {}, 0) is not None

    def why(self, goal: Terms) -> str:
        """Return a human-readable explanation of why `goal` is true (or why not)."""
        result = self._prove(goal, {}, 0)
        if result is None:
            return self._explain_failure(goal)
        _, tree = result
        return tree.explain()

    def add_fact(self, terms: Terms) -> None:
        """Dynamically add a fact at runtime."""
        self.facts.append(terms)

    def add_rule(self, rule: Rule) -> None:
        """Dynamically add a rule at runtime."""
        self.rules.append(rule)

    def all_solutions(self, goal: Terms) -> List[Terms]:
        """Return every unique concrete instantiation of goal that can be proven.

        Example:
            engine.all_solutions(("X", "can", "access", "report"))
            → [("alice", "can", "access", "report"), ("bob", "can", "access", "report")]
        """
        seen: set = set()
        results: List[Terms] = []
        for sub, _ in self._prove_all(goal, {}, 0):
            concrete = apply_sub(goal, sub)
            if concrete not in seen:
                seen.add(concrete)
                results.append(concrete)
        return results

    # ------------------------------------------------------------------
    # Internal: backward chaining (generator-based)
    # ------------------------------------------------------------------
    #
    # _prove_all yields EVERY solution, not just the first.
    # _prove (used by ask/why) just takes the first one.
    # This lets all_solutions() collect every answer.

    def _fresh_tag(self) -> int:
        """Each rule application gets a unique variable tag to avoid collisions."""
        self._counter += 1
        return self._counter

    def _prove(self, goal: Terms, sub: Substitution, depth: int) -> Optional[Tuple[Substitution, ProofNode]]:
        """Return the first proof of goal, or None."""
        return next(iter(self._prove_all(goal, sub, depth)), None)

    def _explain_failure(self, goal: Terms) -> str:
        """Explain WHY a goal cannot be proven.

        Finds the rule that got furthest before failing and pinpoints
        the exact condition that blocked it, including a full proof of
        any negation that was responsible for the block.
        """
        concrete = apply_sub(goal, {})
        goal_text = " ".join(concrete)

        # Track the best (most conditions satisfied) failed attempt
        best_passed = -1
        best_msg = ""
        best_blocker: Optional[ProofNode] = None

        for rule in self.rules:
            tag = self._fresh_tag()
            head = rename_vars(rule.head, tag)
            conds = [rename_condition(c, tag) for c in rule.conditions]

            sub = unify(concrete, head, {})
            if sub is None:
                continue  # rule head doesn't even match the goal shape

            passed = 0
            current_sub = sub
            fail_msg = None
            blocker: Optional[ProofNode] = None

            for cond in conds:
                if cond.negated:
                    # Negation fails when the positive form IS provable
                    pos = next(iter(self._prove_all(cond.terms, current_sub, 0)), None)
                    if pos is not None:
                        _, proof = pos
                        neg_text = " ".join(apply_sub(cond.terms, current_sub))
                        fail_msg = f"'not {neg_text}' is blocked — it CAN be proven:"
                        blocker = proof
                        break
                    # Negation succeeds — carry on
                    passed += 1
                else:
                    pos = next(iter(self._prove_all(cond.terms, current_sub, 0)), None)
                    if pos is None:
                        cond_text = " ".join(apply_sub(cond.terms, current_sub))
                        fail_msg = f"'{cond_text}' cannot be proven"
                        break
                    current_sub, _ = pos
                    passed += 1

            if fail_msg is None:
                continue  # rule fully succeeded — shouldn't happen if _prove returned None

            if passed > best_passed:
                best_passed = passed
                best_msg = fail_msg
                best_blocker = blocker

        if best_passed == -1:
            return f"Cannot prove: {goal_text}\n  No matching rules or facts found."

        lines = [f"Cannot prove: {goal_text}"]
        lines.append(f"  Nearest rule failed because: {best_msg}")
        if best_blocker is not None:
            for line in best_blocker.explain(depth=2).splitlines():
                lines.append(line)
        return "\n".join(lines)

    def _prove_all(
        self,
        goal: Terms,
        sub: Substitution,
        depth: int,
    ) -> Iterator[Tuple[Substitution, ProofNode]]:
        """Yield every (substitution, proof) for goal. Enables all_solutions()."""
        if depth > self.MAX_DEPTH:
            return

        concrete = apply_sub(goal, sub)

        # Built-in: numeric comparison  e.g. ("S", ">", "80")
        if len(concrete) == 3 and concrete[1] in _COMPARISON_OPS:
            left, op, right = concrete
            try:
                if _COMPARISON_OPS[op](float(left), float(right)):
                    yield sub, ProofNode(concrete, "comparison")
            except (ValueError, TypeError):
                pass  # non-numeric terms — fall through to fact/rule lookup
            return

        # Try facts — each matching fact is one solution
        for fact in self.facts:
            new_sub = unify(concrete, fact, sub)
            if new_sub is not None:
                yield new_sub, ProofNode(apply_sub(goal, new_sub), "fact")

        # Try rules — each rule that fully succeeds is one solution
        for rule in self.rules:
            # Fresh tag so variables in this rule never alias other rules
            tag = self._fresh_tag()
            head = rename_vars(rule.head, tag)
            conds = [rename_condition(c, tag) for c in rule.conditions]

            new_sub = unify(concrete, head, sub)
            if new_sub is None:
                continue

            # Prove every condition; yield all combinations that work
            yield from self._prove_conditions(conds, new_sub, depth, concrete)

    def _prove_conditions(
        self,
        conds: List[Condition],
        sub: Substitution,
        depth: int,
        goal: Terms,
        child_nodes: List[ProofNode] = None,
    ) -> Iterator[Tuple[Substitution, ProofNode]]:
        """Recursively prove a list of conditions, yielding one result per
        combination of solutions that satisfies all of them."""
        if child_nodes is None:
            child_nodes = []

        # Base case: all conditions satisfied — emit the proof
        if not conds:
            conclusion = apply_sub(goal, sub)
            yield sub, ProofNode(conclusion, "rule", list(child_nodes))
            return

        cond, *rest = conds

        if cond.negated:
            # Negation as failure: succeed only if we CANNOT prove the term.
            # We only need to know if ANY proof exists — take the first.
            neg = next(iter(self._prove_all(cond.terms, sub, depth + 1)), None)
            if neg is None:
                # Can't prove it → negation succeeds; carry on with rest
                neg_text = apply_sub(cond.terms, sub)
                yield from self._prove_conditions(
                    rest, sub, depth, goal,
                    child_nodes + [ProofNode(neg_text, "negation")],
                )
            # If neg is not None, the negation fails — no solutions from this branch
        else:
            # Positive condition: every proof of this condition opens a branch
            for new_sub, child_node in self._prove_all(cond.terms, sub, depth + 1):
                yield from self._prove_conditions(
                    rest, new_sub, depth, goal,
                    child_nodes + [child_node],
                )
