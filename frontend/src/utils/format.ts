/**
 * Format ISK values with German locale (dots as thousand separators)
 * @param value - The ISK value to format
 * @param compact - Use compact notation (K, M, B)
 */
export function formatISK(value: number | null | undefined, compact = true): string {
  if (value === null || value === undefined) return '-';

  if (compact) {
    if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return value.toFixed(0);
  }

  // Full format with German locale (1.234.567,89)
  return value.toLocaleString('de-DE', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });
}

/**
 * Format percentage values
 */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  if (value > 1000) return '>1000%';
  return `${value.toFixed(1)}%`;
}

/**
 * Format volume in m3
 */
export function formatVolume(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M m³`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K m³`;
  return `${value.toFixed(0)} m³`;
}

/**
 * Format quantity with thousand separators
 */
export function formatQuantity(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return value.toLocaleString('de-DE');
}
