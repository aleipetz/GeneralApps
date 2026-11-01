import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  answer,
  emptyRankings,
  isDone,
  pivotIndex,
  placeInRankings,
  rankedEntries,
  remainingComparisons,
  scoreAt,
  startSession,
} from '../src/ranking.ts';

/** Insert `value` into a list sorted best-first using a simulated user. */
function insertWithOracle(list: number[], value: number): { index: number; asked: number } {
  let s = startSession('liked', list.map(String));
  let asked = 0;
  while (!isDone(s)) {
    const pivot = list[pivotIndex(s)];
    asked++;
    s = answer(s, value > pivot ? 'new' : value < pivot ? 'pivot' : 'tie');
  }
  return { index: s.lo, asked };
}

test('binary insertion finds the correct position for every slot', () => {
  const list = [90, 80, 70, 60, 50, 40, 30];
  for (const v of [95, 85, 75, 65, 55, 45, 35, 25]) {
    const { index, asked } = insertWithOracle(list, v);
    const expected = list.filter((x) => x > v).length;
    assert.equal(index, expected, `value ${v}`);
    assert.ok(asked <= 3, `asked ${asked} questions for 7 items`);
  }
});

test('first item in a bucket needs no comparisons', () => {
  const s = startSession('fine', []);
  assert.ok(isDone(s));
  assert.equal(remainingComparisons(s), 0);
});

test('tie places the new item right after the pivot', () => {
  const { index } = insertWithOracle([90, 80, 70], 80);
  assert.equal(index, 2);
});

test('building a ranking item by item yields a sorted order', () => {
  const values = [42, 7, 99, 63, 15, 88, 3, 51, 70, 26];
  const sorted: number[] = [];
  for (const v of values) {
    const { index } = insertWithOracle(sorted, v);
    sorted.splice(index, 0, v);
  }
  assert.deepEqual(sorted, [...values].sort((a, b) => b - a));
});

test('placeInRankings moves items between buckets', () => {
  let r = emptyRankings();
  r = placeInRankings(r, 'a', 'liked', 0);
  r = placeInRankings(r, 'b', 'liked', 0);
  r = placeInRankings(r, 'c', 'fine', 0);
  assert.deepEqual(r.liked, ['b', 'a']);
  r = placeInRankings(r, 'b', 'disliked', 0);
  assert.deepEqual(r, { liked: ['a'], fine: ['c'], disliked: ['b'] });
});

test('scores stay inside bucket ranges and decrease with rank', () => {
  assert.equal(scoreAt('liked', 0, 1), 10);
  assert.equal(scoreAt('liked', 0, 4), 10);
  assert.ok(scoreAt('liked', 3, 4) >= 6.8);
  assert.ok(scoreAt('fine', 0, 3) <= 6.7);
  assert.ok(scoreAt('disliked', 2, 3) >= 0);

  let r = emptyRankings();
  ['a', 'b', 'c'].forEach((id, i) => (r = placeInRankings(r, id, 'liked', i)));
  ['d', 'e'].forEach((id, i) => (r = placeInRankings(r, id, 'fine', i)));
  r = placeInRankings(r, 'f', 'disliked', 0);
  const entries = rankedEntries(r);
  assert.deepEqual(entries.map((e) => e.id), ['a', 'b', 'c', 'd', 'e', 'f']);
  assert.deepEqual(entries.map((e) => e.rank), [1, 2, 3, 4, 5, 6]);
  for (let i = 1; i < entries.length; i++) assert.ok(entries[i].score < entries[i - 1].score);
});
