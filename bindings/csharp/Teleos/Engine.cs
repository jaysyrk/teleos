using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

namespace Teleos
{
    /// <summary>
    /// A loaded Teleos knowledge base, ready to query.
    ///
    /// <code>
    /// using Teleos;
    ///
    /// using var engine = Teleos.Engine.LoadFile("rules.teleos");
    ///
    /// bool result = engine.Ask("alice can access document");
    /// string  why = engine.Why("alice can access document");
    /// var  people = engine.All("WHO gets distinction");
    /// </code>
    /// </summary>
    public sealed class Engine : IDisposable
    {
        // ── Native imports ────────────────────────────────────────────────

        private const string Lib = "teleos_core";

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        private static extern IntPtr teleos_from_str([MarshalAs(UnmanagedType.LPUTF8Str)] string text);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        private static extern IntPtr teleos_from_file([MarshalAs(UnmanagedType.LPUTF8Str)] string path);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        private static extern int teleos_ask(IntPtr handle, [MarshalAs(UnmanagedType.LPUTF8Str)] string goal);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        private static extern IntPtr teleos_why(IntPtr handle, [MarshalAs(UnmanagedType.LPUTF8Str)] string goal);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        private static extern IntPtr teleos_all(IntPtr handle, [MarshalAs(UnmanagedType.LPUTF8Str)] string goal);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        private static extern int teleos_add_fact(IntPtr handle, [MarshalAs(UnmanagedType.LPUTF8Str)] string fact);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        private static extern void teleos_free_str(IntPtr s);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        private static extern void teleos_free(IntPtr handle);

        // ── State ─────────────────────────────────────────────────────────

        private IntPtr _handle;
        private bool _disposed;

        private Engine(IntPtr handle)
        {
            if (handle == IntPtr.Zero)
                throw new InvalidOperationException("Teleos: failed to create engine.");
            _handle = handle;
        }

        // ── Constructors ──────────────────────────────────────────────────

        /// <summary>Load a .teleos knowledge base from a file path.</summary>
        public static Engine LoadFile(string path)
        {
            var handle = teleos_from_file(path);
            if (handle == IntPtr.Zero)
                throw new ArgumentException($"Teleos: failed to load file: {path}");
            return new Engine(handle);
        }

        /// <summary>Load a .teleos knowledge base from a string.</summary>
        public static Engine Parse(string text)
        {
            var handle = teleos_from_str(text);
            if (handle == IntPtr.Zero)
                throw new ArgumentException("Teleos: failed to parse knowledge base.");
            return new Engine(handle);
        }

        // ── Queries ───────────────────────────────────────────────────────

        /// <summary>
        /// Returns true if the goal can be proven from the knowledge base.
        /// <code>engine.Ask("alice can access document")  // true</code>
        /// </summary>
        public bool Ask(string goal)
        {
            EnsureNotDisposed();
            return teleos_ask(_handle, goal) == 1;
        }

        /// <summary>
        /// Returns a human-readable proof, or an explanation of why the goal fails.
        /// </summary>
        public string Why(string goal)
        {
            EnsureNotDisposed();
            var ptr = teleos_why(_handle, goal);
            if (ptr == IntPtr.Zero) return string.Empty;
            try
            {
                return Marshal.PtrToStringUTF8(ptr) ?? string.Empty;
            }
            finally
            {
                teleos_free_str(ptr);
            }
        }

        /// <summary>
        /// Returns all solutions to a query containing variables (ALL CAPS terms).
        /// Each entry is a full solution string, e.g. "alice gets distinction".
        /// Use LINQ to extract specific fields:
        /// <code>
        /// engine.All("WHO gets distinction")
        ///     .Select(s => s.Split(' ')[0])  // → ["alice", "eve"]
        /// </code>
        /// </summary>
        public IEnumerable<string> All(string goal)
        {
            EnsureNotDisposed();
            var ptr = teleos_all(_handle, goal);
            if (ptr == IntPtr.Zero) yield break;

            string raw;
            try { raw = Marshal.PtrToStringUTF8(ptr) ?? string.Empty; }
            finally { teleos_free_str(ptr); }

            if (string.IsNullOrEmpty(raw)) yield break;

            foreach (var line in raw.Split('\n'))
            {
                if (!string.IsNullOrEmpty(line))
                    yield return line;
            }
        }

        // ── Mutations ─────────────────────────────────────────────────────

        /// <summary>
        /// Add a fact to the knowledge base at runtime.
        /// <code>engine.AddFact("dave is admin")</code>
        /// </summary>
        public void AddFact(string fact)
        {
            EnsureNotDisposed();
            if (teleos_add_fact(_handle, fact) != 0)
                throw new InvalidOperationException($"Teleos: failed to add fact: {fact}");
        }

        // ── IDisposable ───────────────────────────────────────────────────

        public void Dispose()
        {
            if (!_disposed && _handle != IntPtr.Zero)
            {
                teleos_free(_handle);
                _handle = IntPtr.Zero;
                _disposed = true;
            }
        }

        private void EnsureNotDisposed()
        {
            if (_disposed) throw new ObjectDisposedException(nameof(Engine));
        }
    }
}
