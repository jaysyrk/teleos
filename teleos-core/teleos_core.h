/**
 * teleos_core.h — C interface to the Teleos logic engine.
 *
 * Link against teleos_core.dll (Windows) or libteleos_core.so (Linux/macOS).
 *
 * Typical usage:
 *
 *   TeleosHandle* engine = teleos_from_file("rules.teleos");
 *   int result = teleos_ask(engine, "alice can access document");  // 1 = true
 *   char* why   = teleos_why(engine, "alice can access document");
 *   printf("%s\n", why);
 *   teleos_free_str(why);
 *   teleos_free(engine);
 */

#ifndef TELEOS_CORE_H
#define TELEOS_CORE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Opaque handle to a loaded Teleos engine. */
typedef struct TeleosHandle TeleosHandle;

/* --------------------------------------------------------------------------
 * Constructors
 * -------------------------------------------------------------------------- */

/**
 * Load a .teleos knowledge base from a string.
 * Returns NULL on parse error.
 */
TeleosHandle* teleos_from_str(const char* text);

/**
 * Load a .teleos knowledge base from a file path.
 * Returns NULL if the file cannot be read or parsed.
 */
TeleosHandle* teleos_from_file(const char* path);

/* --------------------------------------------------------------------------
 * Queries
 * -------------------------------------------------------------------------- */

/**
 * Ask whether a goal can be proven.
 * Returns: 1 = true, 0 = false, -1 = error (null handle/query).
 *
 * Example: teleos_ask(engine, "alice can access document")  →  1
 */
int32_t teleos_ask(TeleosHandle* handle, const char* goal);

/**
 * Explain why a goal is true — or why it cannot be proven.
 * Returns a heap-allocated string. Caller MUST call teleos_free_str().
 *
 * Example: teleos_why(engine, "alice can access document")
 *   → "'alice can access document' — proven because: ..."
 */
char* teleos_why(TeleosHandle* handle, const char* goal);

/**
 * Find all solutions to a goal containing variables (ALL CAPS terms).
 * Returns a newline-separated list of solutions.
 * Caller MUST call teleos_free_str().
 *
 * Example: teleos_all(engine, "WHO gets distinction")
 *   → "alice\neve"
 */
char* teleos_all(TeleosHandle* handle, const char* goal);

/* --------------------------------------------------------------------------
 * Mutations
 * -------------------------------------------------------------------------- */

/**
 * Add a fact to the engine at runtime.
 * Returns 0 on success, -1 on error.
 *
 * Example: teleos_add_fact(engine, "dave is admin")
 */
int32_t teleos_add_fact(TeleosHandle* handle, const char* fact);

/* --------------------------------------------------------------------------
 * Memory management
 * -------------------------------------------------------------------------- */

/**
 * Free a string returned by teleos_why() or teleos_all().
 * Always call this when done with a returned string — never call free() directly.
 */
void teleos_free_str(char* s);

/**
 * Free an engine handle created by teleos_from_str() or teleos_from_file().
 * After this call the handle is invalid.
 */
void teleos_free(TeleosHandle* handle);

#ifdef __cplusplus
}
#endif

#endif /* TELEOS_CORE_H */
