// Package teleos provides Go bindings for the Teleos logic engine.
//
// Load a .teleos knowledge base, then ask questions in plain English:
//
//	engine, err := teleos.LoadFile("rules.teleos")
//	if err != nil {
//	    log.Fatal(err)
//	}
//	defer engine.Close()
//
//	if engine.Ask("alice can access document") {
//	    fmt.Println("access granted")
//	}
//
//	fmt.Println(engine.Why("alice can access document"))
//
//	for _, who := range engine.All("WHO gets distinction") {
//	    fmt.Println(who)
//	}
//
// # Setup
//
// Build the Rust core first:
//
//	cd teleos-core && cargo build --release
//
// Then set CGO_LDFLAGS to point at the compiled library:
//
//	# Windows
//	set CGO_LDFLAGS=-LC:\path\to\teleos-core\target\release
//	set CGO_CFLAGS=-IC:\path\to\teleos-core
//
//	# Linux / macOS
//	export CGO_LDFLAGS=-L/path/to/teleos-core/target/release
//	export CGO_CFLAGS=-I/path/to/teleos-core
package teleos

/*
#cgo LDFLAGS: -lteleos_core
#include "teleos_core.h"
#include <stdlib.h>
*/
import "C"
import (
	"errors"
	"strings"
	"unsafe"
)

// Engine is a loaded Teleos knowledge base ready to query.
// Always call Close() when done to free the underlying Rust engine.
type Engine struct {
	handle *C.TeleosHandle
}

// LoadFile loads a .teleos knowledge base from a file path.
func LoadFile(path string) (*Engine, error) {
	cpath := C.CString(path)
	defer C.free(unsafe.Pointer(cpath))

	handle := C.teleos_from_file(cpath)
	if handle == nil {
		return nil, errors.New("teleos: failed to load file: " + path)
	}
	return &Engine{handle: handle}, nil
}

// Parse loads a .teleos knowledge base from a string.
func Parse(text string) (*Engine, error) {
	ctext := C.CString(text)
	defer C.free(unsafe.Pointer(ctext))

	handle := C.teleos_from_str(ctext)
	if handle == nil {
		return nil, errors.New("teleos: failed to parse knowledge base")
	}
	return &Engine{handle: handle}, nil
}

// Ask returns true if the goal can be proven from the knowledge base.
//
//	engine.Ask("alice can access document")  // true
func (e *Engine) Ask(goal string) bool {
	cgoal := C.CString(goal)
	defer C.free(unsafe.Pointer(cgoal))
	return C.teleos_ask(e.handle, cgoal) == 1
}

// Why returns a human-readable proof of why a goal is true,
// or an explanation of why it cannot be proven.
//
//	engine.Why("alice can access document")
//	// → "'alice can access document' — proven because: ..."
func (e *Engine) Why(goal string) string {
	cgoal := C.CString(goal)
	defer C.free(unsafe.Pointer(cgoal))

	cresult := C.teleos_why(e.handle, cgoal)
	if cresult == nil {
		return ""
	}
	defer C.teleos_free_str(cresult)
	return C.GoString(cresult)
}

// All returns every solution to a goal containing variables (ALL CAPS terms).
// Returns a slice of strings for single-variable goals.
//
//	engine.All("WHO gets distinction")  // ["alice", "eve"]
func (e *Engine) All(goal string) []string {
	cgoal := C.CString(goal)
	defer C.free(unsafe.Pointer(cgoal))

	cresult := C.teleos_all(e.handle, cgoal)
	if cresult == nil {
		return nil
	}
	defer C.teleos_free_str(cresult)

	raw := C.GoString(cresult)
	if raw == "" {
		return nil
	}

	// Result is newline-separated full solutions e.g. "alice gets distinction"
	// Extract just the variable values (first word that differs per solution).
	lines := strings.Split(raw, "\n")
	goalWords := strings.Fields(goal)

	// Find which positions are variables (ALL CAPS)
	var varPositions []int
	for i, w := range goalWords {
		if isVariable(w) {
			varPositions = append(varPositions, i)
		}
	}

	if len(varPositions) == 0 {
		return lines // no variables — return full solution strings
	}

	results := make([]string, 0, len(lines))
	for _, line := range lines {
		words := strings.Fields(line)
		if len(words) != len(goalWords) {
			results = append(results, line)
			continue
		}
		// Single variable: return just the value
		if len(varPositions) == 1 {
			results = append(results, words[varPositions[0]])
		} else {
			// Multiple variables: return "VAR1=val1 VAR2=val2"
			var parts []string
			for _, pos := range varPositions {
				parts = append(parts, goalWords[pos]+"="+words[pos])
			}
			results = append(results, strings.Join(parts, " "))
		}
	}
	return results
}

// AddFact adds a fact to the knowledge base at runtime.
//
//	engine.AddFact("dave is admin")
func (e *Engine) AddFact(fact string) error {
	cfact := C.CString(fact)
	defer C.free(unsafe.Pointer(cfact))

	if C.teleos_add_fact(e.handle, cfact) != 0 {
		return errors.New("teleos: failed to add fact: " + fact)
	}
	return nil
}

// Close frees the underlying Rust engine. Always call this when done.
func (e *Engine) Close() {
	if e.handle != nil {
		C.teleos_free(e.handle)
		e.handle = nil
	}
}

// isVariable returns true for ALL-CAPS terms (Teleos variables).
func isVariable(s string) bool {
	if len(s) == 0 {
		return false
	}
	for _, c := range s {
		if c < 'A' || c > 'Z' {
			return false
		}
	}
	return true
}
