use std::collections::{HashMap, HashSet};
use crate::parser::{Condition, KnowledgeBase, Rule, Terms};

pub type Sub = HashMap<String, String>;

pub(crate) fn is_variable(term: &str) -> bool {
    let base = term.split('$').next().unwrap_or("");
    !base.is_empty() && base.chars().all(|c| c.is_ascii_alphabetic() && c.is_ascii_uppercase())
}

fn resolve(term: &str, sub: &Sub) -> String {
    let mut current = term.to_string();
    let mut seen = HashSet::new();
    loop {
        if seen.contains(&current) {
            break;
        }
        match sub.get(&current) {
            Some(val) => {
                seen.insert(current.clone());
                current = val.clone();
            }
            None => break,
        }
    }
    current
}

fn apply_sub(terms: &[String], sub: &Sub) -> Terms {
    terms.iter().map(|t| resolve(t, sub)).collect()
}

fn unify(t1: &[String], t2: &[String], sub: &Sub) -> Option<Sub> {
    if t1.len() != t2.len() {
        return None;
    }
    let mut result = sub.clone();
    for (a, b) in t1.iter().zip(t2.iter()) {
        let a = resolve(a, &result);
        let b = resolve(b, &result);
        if a == b {
            continue;
        } else if is_variable(&a) {
            result.insert(a, b);
        } else if is_variable(&b) {
            result.insert(b, a);
        } else {
            return None;
        }
    }
    Some(result)
}

fn rename_terms(terms: &[String], tag: usize) -> Terms {
    terms.iter()
        .map(|t| if is_variable(t) { format!("{}${}", t, tag) } else { t.clone() })
        .collect()
}

fn rename_condition(cond: &Condition, tag: usize) -> Condition {
    Condition { terms: rename_terms(&cond.terms, tag), negated: cond.negated }
}

#[derive(Clone)]
pub enum Reason { Fact, Rule, Negation, Comparison }

#[derive(Clone)]
pub struct ProofNode {
    pub conclusion: Terms,
    pub reason: Reason,
    pub children: Vec<ProofNode>,
}

impl ProofNode {
    pub fn explain(&self, depth: usize) -> String {
        let pad = "  ".repeat(depth);
        let text = self.conclusion.join(" ");
        match self.reason {
            Reason::Fact        => format!("{}'{}' \u{2014} known fact", pad, text),
            Reason::Negation    => format!("{}'not {}' \u{2014} cannot be proven (closed-world)", pad, text),
            Reason::Comparison  => format!("{}'{}' \u{2014} numeric comparison", pad, text),
            Reason::Rule => {
                let mut lines = vec![format!("{}'{}' \u{2014} proven because:", pad, text)];
                for child in &self.children {
                    lines.push(child.explain(depth + 1));
                }
                lines.join("\n")
            }
        }
    }
}

pub struct Engine {
    pub facts: Vec<Terms>,
    pub rules: Vec<Rule>,
    counter: usize,
}

impl Engine {
    pub fn new(kb: KnowledgeBase) -> Self {
        Engine { facts: kb.facts, rules: kb.rules, counter: 0 }
    }

    fn fresh_tag(&mut self) -> usize {
        self.counter += 1;
        self.counter
    }

    pub fn ask(&mut self, goal: &[String]) -> bool {
        self.prove_one(goal, &Sub::new(), 0).is_some()
    }

    pub fn why(&mut self, goal: &[String]) -> String {
        match self.prove_one(goal, &Sub::new(), 0) {
            Some((_, tree)) => tree.explain(0),
            None => self.explain_failure(goal),
        }
    }

    pub fn all_solutions(&mut self, goal: &[String]) -> Vec<Terms> {
        let results = self.prove_all(goal, &Sub::new(), 0);
        let mut seen = HashSet::new();
        let mut out = Vec::new();
        for (sub, _) in results {
            let concrete = apply_sub(goal, &sub);
            if seen.insert(concrete.clone()) {
                out.push(concrete);
            }
        }
        out
    }

    pub fn add_fact(&mut self, terms: Terms) {
        self.facts.push(terms);
    }

    pub fn add_rule(&mut self, rule: Rule) {
        self.rules.push(rule);
    }

