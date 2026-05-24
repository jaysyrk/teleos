import os
import pytest
import teleos

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")

def example(name: str) -> str:
    return os.path.join(EXAMPLES, name)

class TestBasicFacts:
    def test_direct_fact_true(self):
        e = teleos.loads("fact: sky is blue")
        assert e.ask("sky is blue") is True

    def test_direct_fact_false(self):
        e = teleos.loads("fact: sky is blue")
        assert e.ask("sky is red") is False

    def test_multiple_facts(self):
        e = teleos.loads("fact: alice is admin\nfact: bob is user")
        assert e.ask("alice is admin") is True
        assert e.ask("bob is user") is True
        assert e.ask("alice is user") is False

    def test_add_fact_at_runtime(self):
        e = teleos.loads("fact: alice is admin")
        assert e.ask("bob is admin") is False
        e.add_fact("bob is admin")
        assert e.ask("bob is admin") is True

class TestRuleChaining:
    def test_single_rule(self):
        src = "fact: alice is admin\nrule: if X is admin then X can access Y"
        e = teleos.loads(src)
        assert e.ask("alice can access document") is True
        assert e.ask("bob can access document") is False

    def test_two_step_chain(self):
        src = (
            "fact: fido is dog\n"
            "rule: if X is dog then X is mammal\n"
            "rule: if X is mammal then X has fur\n"
        )
        e = teleos.loads(src)
        assert e.ask("fido is mammal") is True
        assert e.ask("fido has fur") is True

    def test_variable_in_conclusion_bound_correctly(self):
        src = (
            "fact: alice is admin\n"
            "fact: report is public\n"
            "rule: if X is admin then X can access Y\n"
        )
        e = teleos.loads(src)
        assert e.ask("alice can access report") is True
        assert e.ask("alice can access document") is True

class TestNegation:
    COMMON = (
        "fact: alice is user\n"
        "fact: charlie is user\n"
        "fact: charlie is banned\n"
        "rule: if X is user and not X is banned then X can post\n"
    )

    def test_negation_succeeds_when_fact_absent(self):
        e = teleos.loads(self.COMMON)
        assert e.ask("alice can post") is True

    def test_negation_fails_when_fact_present(self):
        e = teleos.loads(self.COMMON)
        assert e.ask("charlie can post") is False

class TestNumericComparisons:
    GRADES = (
        "fact: alice has score 95\n"
        "fact: bob has score 72\n"
        "fact: charlie has score 80\n"
        "fact: diana has score 55\n"
        "rule: if X has score S and S >= 90 then X gets distinction\n"
        "rule: if X has score S and S >= 75 and S < 90 then X gets merit\n"
        "rule: if X has score S and S >= 60 and S < 75 then X gets pass\n"
        "rule: if X has score S and S < 60 then X gets fail\n"
    )

    def test_distinction(self):
        e = teleos.loads(self.GRADES)
        assert e.ask("alice gets distinction") is True
        assert e.ask("alice gets fail") is False

    def test_merit(self):
        e = teleos.loads(self.GRADES)
        assert e.ask("charlie gets merit") is True
        assert e.ask("charlie gets distinction") is False

    def test_pass(self):
        e = teleos.loads(self.GRADES)
        assert e.ask("bob gets pass") is True

    def test_fail(self):
        e = teleos.loads(self.GRADES)
        assert e.ask("diana gets fail") is True
        assert e.ask("diana gets pass") is False

    def test_boundary_exactly_90(self):
        e = teleos.loads(
            "fact: alice has score 90\n"
            "rule: if X has score S and S >= 90 then X gets distinction\n"
            "rule: if X has score S and S >= 75 and S < 90 then X gets merit\n"
        )
        assert e.ask("alice gets distinction") is True
        assert e.ask("alice gets merit") is False

    def test_boundary_exactly_75(self):
        e = teleos.loads(
            "fact: bob has score 75\n"
            "rule: if X has score S and S >= 75 and S < 90 then X gets merit\n"
            "rule: if X has score S and S >= 60 and S < 75 then X gets pass\n"
        )
        assert e.ask("bob gets merit") is True
        assert e.ask("bob gets pass") is False

    def test_all_ops(self):
        src = "fact: x has val 5\nrule: if x has val V and V {op} {rhs} then result is true\n"
        cases = [
            (">",  4,  True),
            (">",  5,  False),
            ("<",  6,  True),
            ("<",  5,  False),
            (">=", 5,  True),
            (">=", 6,  False),
            ("<=", 5,  True),
            ("<=", 4,  False),
            ("=",  5,  True),
            ("=",  6,  False),
            ("!=", 6,  True),
            ("!=", 5,  False),
        ]
        for op, rhs, expected in cases:
            e = teleos.loads(src.format(op=op, rhs=rhs))
            assert e.ask("result is true") is expected, f"V {op} {rhs} expected {expected}"

