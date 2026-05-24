import sys
from .parser import parse_file, parse_line, Fact, Rule, Query, Assert, KnowledgeBase
from .engine import Engine


def run_file(path: str) -> None:
    kb = parse_file(path)
    engine = Engine(kb)

    if not kb.queries:
        print("(no ask:/why: queries found in file)")
        return

    for query in kb.queries:
        goal_str = " ".join(query.terms)
        if query.kind == "ask":
            result = engine.ask(query.terms)
            answer = "true" if result else "false"
            print(f"ask: {goal_str}")
            print(f"  → {answer}\n")
        elif query.kind == "why":
            print(f"why: {goal_str}")
            print(f"  → {engine.why(query.terms)}\n")
        elif query.kind == "all":
            solutions = engine.all_solutions(query.terms)
            print(f"all: {goal_str}")
            if solutions:
                print("  → " + "\n     ".join(" ".join(s) for s in solutions))
            else:
                print("  → (none)")
            print()


def test_file(path: str) -> int:
    kb = parse_file(path)
    engine = Engine(kb)

    if not kb.asserts:
        print(f"No assertions found in {path}")
        return 0

    passed = 0
    failed = 0

    print(f"Testing {path}...")
    print()

    for assertion in kb.asserts:
        goal_str = " ".join(assertion.terms)
        result = engine.ask(assertion.terms)
        expected = assertion.expect

        if result == expected:
            label = "true" if expected else "not true"
            print(f"  PASS  {goal_str}  (expected {label})")
            passed += 1
        else:
            label = "true" if expected else "not true"
            print(f"  FAIL  {goal_str}")
            print(f"        Expected: {label}")
            print(f"        Got:      {'true' if result else 'not true'}")
            print(f"        {engine.why(assertion.terms)}")
            failed += 1

    print()
    total = passed + failed
    if failed == 0:
        print(f"All {total} assertions passed.")
    else:
        print(f"{passed}/{total} passed, {failed} failed.")

    return 1 if failed else 0


def repl(path: str = None) -> None:
    kb = parse_file(path) if path else KnowledgeBase()
    engine = Engine(kb)

    print("Teleos interactive mode  (type 'exit' to quit, 'help' for commands)")
    if path:
        print(f"Loaded: {path}")
    print()

    while True:
        try:
            line = input("teleos> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not line:
            continue
        if line in ("exit", "quit"):
            break
        if line == "help":
            print("  fact: <terms>          — add a fact")
            print("  rule: if <cond> [and <cond>...] then <head>  — add a rule")
            print("  ask:  <terms>          — true or false?")
            print("  why:  <terms>          — explain why something is true")
            print("  facts                  — list all facts")
            print("  rules                  — list all rules")
            print()
            continue
        if line == "facts":
            for f in kb.facts:
                print(" ", " ".join(f.terms))
            print()
            continue
        if line == "rules":
            for r in kb.rules:
                conds = " and ".join(" ".join(c) for c in r.conditions)
                head = " ".join(r.head)
                print(f"  if {conds} then {head}")
            print()
            continue

        try:
            item = parse_line(line)
            if item is None:
                print("  (unrecognised — start with fact:, rule:, ask:, or why:)")
                continue

            if isinstance(item, Fact):
                kb.facts.append(item)
                engine = Engine(kb)
                print(f"  ✓ fact added: {' '.join(item.terms)}\n")

            elif isinstance(item, Rule):
                kb.rules.append(item)
                engine = Engine(kb)
                print(f"  ✓ rule added: if ... then {' '.join(item.head)}\n")

            elif isinstance(item, Query):
                goal_str = " ".join(item.terms)
                if item.kind == "ask":
                    result = engine.ask(item.terms)
                    print(f"  → {'true' if result else 'false'}\n")
                elif item.kind == "why":
                    print(f"  → {engine.why(item.terms)}\n")
                elif item.kind == "all":
                    solutions = engine.all_solutions(item.terms)
                    if solutions:
                        print("  → " + "\n     ".join(" ".join(s) for s in solutions))
                    else:
                        print("  → (none)")
                    print()

        except ValueError as e:
            print(f"  Error: {e}\n")


def main() -> None:
    args = sys.argv[1:]

    if not args:
        repl()
        return

    cmd = args[0]

    if cmd == "run" and len(args) >= 2:
        run_file(args[1])
    elif cmd == "test" and len(args) >= 2:
        sys.exit(test_file(args[1]))
    elif cmd == "repl":
        repl(args[1] if len(args) >= 2 else None)
    elif cmd in ("-h", "--help", "help"):
        print("Usage:")
        print("  teleos run  <file.teleos>     — run queries in a file")
        print("  teleos test <file.teleos>     — run assertions in a file")
        print("  teleos repl [file.teleos]     — interactive session")
        print("  teleos                        — interactive session (no file)")
    else:
        run_file(cmd)


if __name__ == "__main__":
    main()