    fn prove_one(&mut self, goal: &[String], sub: &Sub, depth: usize) -> Option<(Sub, ProofNode)> {
        self.prove_all(goal, sub, depth).into_iter().next()
    }

    fn prove_all(&mut self, goal: &[String], sub: &Sub, depth: usize) -> Vec<(Sub, ProofNode)> {
        if depth > 30 {
            return vec![];
        }
        let concrete = apply_sub(goal, sub);
        let mut results: Vec<(Sub, ProofNode)> = Vec::new();

        if concrete.len() == 3 {
            let op = concrete[1].as_str();
            if matches!(op, ">" | "<" | ">=" | "<=" | "=" | "!=") {
                if let (Ok(lhs), Ok(rhs)) = (
                    concrete[0].parse::<f64>(),
                    concrete[2].parse::<f64>(),
                ) {
                    let holds = match op {
                        ">"  => lhs > rhs,
                        "<"  => lhs < rhs,
                        ">=" => lhs >= rhs,
                        "<=" => lhs <= rhs,
                        "="  => (lhs - rhs).abs() < f64::EPSILON,
                        "!=" => (lhs - rhs).abs() >= f64::EPSILON,
                        _    => false,
                    };
                    if holds {
                        results.push((sub.clone(), ProofNode {
                            conclusion: concrete,
                            reason: Reason::Comparison,
                            children: vec![],
                        }));
                    }
                }
                return results;
            }
        }

        let facts = self.facts.clone();
        for fact in &facts {
            if let Some(new_sub) = unify(&concrete, fact, sub) {
                let node = ProofNode {
                    conclusion: apply_sub(goal, &new_sub),
                    reason: Reason::Fact,
                    children: vec![],
                };
                results.push((new_sub, node));
            }
        }

        let rules = self.rules.clone();
        for rule in &rules {
            let tag = self.fresh_tag();
            let head  = rename_terms(&rule.head, tag);
            let conds: Vec<Condition> = rule.conditions.iter()
                .map(|c| rename_condition(c, tag))
                .collect();

            if let Some(new_sub) = unify(&concrete, &head, sub) {
                let mut branch = self.prove_conds(&conds, &new_sub, depth, &concrete, vec![]);
                results.append(&mut branch);
            }
        }

        results
    }

