use wasm_bindgen::prelude::*;
use crate::engine::Engine;
use crate::parser::parse_str;

#[wasm_bindgen]
pub struct TeleosEngine {
    engine: Engine,
}

#[wasm_bindgen]
impl TeleosEngine {
    #[wasm_bindgen(constructor)]
    pub fn new(text: &str) -> TeleosEngine {
        TeleosEngine { engine: Engine::new(parse_str(text)) }
    }

    pub fn ask(&mut self, query: &str) -> bool {
        let terms = terms(query);
        self.engine.ask(&terms)
    }

    pub fn why(&mut self, query: &str) -> String {
        let terms = terms(query);
        self.engine.why(&terms)
    }

        pub fn all(&mut self, query: &str) -> String {
        let terms = terms(query);
        let solutions = self.engine.all_solutions(&terms);

        let mut var_indices = Vec::new();
        for (i, term) in terms.iter().enumerate() {
            if crate::engine::is_variable(term) {
                var_indices.push((term.clone(), i));
            }
        }

        if var_indices.is_empty() {
            if solutions.is_empty() {
                "".to_string()
            } else {
                "true".to_string()
            }
        } else if var_indices.len() == 1 {
            let idx = var_indices[0].1;
            solutions.iter()
                .map(|sol| sol[idx].clone())
                .collect::<Vec<_>>()
                .join("\n")
        } else {
            let mut lines = Vec::new();
            for sol in &solutions {
                let mut pairs = Vec::new();
                for (name, idx) in &var_indices {
                    pairs.push(format!("{}={}", name, sol[*idx]));
                }
                lines.push(pairs.join(" "));
            }
            lines.join("\n")
        }
    }

    pub fn add_fact(&mut self, fact: &str) {
        self.engine.add_fact(terms(fact));
    }
}

fn terms(s: &str) -> Vec<String> {
    s.split_whitespace().map(|t| t.to_string()).collect()
}
