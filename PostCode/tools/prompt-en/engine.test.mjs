import test from 'node:test';
import assert from 'node:assert/strict';
import { protectLiterals, restoreLiterals } from './engine.mjs';

test('code, paths, quoted UI labels and numbers survive unchanged', () => {
  const original = 'Измени `src/app/page.tsx`, добавь кнопку «Оплатить», 3 тарифа за 299.90.\n```ts\nconst label = "Русский";\n```';
  const protectedInput = protectLiterals(original);
  assert.equal(protectedInput.literals.length, 5);
  const rewritten = protectedInput.literals.map(item => item.key).join(' ');
  const restored = restoreLiterals(rewritten, protectedInput.literals);
  for (const literal of protectedInput.literals) assert.ok(restored.includes(literal.value));
});

test('missing and duplicated literals block the rewrite', () => {
  const { literals } = protectLiterals('Оставь «Поехали» и 48 часов.');
  assert.throws(() => restoreLiterals('Keep the label.', literals), /lost or duplicated/);
  assert.throws(() => restoreLiterals(`${literals[0].key} ${literals[0].key} ${literals[1].key}`, literals), /lost or duplicated/);
});

test('a non-English answer or invented marker is rejected', () => {
  assert.throws(() => restoreLiterals('Сделай страницу.', []), /English/);
  assert.throws(() => restoreLiterals('Use __KEEP_ZZ__.', []), /invented/);
});

test('literal replacement does not interpret JavaScript replacement tokens', () => {
  const { literals } = protectLiterals('Оставь "$&" как есть.');
  assert.equal(restoreLiterals(`Keep ${literals[0].key}.`, literals), 'Keep "$&".');
});

test('English contractions are not mistaken for quoted literals', () => {
  const { literals } = protectLiterals("Don't change the UI, and don't add payments.");
  assert.equal(literals.length, 0);
});
