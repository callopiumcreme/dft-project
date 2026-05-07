import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

// ── Replicate pure functions from route.ts ───────────────────────────────────

function clean(v, max = 500) {
  if (typeof v !== 'string') return '';
  return v
    .replace(/[\r\n]/g, ' ')
    .replace(/[<>]/g, '')
    .trim()
    .slice(0, max);
}

function isValidEmail(s) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

const WINDOW_MS = 10 * 60 * 1000;
const MAX_PER_WINDOW = 3;

function makeRateLimiter() {
  const rateMap = new Map();
  let lastClean = 0;
  return function rateLimited(ip) {
    const now = Date.now();
    if (now - lastClean > WINDOW_MS) {
      for (const [k, v] of rateMap) if (now > v.resetAt) rateMap.delete(k);
      lastClean = now;
    }
    const entry = rateMap.get(ip);
    if (!entry || now > entry.resetAt) {
      rateMap.set(ip, { hits: 1, resetAt: now + WINDOW_MS });
      return false;
    }
    if (entry.hits >= MAX_PER_WINDOW) return true;
    entry.hits++;
    return false;
  };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('clean() — header injection prevention', () => {
  test('strips \\r\\n (email header injection)', () => {
    const result = clean('Test\r\nBcc: evil@test.com');
    assert.equal(result.includes('\r'), false, 'must not contain \\r');
    assert.equal(result.includes('\n'), false, 'must not contain \\n');
  });

  test('replaces \\r\\n with spaces, keeps rest', () => {
    const result = clean('Test\r\nBcc: evil@test.com');
    assert.equal(result, 'Test  Bcc: evil@test.com');
  });

  test('strips < > (HTML injection)', () => {
    const result = clean('<script>alert(1)</script>');
    assert.equal(result.includes('<'), false);
    assert.equal(result.includes('>'), false);
    assert.equal(result, 'scriptalert(1)/script');
  });

  test('returns empty string for non-string input', () => {
    assert.equal(clean(null), '');
    assert.equal(clean(undefined), '');
    assert.equal(clean(42), '');
    assert.equal(clean({}), '');
  });

  test('truncates to max length', () => {
    const long = 'a'.repeat(600);
    assert.equal(clean(long, 500).length, 500);
  });

  test('trims whitespace', () => {
    assert.equal(clean('  hello  '), 'hello');
  });

  test('lone \\n stripped', () => {
    const result = clean('line1\nline2');
    assert.equal(result.includes('\n'), false);
  });
});

describe('rateLimited() — 3 req/10min per IP', () => {
  test('first 3 requests allowed', () => {
    const rateLimited = makeRateLimiter();
    assert.equal(rateLimited('1.2.3.4'), false, 'req 1 allowed');
    assert.equal(rateLimited('1.2.3.4'), false, 'req 2 allowed');
    assert.equal(rateLimited('1.2.3.4'), false, 'req 3 allowed');
  });

  test('4th request from same IP blocked (429)', () => {
    const rateLimited = makeRateLimiter();
    rateLimited('1.2.3.4'); // 1
    rateLimited('1.2.3.4'); // 2
    rateLimited('1.2.3.4'); // 3
    assert.equal(rateLimited('1.2.3.4'), true, '4th request must be blocked');
  });

  test('5th request also blocked', () => {
    const rateLimited = makeRateLimiter();
    rateLimited('1.2.3.4');
    rateLimited('1.2.3.4');
    rateLimited('1.2.3.4');
    rateLimited('1.2.3.4'); // blocked
    assert.equal(rateLimited('1.2.3.4'), true, '5th also blocked');
  });

  test('different IPs have independent counters', () => {
    const rateLimited = makeRateLimiter();
    rateLimited('1.1.1.1');
    rateLimited('1.1.1.1');
    rateLimited('1.1.1.1');
    // 1.1.1.1 exhausted; 2.2.2.2 still fresh
    assert.equal(rateLimited('2.2.2.2'), false, 'different IP still allowed');
    assert.equal(rateLimited('1.1.1.1'), true,  '1.1.1.1 still blocked');
  });
});

describe('isValidEmail()', () => {
  test('valid emails pass', () => {
    assert.equal(isValidEmail('user@example.com'), true);
    assert.equal(isValidEmail('a+b@x.io'), true);
  });

  test('invalid emails fail', () => {
    assert.equal(isValidEmail('notanemail'), false);
    assert.equal(isValidEmail('@example.com'), false);
    assert.equal(isValidEmail('user@'), false);
    assert.equal(isValidEmail(''), false);
  });
});
