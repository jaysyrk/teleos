//! teleos-core/src/parser.rs
//!
//! Reads .teleos syntax and turns it into Rust data structures.
//! Mirrors the logic in the Python teleos/parser.py exactly.

// ── Types ────────────────────────────────────────────────────────────────────

pub type Terms = Vec<String>;

#[derive(Clone, Debug)]
pub struct Condition {
    pub terms: Terms,
    pub negated: bool,
}

#[derive(Clone, Debug)]
pub struct Rule {
    pub head: Terms,
    pub conditions: Vec<Condition>,
}

#[derive(Clone, Debug)]
pub struct Query {
    pub terms: Terms,
    pub kind: QueryKind,
}

#[derive(Clone, Debug)]
pub enum QueryKind {
    Ask,
    Why,
    All,
}

#[derive(Clone, Debug)]
pub struct Assert {
    pub terms: Terms,
    pub expect: bool, // true = must be provable, false = must NOT be provable
}

#[derive(Default, Debug, Clone)]
pub struct KnowledgeBase {
    pub facts: Vec<Terms>,
    pub rules: Vec<Rule>,
    pub queries: Vec<Query>,
    pub asserts: Vec<Assert>,
}

// ── Parsing helpers ───────────────────────────────────────────────────────────

fn parse_terms(text: &str) -> Terms {
    text.split_whitespace().map(|s| s.to_string()).collect()
}

fn parse_conditions(text: &str) -> Vec<Condition> {
    text.split(" and ")
        .map(|part| part.trim())
        .filter(|part| !part.is_empty())
        .map(|part| {
            if part.to_lowercase().starts_with("not ") {
                Condition { terms: parse_terms(&part[4..]), negated: true }
            } else {
                Condition { terms: parse_terms(part), negated: false }
            }
        })
        .collect()
}

// ── Line parser ───────────────────────────────────────────────────────────────

pub enum KbItem {
    Fact(Terms),
    Rule(Rule),
    Query(Query),
    Assert(Assert),
    Import(String),
}

pub fn parse_line(line: &str) -> Option<KbItem> {
    let line = line.trim();
    if line.is_empty() || line.starts_with('#') {
        return None;
    }
    let colon = line.find(':')?;
    let keyword = line[..colon].trim().to_lowercase();
    let rest = line[colon + 1..].trim();

    match keyword.as_str() {
        "fact" => Some(KbItem::Fact(parse_terms(rest))),

        "rule" => {
            // Strip leading "if "
            let body = if rest.to_lowercase().starts_with("if ") {
                &rest[3..]
            } else {
                rest
            };
            let then_pos = body.find(" then ")?;
            let cond_text = &body[..then_pos];
            let head_text = &body[then_pos + 6..];
            Some(KbItem::Rule(Rule {
                head: parse_terms(head_text),
                conditions: parse_conditions(cond_text),
            }))
        }

        "ask" => Some(KbItem::Query(Query { terms: parse_terms(rest), kind: QueryKind::Ask })),
        "why" => Some(KbItem::Query(Query { terms: parse_terms(rest), kind: QueryKind::Why })),
        "all" => Some(KbItem::Query(Query { terms: parse_terms(rest), kind: QueryKind::All })),

        "assert" => {
            let negated = rest.to_lowercase().starts_with("not ");
            let body = if negated { rest[4..].trim() } else { rest };
            Some(KbItem::Assert(Assert { terms: parse_terms(body), expect: !negated }))
        }
        "assert not" => {
            Some(KbItem::Assert(Assert { terms: parse_terms(rest), expect: false }))
        }
        "import" => {
            Some(KbItem::Import(rest.to_string()))
        }

        _ => None,
    }
}

// ── Entry points ──────────────────────────────────────────────────────────────

pub fn parse_str(text: &str) -> KnowledgeBase {
    parse_str_with_dir(text, None)
}

fn parse_str_with_dir(text: &str, base_dir: Option<&std::path::Path>) -> KnowledgeBase {
    let mut kb = KnowledgeBase::default();
    for line in text.lines() {
        match parse_line(line) {
            Some(KbItem::Fact(f))    => kb.facts.push(f),
            Some(KbItem::Rule(r))    => kb.rules.push(r),
            Some(KbItem::Query(q))   => kb.queries.push(q),
            Some(KbItem::Assert(a))  => kb.asserts.push(a),
            Some(KbItem::Import(p))  => {
                if let Some(dir) = base_dir {
                    let import_path = if std::path::Path::new(&p).is_absolute() {
                        std::path::PathBuf::from(&p)
                    } else {
                        dir.join(&p)
                    };
                    if let Ok(imported) = parse_file(import_path.to_str().unwrap_or("")) {
                        kb.facts.extend(imported.facts);
                        kb.rules.extend(imported.rules);
                        kb.asserts.extend(imported.asserts);
                    }
                }
            }
            None => {}
        }
    }
    kb
}

pub fn parse_file(path: &str) -> Result<KnowledgeBase, std::io::Error> {
    let content = std::fs::read_to_string(path)?;
    let base_dir = std::path::Path::new(path).parent();
    Ok(parse_str_with_dir(&content, base_dir))
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn t(s: &str) -> Terms {
        s.split_whitespace().map(|w| w.to_string()).collect()
    }

    #[test]
    fn parse_fact() {
        let kb = parse_str("fact: alice is admin");
        assert_eq!(kb.facts.len(), 1);
        assert_eq!(kb.facts[0], t("alice is admin"));
    }

    #[test]
    fn parse_rule_simple() {
        let kb = parse_str("rule: if X is admin then X can access Y");
        assert_eq!(kb.rules.len(), 1);
        let rule = &kb.rules[0];
        assert_eq!(rule.head, t("X can access Y"));
        assert_eq!(rule.conditions.len(), 1);
        assert!(!rule.conditions[0].negated);
    }

    #[test]
    fn parse_rule_negated_condition() {
        let kb = parse_str("rule: if X is user and not X is banned then X can post");
        let rule = &kb.rules[0];
        assert_eq!(rule.conditions.len(), 2);
        assert!(!rule.conditions[0].negated);
        assert!(rule.conditions[1].negated);
    }

    #[test]
    fn parse_assert_true_and_false() {
        let kb = parse_str("assert: alice is admin\nassert not: bob is admin");
        assert_eq!(kb.asserts.len(), 2);
        assert!(kb.asserts[0].expect);
        assert!(!kb.asserts[1].expect);
        assert_eq!(kb.asserts[0].terms, t("alice is admin"));
    }

    #[test]
    fn parse_query_kinds() {
        let kb = parse_str("ask: alice is admin\nwhy: bob is user\nall: WHO is admin");
        assert_eq!(kb.queries.len(), 3);
        assert!(matches!(kb.queries[0].kind, QueryKind::Ask));
        assert!(matches!(kb.queries[1].kind, QueryKind::Why));
        assert!(matches!(kb.queries[2].kind, QueryKind::All));
    }

    #[test]
    fn parse_comment_ignored() {
        let kb = parse_str("# this is a comment\nfact: sky is blue");
        assert_eq!(kb.facts.len(), 1);
    }

    #[test]
    fn parse_empty_string() {
        let kb = parse_str("");
        assert!(kb.facts.is_empty());
        assert!(kb.rules.is_empty());
    }
}