    fn prove_conds(
        &mut self,
        conds: &[Condition],
        sub: &Sub,
        depth: usize,
        goal: &[String],
        children: Vec<ProofNode>,
    ) -> Vec<(Sub, ProofNode)> {
        if conds.is_empty() {
            return vec![(sub.clone(), ProofNode {
                conclusion: apply_sub(goal, sub),
                reason: Reason::Rule,
                children,
            })];
        }

    let (cond, rest) = conds.split_first().unwrap();
        let mut vec_results = Vec::new();

        if cond.negated {
            let has_proof = self.prove_one(&cond.terms, sub, depth + 1).is_some();
            if !has_proof {
                let neg_text = apply_sub(&cond.terms, sub);
                let mut new_children = children.clone();
                new_children.push(ProofNode {
                    conclusion: neg_text,
                    reason: Reason::Negation,
                    children: vec![],
                });
                let mut sub_results = self.prove_conds(rest, sub, depth, goal, new_children);
                vec_results.append(&mut sub_results);
            }
        } else {
            let pos_results = self.prove_all(&cond.terms, sub, depth + 1);
            for (new_sub, child_node) in pos_results {
                let mut new_children = children.clone();
                new_children.push(child_node);
                let mut sub_results = self.prove_conds(rest, &new_sub, depth, goal, new_children);
                vec_results.append(&mut sub_results);
            }
        }

        vec_results

    }
    fn explain_failure(&mut self, goal: &[String]) -> String {
        let concrete = apply_sub(goal, &Sub::new());
        let goal_text = concrete.join(" ");

        let mut best_passed: i32 = -1;
        let mut best_msg = String::new();
        let mut best_blocker: Option<ProofNode> = None;

        let rules = self.rules.clone();
        for rule in &rules {
            let tag = self.fresh_tag();
            let head  = rename_terms(&rule.head, tag);
            let conds: Vec<Condition> = rule.conditions.iter()
                .map(|c| rename_condition(c, tag))
                .collect();

            let sub = match unify(&concrete, &head, &Sub::new()) {
                Some(s) => s,
                None => continue,
            };

            let mut passed = 0i32;
            let mut current_sub = sub;
            let mut fail_msg: Option<String> = None;
            let mut blocker: Option<ProofNode> = None;

            for cond in &conds {
                if cond.negated {
                    if let Some((_, proof)) = self.prove_one(&cond.terms, &current_sub, 0) {
                        let neg_text = apply_sub(&cond.terms, &current_sub).join(" ");
                        fail_msg = Some(format!(
                            "'not {}' is blocked \u{2014} it CAN be proven:", neg_text
                        ));
                        blocker = Some(proof);
                        break;
                    }
                    passed += 1;
                } else {
                    match self.prove_one(&cond.terms, &current_sub, 0) {
                        Some((new_sub, _)) => {
                            current_sub = new_sub;
                            passed += 1;
                        }
                        None => {
                            let cond_text = apply_sub(&cond.terms, &current_sub).join(" ");
                            fail_msg = Some(format!("'{}' cannot be proven", cond_text));
                            break;
                        }
                    }
                }
            }

            if let Some(msg) = fail_msg {
                if passed > best_passed {
                    best_passed = passed;
                    best_msg = msg;
                    best_blocker = blocker;
                }
            }
        }

        if best_passed == -1 {
            return format!("Cannot prove: {}\n  No matching rules or facts found.", goal_text);
        }

        let mut lines = vec![
            format!("Cannot prove: {}", goal_text),
            format!("  Nearest rule failed because: {}", best_msg),
        ];
        if let Some(b) = best_blocker {
            for line in b.explain(2).lines() {
                lines.push(line.to_string());
            }
        }
        lines.join("\n")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parser::parse_str;

    fn e(src: &str) -> Engine {
        Engine::new(parse_str(src))
    }

    fn goal(s: &str) -> Terms {
        s.split_whitespace().map(|w| w.to_string()).collect()
    }

    #[test]
    fn direct_fact_true() {
        assert!(e("fact: sky is blue").ask(&goal("sky is blue")));
    }

    #[test]
    fn direct_fact_false() {
        assert!(!e("fact: sky is blue").ask(&goal("sky is red")));
    }

    #[test]
    fn multiple_facts() {
        let mut eng = e("fact: alice is admin\nfact: bob is user");
        assert!(eng.ask(&goal("alice is admin")));
        assert!(eng.ask(&goal("bob is user")));
        assert!(!eng.ask(&goal("alice is user")));
    }

    #[test]
    fn add_fact_at_runtime() {
        let mut eng = e("fact: alice is admin");
        assert!(!eng.ask(&goal("bob is admin")));
        eng.add_fact(goal("bob is admin"));
        assert!(eng.ask(&goal("bob is admin")));
    }

    #[test]
    fn single_rule() {
        let mut eng = e("fact: alice is admin\nrule: if X is admin then X can access Y");
        assert!(eng.ask(&goal("alice can access document")));
        assert!(!eng.ask(&goal("bob can access document")));
    }

    #[test]
    fn two_step_chain() {
        let src = "fact: fido is dog\n\
                   rule: if X is dog then X is mammal\n\
                   rule: if X is mammal then X has fur";
        let mut eng = e(src);
        assert!(eng.ask(&goal("fido is mammal")));
        assert!(eng.ask(&goal("fido has fur")));
    }

    #[test]
    fn negation_succeeds_when_absent() {
        let src = "fact: alice is user\n\
                   fact: charlie is user\n\
                   fact: charlie is banned\n\
                   rule: if X is user and not X is banned then X can post";
        let mut eng = e(src);
        assert!(eng.ask(&goal("alice can post")));
        assert!(!eng.ask(&goal("charlie can post")));
    }

    #[test]
    fn distinction_above_90() {
        let src = "fact: alice has score 95\n\
                   rule: if X has score S and S >= 90 then X gets distinction";
        assert!(e(src).ask(&goal("alice gets distinction")));
    }

    #[test]
    fn merit_between_75_and_90() {
        let src = "fact: charlie has score 80\n\
                   rule: if X has score S and S >= 75 and S < 90 then X gets merit";
        assert!(e(src).ask(&goal("charlie gets merit")));
    }

    #[test]
    fn fail_below_60() {
        let src = "fact: diana has score 55\n\
                   rule: if X has score S and S < 60 then X gets fail";
        assert!(e(src).ask(&goal("diana gets fail")));
    }

    #[test]
    fn boundary_exactly_90_is_distinction_not_merit() {
        let src = "fact: alice has score 90\n\
                   rule: if X has score S and S >= 90 then X gets distinction\n\
                   rule: if X has score S and S >= 75 and S < 90 then X gets merit";
        let mut eng = e(src);
        assert!(eng.ask(&goal("alice gets distinction")));
        assert!(!eng.ask(&goal("alice gets merit")));
    }

    #[test]
    fn all_comparison_operators() {
        let src = "fact: x has val 5\n\
                   rule: if x has val V and V {op} {rhs} then result is true\n";
        let cases: &[(&str, &str, bool)] = &[
            (">",  "4",  true),
            (">",  "5",  false),
            ("<",  "6",  true),
            ("<",  "5",  false),
            (">=", "5",  true),
            (">=", "6",  false),
            ("<=", "5",  true),
            ("<=", "4",  false),
            ("=",  "5",  true),
            ("=",  "6",  false),
            ("!=", "6",  true),
            ("!=", "5",  false),
        ];
        for &(op, rhs, expected) in cases {
            let rule_src = src
                .replace("{op}", op)
                .replace("{rhs}", rhs);
            let mut eng = e(&rule_src);
            assert_eq!(
                eng.ask(&goal("result is true")),
                expected,
                "V {op} {rhs} should be {expected}",
                op = op, rhs = rhs, expected = expected
            );
        }
    }

    #[test]
    fn all_solutions_basic() {
        let src = "fact: alice is admin\n\
                   fact: bob is admin\n\
                   fact: charlie is user";
        let mut eng = e(src);
        let solutions = eng.all_solutions(&goal("WHO is admin"));
        let mut names: Vec<String> = solutions.iter()
            .map(|s| s[0].clone())
            .collect();
        names.sort();
        assert_eq!(names, vec!["alice", "bob"]);
    }

    #[test]
    fn all_solutions_empty() {
        let mut eng = e("fact: alice is user");
        assert!(eng.all_solutions(&goal("WHO is admin")).is_empty());
    }

    #[test]
    fn assertions_pass() {
        use crate::parser::parse_str;
        let src = "fact: alice is admin\n\
                   rule: if X is admin then X can access Y\n\
                   assert: alice can access document\n\
                   assert not: bob can access document";
        let kb = parse_str(src);
        let mut eng = Engine::new(kb.clone());
        let mut passed = 0;
        let mut failed = 0;
        for a in &kb.asserts {
            let result = eng.ask(&a.terms);
            if result == a.expect { passed += 1; } else { failed += 1; }
        }
        assert_eq!(passed, 2);
        assert_eq!(failed, 0);
    }

    fn run_example_assertions(path: &str) -> (usize, usize) {
        let kb = crate::parser::parse_file(path).expect("parse failed");
        let mut eng = Engine::new(kb.clone());
        let mut passed = 0;
        let mut failed = 0;
        for a in &kb.asserts {
            let result = eng.ask(&a.terms);
            if result == a.expect { passed += 1; } else { failed += 1; }
        }
        (passed, failed)
    }

    #[test]
    fn example_access_all_pass() {
        let (passed, failed) = run_example_assertions("../examples/access.teleos");
        assert_eq!(failed, 0, "{failed} assertion(s) failed");
        assert_eq!(passed, 7);
    }

    #[test]
    fn example_grades_all_pass() {
        let (passed, failed) = run_example_assertions("../examples/grades.teleos");
        assert_eq!(failed, 0, "{failed} assertion(s) failed");
        assert_eq!(passed, 9);
    }

    #[test]
    fn example_import_demo_all_pass() {
        let (passed, failed) = run_example_assertions("../examples/import-demo.teleos");
        assert_eq!(failed, 0, "{failed} assertion(s) failed");
        assert_eq!(passed, 6);
    }
}
