/**
 * test.cpp — Integration tests for the Teleos C++ binding.
 *
 * Compile (from bindings/cpp/):
 *   g++ test.cpp -I. -I../../teleos-core ^
 *       -L../../teleos-core/target/release -lteleos_core ^
 *       -o test.exe
 *   set PATH=..\..\teleos-core\target\release;%PATH%
 *   test.exe
 */

#include "teleos.hpp"
#include <iostream>
#include <cassert>
#include <stdexcept>

static int passed = 0;
static int failed = 0;

static void check(const char* name, bool cond) {
    if (cond) {
        std::cout << "  PASS  " << name << "\n";
        ++passed;
    } else {
        std::cout << "  FAIL  " << name << "\n";
        ++failed;
    }
}

static const std::string ACCESS_RULES =
    "fact: alice is admin\n"
    "fact: bob is user\n"
    "fact: charlie is user\n"
    "fact: charlie is banned\n"
    "fact: report is public\n"
    "fact: document is confidential\n"
    "rule: if X is admin then X can access Y\n"
    "rule: if X is user and Y is public and not X is banned then X can access Y\n";

static const std::string GRADES_RULES =
    "fact: alice score 95\n"
    "fact: bob score 80\n"
    "fact: charlie score 65\n"
    "rule: if X score S and S > 90 then X gets distinction\n"
    "rule: if X score S and S > 75 and S <= 90 then X gets merit\n"
    "rule: if X score S and S > 60 and S <= 75 then X gets pass\n"
    "rule: if X score S and S <= 60 then X gets fail\n";

int main() {
    std::cout << "Testing C++ binding (teleos.hpp)...\n\n";

    // ── Basic facts / ask ─────────────────────────────────────────────────
    std::cout << "Basic facts\n";
    {
        auto e = teleos::parse(ACCESS_RULES);
        check("ask true (alice can access document)",  e.ask("alice can access document"));
        check("ask false (bob can access document)",  !e.ask("bob can access document"));
    }

    // ── Rule chaining ─────────────────────────────────────────────────────
    std::cout << "\nRule chaining\n";
    {
        auto e = teleos::parse(ACCESS_RULES);
        check("bob can access report (derived)",  e.ask("bob can access report"));
        check("charlie cannot access report (banned)", !e.ask("charlie can access report"));
    }

    // ── Negation ─────────────────────────────────────────────────────────
    std::cout << "\nNegation\n";
    {
        auto e = teleos::parse(ACCESS_RULES);
        check("negation true (bob not banned)",   e.ask("bob can access report"));
        check("negation false (charlie banned)",  !e.ask("charlie can access report"));
    }

    // ── Numeric comparisons ───────────────────────────────────────────────
    std::cout << "\nNumeric comparisons\n";
    {
        auto e = teleos::parse(GRADES_RULES);
        check("alice gets distinction (score 95 > 90)",  e.ask("alice gets distinction"));
        check("alice does not get fail",                 !e.ask("alice gets fail"));
        check("bob gets merit (score 80)",                e.ask("bob gets merit"));
        check("charlie gets pass (score 65)",             e.ask("charlie gets pass"));
    }

    // ── all() queries ─────────────────────────────────────────────────────
    std::cout << "\nall() queries\n";
    {
        auto e = teleos::parse(GRADES_RULES);
        auto results = e.all("WHO gets distinction");
        bool found_alice = false;
        for (const auto& r : results) {
            if (r.find("alice") != std::string::npos) found_alice = true;
        }
        check("alice in WHO gets distinction", found_alice);
        check("all() returns at least one result", !results.empty());
    }

    // ── why() explanations ────────────────────────────────────────────────
    std::cout << "\nwhy() explanations\n";
    {
        auto e = teleos::parse(ACCESS_RULES);
        std::string why = e.why("bob can access report");
        check("why contains 'bob is user'", why.find("bob is user") != std::string::npos);

        std::string why_fail = e.why("charlie can access document");
        check("why failure contains 'Cannot prove'", why_fail.find("Cannot prove") != std::string::npos);
    }

    // ── addFact() at runtime ──────────────────────────────────────────────
    std::cout << "\naddFact() at runtime\n";
    {
        auto e = teleos::parse(ACCESS_RULES);
        check("before addFact: dave cannot access document", !e.ask("dave can access document"));
        e.add_fact("dave is admin");
        check("after addFact: dave can access document",      e.ask("dave can access document"));
    }

    // ── Summary ───────────────────────────────────────────────────────────
    std::cout << "\n" << std::string(50, '-') << "\n";
    std::cout << "C++ binding: " << passed << " passed, " << failed << " failed\n";
    return failed == 0 ? 0 : 1;
}
