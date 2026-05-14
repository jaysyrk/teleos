/**
 * JS/WASM binding integration test for Teleos.
 * Run with: node test.cjs
 */

const { Teleos, parse } = require('./dist/index.js');

let passed = 0;
let failed = 0;

function assert(desc, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (ok) {
    console.log(`  PASS  ${desc}`);
    passed++;
  } else {
    console.error(`  FAIL  ${desc}`);
    console.error(`        expected: ${JSON.stringify(expected)}`);
    console.error(`        actual:   ${JSON.stringify(actual)}`);
    failed++;
  }
}

function assertContains(desc, actual, substr) {
  const ok = typeof actual === 'string' && actual.includes(substr);
  if (ok) {
    console.log(`  PASS  ${desc}`);
    passed++;
  } else {
    console.error(`  FAIL  ${desc}`);
    console.error(`        expected to contain: ${substr}`);
    console.error(`        actual: ${actual}`);
    failed++;
  }
}

// ── Test 1: Basic fact ────────────────────────────────────────────────────────
console.log('\nBasic facts');
{
  const e = parse('fact: alice is admin');
  assert('ask true', e.ask('alice is admin'), true);
  assert('ask false', e.ask('bob is admin'), false);
  e.dispose();
}

// ── Test 2: Rule chaining ─────────────────────────────────────────────────────
console.log('\nRule chaining');
{
  const e = parse(`
fact: alice is admin
rule: if X is admin then X can access files
`);
  assert('derived fact', e.ask('alice can access files'), true);
  assert('non-matching', e.ask('bob can access files'), false);
  e.dispose();
}

// ── Test 3: Negation ──────────────────────────────────────────────────────────
console.log('\nNegation');
{
  const e = parse(`
fact: alice is active
rule: if X is active and not X is banned then X can login
`);
  assert('negation true', e.ask('alice can login'), true);
  assert('negation false (banned)', (() => {
    const e2 = parse(`
fact: bob is active
fact: bob is banned
rule: if X is active and not X is banned then X can login
`);
    const r = e2.ask('bob can login');
    e2.dispose();
    return r;
  })(), false);
  e.dispose();
}

// ── Test 4: Numeric comparisons ───────────────────────────────────────────────
console.log('\nNumeric comparisons');
{
  const e = parse(`
fact: alice score 95
rule: if X score N and N > 90 then X gets distinction
`);
  assert('numeric > true', e.ask('alice gets distinction'), true);
  const e2 = parse(`
fact: bob score 70
rule: if X score N and N > 90 then X gets distinction
`);
  assert('numeric > false', e2.ask('bob gets distinction'), false);
  e.dispose();
  e2.dispose();
}

// ── Test 5: all() single variable ─────────────────────────────────────────────
console.log('\nall() queries');
{
  const e = parse(`
fact: alice score 95
fact: eve score 92
fact: bob score 70
rule: if X score N and N > 90 then X gets distinction
`);
  const result = e.ask('alice gets distinction');
  assert('alice distinction', result, true);

  const allResult = e.all('WHO gets distinction');
  assert('all single-var length', Array.isArray(allResult) && allResult.length, 2);
  assert('alice in all', Array.isArray(allResult) && allResult.includes('alice'), true);
  assert('eve in all', Array.isArray(allResult) && allResult.includes('eve'), true);
  e.dispose();
}

// ── Test 6: why() ─────────────────────────────────────────────────────────────
console.log('\nwhy() explanations');
{
  const e = parse(`
fact: alice is admin
rule: if X is admin then X can access files
`);
  const proof = e.why('alice can access files');
  assertContains('why contains alice', proof, 'alice');
  const fail = e.why('bob can access files');
  assertContains('why fail contains bob or cannot', fail, 'bob');
  e.dispose();
}

// ── Test 7: addFact() at runtime ──────────────────────────────────────────────
console.log('\naddFact() at runtime');
{
  const e = parse(`
rule: if X is admin then X can access files
`);
  assert('before addFact', e.ask('dave can access files'), false);
  e.addFact('dave is admin');
  assert('after addFact', e.ask('dave can access files'), true);
  e.dispose();
}

// ── Test 8: parse() convenience function ──────────────────────────────────────
console.log('\nparse() convenience');
{
  const e = parse('fact: charlie is manager');
  assert('parse() convenience', e.ask('charlie is manager'), true);
  e.dispose();
}

// ── Summary ───────────────────────────────────────────────────────────────────
console.log(`\n${'─'.repeat(50)}`);
console.log(`JS/WASM binding: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