class TestAllQueries:
    def test_single_variable(self):
        src = (
            "fact: alice is admin\n"
            "fact: bob is admin\n"
            "fact: charlie is user\n"
        )
        e = teleos.loads(src)
        result = e.all("WHO is admin")
        assert sorted(result) == ["alice", "bob"]

    def test_no_matches(self):
        e = teleos.loads("fact: alice is user")
        assert e.all("WHO is admin") == []

    def test_derived_via_rule(self):
        src = (
            "fact: fido is dog\n"
            "fact: whiskers is cat\n"
            "rule: if X is dog then X is mammal\n"
            "rule: if X is cat then X is mammal\n"
        )
        e = teleos.loads(src)
        result = e.all("WHO is mammal")
        assert sorted(result) == ["fido", "whiskers"]

class TestWhyExplanations:
    def test_why_fact(self):
        e = teleos.loads("fact: sky is blue")
        why = e.why("sky is blue")
        assert "sky is blue" in why

    def test_why_rule_chain(self):
        src = (
            "fact: alice is admin\n"
            "rule: if X is admin then X can access Y\n"
        )
        e = teleos.loads(src)
        why = e.why("alice can access document")
        assert "alice is admin" in why

    def test_why_false(self):
        e = teleos.loads("fact: alice is admin")
        why = e.why("alice is banned")
        assert "Cannot prove" in why or "cannot prove" in why.lower()

    def test_why_comparison(self):
        src = (
            "fact: alice has score 95\n"
            "rule: if X has score S and S >= 90 then X gets distinction\n"
        )
        e = teleos.loads(src)
        why = e.why("alice gets distinction")
        assert "95" in why

class TestAssertMode:
    def test_all_assertions_pass(self):
        src = (
            "fact: alice is admin\n"
            "rule: if X is admin then X can access Y\n"
            "assert: alice can access document\n"
            "assert not: bob can access document\n"
        )
        e = teleos.loads(src)
        results = e.test()
        assert results["passed"] == 2
        assert results["failed"] == 0

    def test_failing_assertion_detected(self):
        src = (
            "fact: alice is admin\n"
            "assert not: alice is admin\n"
        )
        e = teleos.loads(src)
        results = e.test()
        assert results["failed"] == 1

    def test_no_assertions(self):
        e = teleos.loads("fact: alice is admin")
        results = e.test()
        assert results["passed"] == 0
        assert results["failed"] == 0

class TestImport:
    def test_import_facts_available(self):
        e = teleos.load(example("import-demo.teleos"))

        assert e.ask("alice is admin") is True

    def test_import_rules_available(self):
        e = teleos.load(example("import-demo.teleos"))

        assert e.ask("alice is staff") is True

    def test_import_plus_local_rules(self):
        e = teleos.load(example("import-demo.teleos"))
        assert e.ask("alice can access document") is True
        assert e.ask("eve can access document") is True

    def test_import_assertions_all_pass(self):
        e = teleos.load(example("import-demo.teleos"))
        results = e.test()
        assert results["failed"] == 0, results["results"]

@pytest.mark.parametrize("filename,expected_assertions", [
    ("access.teleos",      7),
    ("grades.teleos",      9),
    ("import-demo.teleos", 6),
])
def test_example_assertions(filename, expected_assertions):
    e = teleos.load(example(filename))
    results = e.test()
    assert results["failed"] == 0, (
        f"{filename}: {results['failed']} assertion(s) failed\n"
        + "\n".join(
            f"  FAIL: {r['query']} (expected {r['expected']}, got {r['got']})"
            for r in results.get("results", [])
            if not r["passed"]
        )
    )
    assert results["passed"] == expected_assertions, (
        f"{filename}: expected {expected_assertions} assertions, found {results['passed']}"
    )

class TestParserErrors:
    def test_unknown_keyword_raises(self):
        with pytest.raises(ValueError, match="Unknown keyword"):
            teleos.loads("blah: sky is blue")

    def test_empty_string_ok(self):
        e = teleos.loads("")
        assert e.ask("anything") is False

    def test_comment_only_ok(self):
        e = teleos.loads("# this is a comment\n# another comment")
        assert e.ask("anything") is False

class TestAPIShape:
    def test_facts_list(self):
        e = teleos.loads("fact: sky is blue\nfact: grass is green")
        facts = e.facts()
        assert any("sky" in f for f in facts)
        assert any("grass" in f for f in facts)

    def test_rules_list(self):
        src = "rule: if X is admin then X can access Y"
        e = teleos.loads(src)
        rules = e.rules()
        assert len(rules) == 1
        assert "admin" in rules[0]

    def test_add_rule_at_runtime(self):
        e = teleos.loads("fact: alice is admin")
        assert e.ask("alice can access document") is False
        e.add_rule("if X is admin then X can access Y")
        assert e.ask("alice can access document") is True
