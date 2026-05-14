// TeleosTest — C# binding integration test
// Verifies the P/Invoke wrapper works against the real Rust DLL.

using Teleos;

int passed = 0;
int failed = 0;

void Assert(string label, bool condition)
{
    if (condition) { Console.WriteLine($"  PASS  {label}"); passed++; }
    else           { Console.WriteLine($"  FAIL  {label}"); failed++; }
}

Console.WriteLine("Testing C# binding against teleos_core.dll...\n");

// ── Load from string ──────────────────────────────────────────────────────────
const string src = """
    fact: alice is admin
    fact: bob is user
    fact: charlie is user
    fact: charlie is banned
    fact: report is public
    fact: document is confidential
    rule: if X is admin then X can access Y
    rule: if X is user and Y is public and not X is banned then X can access Y
    """;

using var engine = Engine.Parse(src);

// ── Ask ───────────────────────────────────────────────────────────────────────
Assert("alice can access document (true)",  engine.Ask("alice can access document"));
Assert("alice can access report (true)",    engine.Ask("alice can access report"));
Assert("bob can access report (true)",      engine.Ask("bob can access report"));
Assert("bob can access document (false)",  !engine.Ask("bob can access document"));
Assert("charlie can access report (false)",!engine.Ask("charlie can access report"));

// ── Why ───────────────────────────────────────────────────────────────────────
var why = engine.Why("bob can access report");
Assert("why: bob can access report contains 'bob is user'", why.Contains("bob is user"));

var whyFail = engine.Why("charlie can access report");
Assert("why failure contains 'Cannot prove'", whyFail.Contains("Cannot prove"));

// ── All ───────────────────────────────────────────────────────────────────────
var allDoc = engine.All("WHO can access document").ToList();
Assert("all: WHO can access document contains alice", allDoc.Any(s => s.Contains("alice")));
Assert("all: WHO can access document does not contain charlie", !allDoc.Any(s => s.Contains("charlie")));

// ── Add fact at runtime ───────────────────────────────────────────────────────
Assert("dave can access document before add (false)", !engine.Ask("dave can access document"));
engine.AddFact("dave is admin");
Assert("dave can access document after add (true)", engine.Ask("dave can access document"));

// ── Numeric comparisons ───────────────────────────────────────────────────────
const string gradeSrc = """
    fact: alice has score 95
    fact: bob has score 72
    rule: if X has score S and S >= 90 then X gets distinction
    rule: if X has score S and S >= 60 and S < 90 then X gets pass
    """;

using var grades = Engine.Parse(gradeSrc);
Assert("alice gets distinction (true)",  grades.Ask("alice gets distinction"));
Assert("alice gets pass (false)",       !grades.Ask("alice gets pass"));
Assert("bob gets pass (true)",           grades.Ask("bob gets pass"));
Assert("bob gets distinction (false)",  !grades.Ask("bob gets distinction"));

// ── Load from file ────────────────────────────────────────────────────────────
var examplesPath = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "..", "examples", "access.teleos"));
if (File.Exists(examplesPath))
{
    using var fromFile = Engine.LoadFile(examplesPath);
    Assert("LoadFile: alice can access document", fromFile.Ask("alice can access document"));
    Assert("LoadFile: charlie cannot access report", !fromFile.Ask("charlie can access report"));
}
else
{
    Console.WriteLine($"  SKIP  LoadFile test (path not found: {examplesPath})");
}

// ── Summary ───────────────────────────────────────────────────────────────────
Console.WriteLine();
Console.WriteLine($"Results: {passed} passed, {failed} failed");
return failed == 0 ? 0 : 1;
