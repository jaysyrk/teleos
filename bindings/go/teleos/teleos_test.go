package teleos_test

import (
	"testing"

	teleos "github.com/teleos/teleos-go/teleos"
)

const accessRules = `
fact: alice is admin
fact: bob is user
fact: charlie is user
fact: charlie is banned
fact: report is public
fact: document is confidential
rule: if X is admin then X can access Y
rule: if X is user and Y is public and not X is banned then X can access Y
`

func setup(t *testing.T) *teleos.Engine {
	t.Helper()
	engine, err := teleos.Parse(accessRules)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	return engine
}

func TestAsk(t *testing.T) {
	engine := setup(t)
	defer engine.Close()

	cases := []struct {
		goal string
		want bool
	}{
		{"alice can access document", true},
		{"alice can access report", true},
		{"bob can access report", true},
		{"bob can access document", false},
		{"charlie can access report", false},
	}

	for _, c := range cases {
		got := engine.Ask(c.goal)
		if got != c.want {
			t.Errorf("Ask(%q) = %v, want %v", c.goal, got, c.want)
		}
	}
}

func TestWhy(t *testing.T) {
	engine := setup(t)
	defer engine.Close()

	why := engine.Why("alice can access document")
	if why == "" {
		t.Error("Why returned empty string")
	}
}

func TestAll(t *testing.T) {
	engine := setup(t)
	defer engine.Close()

	results := engine.All("WHO can access report")
	if len(results) == 0 {
		t.Error("All returned no results")
	}
}

func TestAddFact(t *testing.T) {
	engine := setup(t)
	defer engine.Close()

	if engine.Ask("dave can access report") {
		t.Error("dave should not have access before AddFact")
	}

	if err := engine.AddFact("dave is admin"); err != nil {
		t.Fatalf("AddFact failed: %v", err)
	}

	if !engine.Ask("dave can access report") {
		t.Error("dave should have access after AddFact")
	}
}
