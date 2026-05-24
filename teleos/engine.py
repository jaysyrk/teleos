from typing import Dict, Iterator, List, Optional, Tuple
import operator as _op

from .parser import Condition, KnowledgeBase, Rule, Terms

Substitution = Dict[str, str]

_COMPARISON_OPS = {
    ">": _op.gt,
    "<": _op.lt,
    ">=": _op.ge,
    "<=": _op.le,
    "=": _op.eq,
    "!=": _op.ne,
}

def is_variable(term: str) -> bool:
    base = term.split("$")[0]
    return bool(base) and base.isalpha() and base.isupper()

def resolve(term: str, sub: Substitution) -> str:
    seen: set = set()
    while term in sub and term not in seen:
        seen.add(term)
        term = sub[term]
    return term

def apply_sub(terms: Terms, sub: Substitution) -> Terms:
    return tuple(resolve(t, sub) for t in terms)

def unify(t1: Terms, t2: Terms, sub: Substitution) -> Optional[Substitution]:
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
            return None
    return result

def rename_vars(terms: Terms, tag: int) -> Terms:
    return tuple(f"{t}${tag}" if is_variable(t) else t for t in terms)

def rename_condition(cond: Condition, tag: int) -> Condition:
    return Condition(terms=rename_vars(cond.terms, tag), negated=cond.negated)

class ProofNode:

    def __init__(self, conclusion: Terms, reason: str, children: List["ProofNode"] = None):
        self.conclusion = conclusion
        self.reason = reason
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

class Engine:

    MAX_DEPTH = 30

    def __init__(self, kb: KnowledgeBase):
        self.facts: List[Terms] = [f.terms for f in kb.facts]
        self.rules: List[Rule] = list(kb.rules)
        self._counter = 0

    def ask(self, goal: Terms) -> bool:
        return self._prove(goal, {}, 0) is not None

    def why(self, goal: Terms) -> str:
        result = self._prove(goal, {}, 0)
        if result is None:
            return self._explain_failure(goal)
        _, tree = result
        return tree.explain()

    def add_fact(self, terms: Terms) -> None:
        self.facts.append(terms)

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def all_solutions(self, goal: Terms) -> List[Terms]:
        seen: set = set()
        results: List[Terms] = []
        for sub, _ in self._prove_all(goal, {}, 0):
            concrete = apply_sub(goal, sub)
            if concrete not in seen:
                seen.add(concrete)
                results.append(concrete)
        return results

    def _fresh_tag(self) -> int:
        self._counter += 1
        return self._counter

    def _prove(self, goal: Terms, sub: Substitution, depth: int) -> Optional[Tuple[Substitution, ProofNode]]:
        return next(iter(self._prove_all(goal, sub, depth)), None)

    def _explain_failure(self, goal: Terms) -> str:
        concrete = apply_sub(goal, {})
        goal_text = " ".join(concrete)

        best_passed = -1
        best_msg = ""
        best_blocker: Optional[ProofNode] = None

        for rule in self.rules:
            tag = self._fresh_tag()
            head = rename_vars(rule.head, tag)
            conds = [rename_condition(c, tag) for c in rule.conditions]

            sub = unify(concrete, head, {})
            if sub is None:
                continue

            passed = 0
            current_sub = sub
            fail_msg = None
            blocker: Optional[ProofNode] = None

            for cond in conds:
                if cond.negated:
                    pos = next(iter(self._prove_all(cond.terms, current_sub, 0)), None)
                    if pos is not None:
                        _, proof = pos
                        neg_text = " ".join(apply_sub(cond.terms, current_sub))
                        fail_msg = f"'not {neg_text}' is blocked — it CAN be proven:"
                        blocker = proof
                        break
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
                continue

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
        if depth > self.MAX_DEPTH:
            return

        concrete = apply_sub(goal, sub)

        if len(concrete) == 3 and concrete[1] in _COMPARISON_OPS:
            left, op, right = concrete
            try:
                if _COMPARISON_OPS[op](float(left), float(right)):
                    yield sub, ProofNode(concrete, "comparison")
            except (ValueError, TypeError):
                pass
            return

        for fact in self.facts:
            new_sub = unify(concrete, fact, sub)
            if new_sub is not None:
                yield new_sub, ProofNode(apply_sub(goal, new_sub), "fact")

        for rule in self.rules:
            tag = self._fresh_tag()
            head = rename_vars(rule.head, tag)
            conds = [rename_condition(c, tag) for c in rule.conditions]

            new_sub = unify(concrete, head, sub)
            if new_sub is None:
                continue

            yield from self._prove_conditions(conds, new_sub, depth, concrete)

    def _prove_conditions(
        self,
        conds: List[Condition],
        sub: Substitution,
        depth: int,
        goal: Terms,
        child_nodes: List[ProofNode] = None,
    ) -> Iterator[Tuple[Substitution, ProofNode]]:
        if child_nodes is None:
            child_nodes = []

        if not conds:
            conclusion = apply_sub(goal, sub)
            yield sub, ProofNode(conclusion, "rule", list(child_nodes))
            return

        cond, *rest = conds

        if cond.negated:
            neg = next(iter(self._prove_all(cond.terms, sub, depth + 1)), None)
            if neg is None:
                neg_text = apply_sub(cond.terms, sub)
                yield from self._prove_conditions(
                    rest, sub, depth, goal,
                    child_nodes + [ProofNode(neg_text, "negation")],
                )
        else:
            for new_sub, child_node in self._prove_all(cond.terms, sub, depth + 1):
                yield from self._prove_conditions(
                    rest, new_sub, depth, goal,
                    child_nodes + [child_node],
                )
