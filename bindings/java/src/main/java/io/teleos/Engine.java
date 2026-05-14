package io.teleos;

import com.sun.jna.Library;
import com.sun.jna.Native;
import com.sun.jna.Pointer;

/**
 * Java binding for the Teleos logic engine via JNA.
 *
 * <pre>
 * // Maven dependency:
 * // &lt;dependency&gt;
 * //   &lt;groupId&gt;io.teleos&lt;/groupId&gt;
 * //   &lt;artifactId&gt;teleos-java&lt;/artifactId&gt;
 * //   &lt;version&gt;0.1.0&lt;/version&gt;
 * // &lt;/dependency&gt;
 *
 * try (Engine engine = Engine.loadFile("rules.teleos")) {
 *     engine.ask("alice can access document");   // true
 *     engine.why("alice can access document");   // proof string
 *     engine.all("WHO gets distinction");        // List&lt;String&gt;
 * }
 * </pre>
 */
public class Engine implements AutoCloseable {

    // ── Native interface (JNA) ────────────────────────────────────────────

    private interface TeleosLib extends Library {
        TeleosLib INSTANCE = Native.load("teleos_core", TeleosLib.class);

        Pointer teleos_from_str(String text);
        Pointer teleos_from_file(String path);
        int     teleos_ask(Pointer handle, String goal);
        Pointer teleos_why(Pointer handle, String goal);
        Pointer teleos_all(Pointer handle, String goal);
        int     teleos_add_fact(Pointer handle, String fact);
        void    teleos_free_str(Pointer s);
        void    teleos_free(Pointer handle);
    }

    // ── State ─────────────────────────────────────────────────────────────

    private Pointer handle;

    private Engine(Pointer handle) {
        if (handle == null) throw new IllegalStateException("Teleos: failed to create engine.");
        this.handle = handle;
    }

    // ── Constructors ──────────────────────────────────────────────────────

    /**
     * Load a .teleos knowledge base from a file path.
     *
     * <pre>
     * Engine engine = Engine.loadFile("rules.teleos");
     * </pre>
     */
    public static Engine loadFile(String path) {
        Pointer h = TeleosLib.INSTANCE.teleos_from_file(path);
        if (h == null) throw new IllegalArgumentException("Teleos: failed to load file: " + path);
        return new Engine(h);
    }

    /**
     * Load a .teleos knowledge base from a string.
     *
     * <pre>
     * Engine engine = Engine.parse("""
     *     fact: alice is admin
     *     rule: if X is admin then X can access Y
     * """);
     * </pre>
     */
    public static Engine parse(String text) {
        Pointer h = TeleosLib.INSTANCE.teleos_from_str(text);
        if (h == null) throw new IllegalArgumentException("Teleos: failed to parse knowledge base.");
        return new Engine(h);
    }

    // ── Queries ───────────────────────────────────────────────────────────

    /**
     * Returns true if the goal can be proven from the knowledge base.
     *
     * <pre>engine.ask("alice can access document")  // true</pre>
     */
    public boolean ask(String goal) {
        ensureOpen();
        return TeleosLib.INSTANCE.teleos_ask(handle, goal) == 1;
    }

    /**
     * Returns a human-readable proof, or an explanation of why the goal fails.
     *
     * <pre>engine.why("alice can access document")</pre>
     */
    public String why(String goal) {
        ensureOpen();
        Pointer ptr = TeleosLib.INSTANCE.teleos_why(handle, goal);
        if (ptr == null) return "";
        try {
            return ptr.getString(0, "UTF-8");
        } finally {
            TeleosLib.INSTANCE.teleos_free_str(ptr);
        }
    }

    /**
     * Returns all solutions to a query containing variables (ALL CAPS terms).
     * Each element is a full solution string, e.g. "alice gets distinction".
     *
     * <pre>
     * engine.all("WHO gets distinction")
     *     .stream()
     *     .map(s -> s.split(" ")[0])  // → ["alice", "eve"]
     *     .toList();
     * </pre>
     */
    public java.util.List<String> all(String goal) {
        ensureOpen();
        Pointer ptr = TeleosLib.INSTANCE.teleos_all(handle, goal);
        if (ptr == null) return java.util.List.of();
        String raw;
        try {
            raw = ptr.getString(0, "UTF-8");
        } finally {
            TeleosLib.INSTANCE.teleos_free_str(ptr);
        }
        if (raw == null || raw.isEmpty()) return java.util.List.of();
        return java.util.Arrays.stream(raw.split("\n"))
            .filter(s -> !s.isEmpty())
            .toList();
    }

    // ── Mutations ─────────────────────────────────────────────────────────

    /**
     * Add a fact to the knowledge base at runtime.
     *
     * <pre>engine.addFact("dave is admin")</pre>
     */
    public void addFact(String fact) {
        ensureOpen();
        if (TeleosLib.INSTANCE.teleos_add_fact(handle, fact) != 0)
            throw new IllegalArgumentException("Teleos: failed to add fact: " + fact);
    }

    // ── Annotations ───────────────────────────────────────────────────────

    /**
     * Load rules defined via @TeleosFact and @TeleosRule annotations on a class.
     *
     * <pre>
     * {@literal @}TeleosFact("alice is admin")
     * {@literal @}TeleosRule("if X is admin then X can access Y")
     * public class AccessPolicy {}
     *
     * Engine engine = Engine.from(AccessPolicy.class);
     * </pre>
     */
    public static Engine from(Class<?> annotatedClass) {
        StringBuilder sb = new StringBuilder();
        for (TeleosFact f : annotatedClass.getAnnotationsByType(TeleosFact.class)) {
            sb.append("fact: ").append(f.value()).append('\n');
        }
        for (TeleosRule r : annotatedClass.getAnnotationsByType(TeleosRule.class)) {
            sb.append("rule: ").append(r.value()).append('\n');
        }
        return parse(sb.toString());
    }

    // ── AutoCloseable ─────────────────────────────────────────────────────

    @Override
    public void close() {
        if (handle != null) {
            TeleosLib.INSTANCE.teleos_free(handle);
            handle = null;
        }
    }

    private void ensureOpen() {
        if (handle == null) throw new IllegalStateException("Teleos engine is closed.");
    }
}
