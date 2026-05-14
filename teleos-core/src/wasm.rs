//! teleos-core/src/wasm.rs
//!
//! wasm-bindgen exports for the browser / Node.js WASM target.
//! Built with: wasm-pack build --target web  (browser)
//!             wasm-pack build --target nodejs (Node.js)

use wasm_bindgen::prelude::*;
use crate::engine::Engine;
use crate::parser::parse_str;

/// A Teleos knowledge base loaded in WASM.
#[wasm_bindgen]
pub struct TeleosEngine {
    engine: Engine,
}

#[wasm_bindgen]
impl TeleosEngine {
    /// Load a knowledge base from a .teleos source string.
    #[wasm_bindgen(constructor)]
    pub fn new(text: &str) -> TeleosEngine {
        TeleosEngine { engine: Engine::new(parse_str(text)) }
    }

    /// Returns true if the query can be proven.
    pub fn ask(&mut self, query: &str) -> bool {
        let terms = terms(query);
        self.engine.ask(&terms)
    }

    /// Returns a proof explanation, or a failure diagnosis.
    pub fn why(&mut self, query: &str) -> String {
        let terms = terms(query);
        self.engine.why(&terms)
    }

    /// Returns newline-separated solution strings (one per match).
    pub fn all(&mut self, query: &str) -> String {
        let terms = terms(query);
        self.engine.all_solutions(&terms)
            .iter()
            .map(|s| s.join(" "))
            .collect::<Vec<_>>()
            .join("\n")
    }

    /// Add a fact at runtime.
    pub fn add_fact(&mut self, fact: &str) {
        self.engine.add_fact(terms(fact));
    }
}

fn terms(s: &str) -> Vec<String> {
    s.split_whitespace().map(|t| t.to_string()).collect()
}
