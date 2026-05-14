//! teleos-core/src/lib.rs
//!
//! Public Rust API + C FFI exports.
//!
//! The FFI lets any language (Python, Go, Lua, JS via WASM, C, ...) load
//! teleos_core.dll / .so and call the engine without knowing Rust.
//!
//! C header (for reference):
//!
//!   TeleosHandle* teleos_from_str(const char* text);
//!   TeleosHandle* teleos_from_file(const char* path);
//!   int           teleos_ask(TeleosHandle*, const char* query);  // 1=true 0=false -1=err
//!   char*         teleos_why(TeleosHandle*, const char* query);  // caller must teleos_free_str
//!   char*         teleos_all(TeleosHandle*, const char* query);  // newline-separated
//!   int           teleos_add_fact(TeleosHandle*, const char* fact);
//!   void          teleos_free_str(char* s);
//!   void          teleos_free(TeleosHandle*);

pub mod engine;
pub mod parser;

#[cfg(feature = "wasm")]
pub mod wasm;

use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;

use engine::Engine;
use parser::{parse_file, parse_str};

// ── Opaque handle ─────────────────────────────────────────────────────────────

pub struct TeleosHandle {
    pub engine: Engine,
}

// ── Constructors ──────────────────────────────────────────────────────────────

/// Create an engine from a .teleos string.
#[no_mangle]
pub extern "C" fn teleos_from_str(text: *const c_char) -> *mut TeleosHandle {
    if text.is_null() { return ptr::null_mut(); }
    let s = unsafe { CStr::from_ptr(text) };
    let s = match s.to_str() { Ok(s) => s, Err(_) => return ptr::null_mut() };
    let kb = parse_str(s);
    Box::into_raw(Box::new(TeleosHandle { engine: Engine::new(kb) }))
}

/// Create an engine from a .teleos file path.
#[no_mangle]
pub extern "C" fn teleos_from_file(path: *const c_char) -> *mut TeleosHandle {
    if path.is_null() { return ptr::null_mut(); }
    let s = unsafe { CStr::from_ptr(path) };
    let s = match s.to_str() { Ok(s) => s, Err(_) => return ptr::null_mut() };
    match parse_file(s) {
        Ok(kb) => Box::into_raw(Box::new(TeleosHandle { engine: Engine::new(kb) })),
        Err(_) => ptr::null_mut(),
    }
}

// ── Queries ───────────────────────────────────────────────────────────────────

/// Returns 1 (true), 0 (false), or -1 (error).
#[no_mangle]
pub extern "C" fn teleos_ask(handle: *mut TeleosHandle, query: *const c_char) -> i32 {
    let (h, q) = match get_handle_query(handle, query) { Some(x) => x, None => return -1 };
    if h.engine.ask(&q) { 1 } else { 0 }
}

/// Returns a heap-allocated explanation string.  Caller must call teleos_free_str.
#[no_mangle]
pub extern "C" fn teleos_why(handle: *mut TeleosHandle, query: *const c_char) -> *mut c_char {
    let (h, q) = match get_handle_query(handle, query) { Some(x) => x, None => return ptr::null_mut() };
    let result = h.engine.why(&q);
    str_to_ptr(result)
}

/// Returns newline-separated solutions.  Caller must call teleos_free_str.
#[no_mangle]
pub extern "C" fn teleos_all(handle: *mut TeleosHandle, query: *const c_char) -> *mut c_char {
    let (h, q) = match get_handle_query(handle, query) { Some(x) => x, None => return ptr::null_mut() };
    let solutions = h.engine.all_solutions(&q);
    let result = solutions.iter().map(|s| s.join(" ")).collect::<Vec<_>>().join("\n");
    str_to_ptr(result)
}

// ── Mutations ─────────────────────────────────────────────────────────────────

/// Add a fact at runtime.  Returns 0 on success, -1 on error.
#[no_mangle]
pub extern "C" fn teleos_add_fact(handle: *mut TeleosHandle, fact: *const c_char) -> i32 {
    if handle.is_null() || fact.is_null() { return -1; }
    let h = unsafe { &mut *handle };
    let s = unsafe { CStr::from_ptr(fact) };
    let s = match s.to_str() { Ok(s) => s, Err(_) => return -1 };
    let terms: Vec<String> = s.split_whitespace().map(|t| t.to_string()).collect();
    h.engine.add_fact(terms);
    0
}

// ── Memory management ─────────────────────────────────────────────────────────

/// Free a string returned by teleos_why or teleos_all.
#[no_mangle]
pub extern "C" fn teleos_free_str(s: *mut c_char) {
    if !s.is_null() {
        unsafe { drop(CString::from_raw(s)) };
    }
}

/// Free an engine handle.
#[no_mangle]
pub extern "C" fn teleos_free(handle: *mut TeleosHandle) {
    if !handle.is_null() {
        unsafe { drop(Box::from_raw(handle)) };
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn get_handle_query<'a>(
    handle: *mut TeleosHandle,
    query: *const c_char,
) -> Option<(&'a mut TeleosHandle, Vec<String>)> {
    if handle.is_null() || query.is_null() { return None; }
    let h = unsafe { &mut *handle };
    let s = unsafe { CStr::from_ptr(query) };
    let s = s.to_str().ok()?;
    let terms = s.split_whitespace().map(|t| t.to_string()).collect();
    Some((h, terms))
}

fn str_to_ptr(s: String) -> *mut c_char {
    match CString::new(s) {
        Ok(cs) => cs.into_raw(),
        Err(_) => ptr::null_mut(),
    }
}
