/**
 * Calculates the factorial of a non-negative integer recursively.
 * @param n - The non-negative integer to calculate factorial for.
 * @returns The factorial of n.
 * @throws Error if n is negative or not an integer.
 */
function factorial(n: number): number {
  if (n < 0 || !Number.isInteger(n)) {
    throw new Error('Input must be a non-negative integer');
  }

  if (n === 0 || n === 1) {
    return 1;
  }

  return n * factorial(n - 1);
}

// Run tests when executed directly
if (require.main === module) {
  const assert = require('assert');

  assert.strictEqual(factorial(0), 1);
  assert.strictEqual(factorial(1), 1);
  assert.strictEqual(factorial(5), 120);
  assert.strictEqual(factorial(10), 3628800);

  let errorThrown = false;
  try {
    factorial(-1);
  } catch (error) {
    errorThrown = true;
  }
  assert.strictEqual(errorThrown, true);

  errorThrown = false;
  try {
    factorial(1.5);
  } catch (error) {
    errorThrown = true;
  }
  assert.strictEqual(errorThrown, true);

  console.log('All tests passed!');
}

export { factorial };