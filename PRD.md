# Teleos Product Requirements Document (PRD)

## Overview
Teleos is a plain-language logic engine that lets users define, query, and explain business rules in English-like syntax, decoupled from application code.

## Problem Statement
- Business logic is often hard-coded, making it difficult to audit, update, or explain.
- Non-developers struggle to understand or modify rules embedded in code.

## Goals
- Allow rules to be written and maintained in plain language files.
- Support explainable reasoning ("why" queries) and variable binding ("all" queries).
- Enable multi-language integration via FFI and CLI.

## Key Features
- .teleos file syntax for facts, rules, queries, assertions
- Backward chaining inference engine
- Proof/explanation output for failed queries
- CLI and Python API
- Language bindings (Rust, Go, JS, C++, C#, Java)

## Non-Goals
- Full natural language understanding (focus is on structured, readable syntax)
- Real-time distributed rule evaluation

## User Stories
- As a developer, I want to move business rules out of code for easier updates.
- As a product manager, I want to audit and explain why a decision was made.
- As a QA, I want to test rule sets independently from the app.

## Metrics
- Number of rules/facts loaded
- Query response time
- Proof explanation coverage

## Trade-offs
- Prioritizes explainability and portability over raw inference speed.
- Focuses on English-like syntax, not full natural language parsing.
