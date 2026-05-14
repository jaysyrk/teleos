/**
 * teleos.hpp — header-only C++ binding for the Teleos logic engine.
 *
 * Drop this file into your project. Link against teleos_core.
 * That's it — no other setup required.
 *
 * Usage:
 *
 *   #include "teleos.hpp"
 *
 *   auto engine = teleos::load_file("rules.teleos");
 *   engine.ask("alice can access document");    // true
 *   engine.why("alice can access document");    // std::string proof
 *   engine.all("WHO gets distinction");         // std::vector<std::string>
 *
 * Compile:
 *   g++ main.cpp -I. -L/path/to/release -lteleos_core -o myapp
 */

#pragma once

#include <string>
#include <vector>
#include <stdexcept>
#include <sstream>
#include "teleos_core.h"

namespace teleos {

/**
 * A loaded Teleos knowledge base, ready to query.
 * RAII — the underlying engine is freed automatically when this goes out of scope.
 */
class Engine {
public:
    // ── Constructors / destructor ─────────────────────────────────────────

    explicit Engine(TeleosHandle* handle) : handle_(handle) {
        if (!handle_) {
            throw std::runtime_error("teleos: failed to create engine (null handle)");
        }
    }

    ~Engine() {
        if (handle_) {
            teleos_free(handle_);
            handle_ = nullptr;
        }
    }

    // Non-copyable (owns the handle)
    Engine(const Engine&) = delete;
    Engine& operator=(const Engine&) = delete;

    // Movable
    Engine(Engine&& other) noexcept : handle_(other.handle_) {
        other.handle_ = nullptr;
    }
    Engine& operator=(Engine&& other) noexcept {
        if (this != &other) {
            if (handle_) teleos_free(handle_);
            handle_ = other.handle_;
            other.handle_ = nullptr;
        }
        return *this;
    }

    // ── Queries ───────────────────────────────────────────────────────────

    /**
     * Returns true if the goal can be proven from the knowledge base.
     *
     *   engine.ask("alice can access document")  // true
     */
    bool ask(const std::string& goal) const {
        return teleos_ask(handle_, goal.c_str()) == 1;
    }

    /**
     * Returns a human-readable proof, or an explanation of why the goal fails.
     *
     *   engine.why("alice can access document")
     *   // → "'alice can access document' — proven because: ..."
     */
    std::string why(const std::string& goal) const {
        char* raw = teleos_why(handle_, goal.c_str());
        if (!raw) return "";
        std::string result(raw);
        teleos_free_str(raw);
        return result;
    }

    /**
     * Returns all solutions to a query containing variables (ALL CAPS terms).
     * Each element is a full solution string, e.g. "alice gets distinction".
     *
     *   engine.all("WHO gets distinction")
     *   // → {"alice gets distinction", "eve gets distinction"}
     */
    std::vector<std::string> all(const std::string& goal) const {
        char* raw = teleos_all(handle_, goal.c_str());
        if (!raw) return {};
        std::string combined(raw);
        teleos_free_str(raw);

        std::vector<std::string> results;
        std::istringstream ss(combined);
        std::string line;
        while (std::getline(ss, line)) {
            if (!line.empty()) results.push_back(line);
        }
        return results;
    }

    // ── Mutations ─────────────────────────────────────────────────────────

    /**
     * Add a fact to the knowledge base at runtime.
     *
     *   engine.add_fact("dave is admin")
     */
    void add_fact(const std::string& fact) {
        if (teleos_add_fact(handle_, fact.c_str()) != 0) {
            throw std::runtime_error("teleos: failed to add fact: " + fact);
        }
    }

private:
    TeleosHandle* handle_;
};

// ── Free functions ────────────────────────────────────────────────────────────

/**
 * Load a .teleos knowledge base from a file path.
 *
 *   auto engine = teleos::load_file("rules.teleos");
 */
inline Engine load_file(const std::string& path) {
    TeleosHandle* h = teleos_from_file(path.c_str());
    if (!h) throw std::runtime_error("teleos: failed to load file: " + path);
    return Engine(h);
}

/**
 * Load a .teleos knowledge base from a string.
 *
 *   auto engine = teleos::parse(R"(
 *       fact: alice is admin
 *       rule: if X is admin then X can access Y
 *   )");
 */
inline Engine parse(const std::string& text) {
    TeleosHandle* h = teleos_from_str(text.c_str());
    if (!h) throw std::runtime_error("teleos: failed to parse knowledge base");
    return Engine(h);
}

} // namespace teleos
