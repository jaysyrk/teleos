//! teleos-core/src/main.rs  —  standalone CLI binary
//!
//! Usage:
//!   teleos-core run  <file.teleos>
//!   teleos-core test <file.teleos>
//!   teleos-core <file.teleos>          (shorthand for run)

use teleos_core::engine::Engine;
use teleos_core::parser::{parse_file, QueryKind};

fn run(path: &str) {
    let kb = match parse_file(path) {
        Ok(kb) => kb,
        Err(e) => {
            eprintln!("Error reading '{}': {}", path, e);
            std::process::exit(1);
        }
    };

    let queries = kb.queries.clone();
    let mut engine = Engine::new(kb);

    if queries.is_empty() {
        println!("(no ask:/why:/all: queries found in file)");
        return;
    }

    for query in &queries {
        let goal_str = query.terms.join(" ");
        match query.kind {
            QueryKind::Ask => {
                let result = engine.ask(&query.terms);
                println!("ask: {}", goal_str);
                println!("  \u{2192} {}\n", if result { "true" } else { "false" });
            }
            QueryKind::Why => {
                println!("why: {}", goal_str);
                println!("  \u{2192} {}\n", engine.why(&query.terms));
            }
            QueryKind::All => {
                let solutions = engine.all_solutions(&query.terms);
                println!("all: {}", goal_str);
                if solutions.is_empty() {
                    println!("  \u{2192} (none)");
                } else {
                    print!("  \u{2192} {}", solutions[0].join(" "));
                    for s in &solutions[1..] {
                        print!("\n     {}", s.join(" "));
                    }
                    println!();
                }
                println!();
            }
        }
    }
}

fn test(path: &str) -> i32 {
    let kb = match parse_file(path) {
        Ok(kb) => kb,
        Err(e) => {
            eprintln!("Error reading '{}': {}", path, e);
            return 1;
        }
    };

    if kb.asserts.is_empty() {
        println!("No assertions found in {}", path);
        return 0;
    }

    let asserts = kb.asserts.clone();
    let mut engine = Engine::new(kb);
    let mut passed = 0usize;
    let mut failed = 0usize;

    println!("Testing {}...\n", path);

    for assertion in &asserts {
        let goal_str = assertion.terms.join(" ");
        let result = engine.ask(&assertion.terms);
        let label = if assertion.expect { "true" } else { "not true" };
        if result == assertion.expect {
            println!("  PASS  {}  (expected {})", goal_str, label);
            passed += 1;
        } else {
            let got = if result { "true" } else { "not true" };
            println!("  FAIL  {}", goal_str);
            println!("        Expected: {}", label);
            println!("        Got:      {}", got);
            println!("        {}", engine.why(&assertion.terms));
            failed += 1;
        }
    }

    println!();
    if failed == 0 {
        println!("All {} assertions passed.", passed);
        0
    } else {
        println!("{}/{} passed, {} failed.", passed, passed + failed, failed);
        1
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();

    match args.get(1).map(|s| s.as_str()) {
        Some("run") => {
            if let Some(path) = args.get(2) {
                run(path);
            } else {
                eprintln!("Usage: teleos-core run <file.teleos>");
                std::process::exit(1);
            }
        }
        Some("test") => {
            if let Some(path) = args.get(2) {
                std::process::exit(test(path));
            } else {
                eprintln!("Usage: teleos-core test <file.teleos>");
                std::process::exit(1);
            }
        }
        Some(path) => run(path),
        None => {
            eprintln!("Usage:");
            eprintln!("  teleos-core run  <file.teleos>");
            eprintln!("  teleos-core test <file.teleos>");
            std::process::exit(1);
        }
    }
}
