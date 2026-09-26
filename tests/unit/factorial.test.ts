import { factorial } from '../../src/factorial';

describe('factorial', () => {
  test('factorial(0) returns 1', () => {
    expect(factorial(0)).toBe(1);
  });

  test('factorial(1) returns 1', () => {
    expect(factorial(1)).toBe(1);
  });

  test('factorial(5) returns 120', () => {
    expect(factorial(5)).toBe(120);
  });

  test('factorial(10) returns 3628800', () => {
    expect(factorial(10)).toBe(3628800);
  });

  test('throws error for negative numbers', () => {
    expect(() => factorial(-1)).toThrow('Input must be a non-negative integer');
  });

  test('throws error for non-integers', () => {
    expect(() => factorial(1.5)).toThrow('Input must be a non-negative integer');
  });
});