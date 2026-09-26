/**
 * Calcula el factorial de un entero no negativo de forma recursiva.
 * @param n - Entero no negativo.
 * @returns El factorial de n.
 * @throws Error si n es negativo o no es entero.
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

export { factorial };
