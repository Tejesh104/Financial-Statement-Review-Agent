// src/tests/utils/currency.test.js
import { describe, it, expect } from 'vitest';
import { formatCurrency, getCurrencySymbol, extractCurrencyMeta } from '../../utils/currency.js';

const usdMeta = { currency_code: 'USD', currency_symbol: '$', scale: 'USD' };
const eurMeta = { currency_code: 'EUR', currency_symbol: '€', scale: 'EUR' };
const inrMeta = { currency_code: 'INR', currency_symbol: '₹', scale: 'INR' };

describe('formatCurrency', () => {
  it('formats positive number with USD', () => {
    expect(formatCurrency(1234.56, usdMeta)).toBe('$1,234.56 USD');
  });
  it('formats negative number with EUR', () => {
    expect(formatCurrency(-9876.5, eurMeta)).toBe('-€9,876.50 EUR');
  });
  it('handles zero value', () => {
    expect(formatCurrency(0, usdMeta)).toBe('$0.00 USD');
  });
  it('returns N/A for null/undefined', () => {
    expect(formatCurrency(null, usdMeta)).toBe('N/A');
    expect(formatCurrency(undefined, usdMeta)).toBe('N/A');
  });
  it('returns N/A for non‑numeric string', () => {
    expect(formatCurrency('abc', usdMeta)).toBe('N/A');
  });
  it('formats large numbers with compact option', () => {
    expect(formatCurrency(2500000000, usdMeta, { compact: true, includeScale: false })).toBe('$2.50B');
    expect(formatCurrency(1500000, usdMeta, { compact: true, includeScale: false })).toBe('$1.50M');
    expect(formatCurrency(7500, usdMeta, { compact: true, includeScale: false })).toBe('$7.5K');
  });
  it('omits scale when includeScale false', () => {
    expect(formatCurrency(123, usdMeta, { includeScale: false })).toBe('$123.00');
  });
});

describe('getCurrencySymbol', () => {
  it('returns symbol from meta', () => {
    expect(getCurrencySymbol(usdMeta)).toBe('$');
    expect(getCurrencySymbol(eurMeta)).toBe('€');
  });
  it('returns empty string when meta missing', () => {
    expect(getCurrencySymbol(null)).toBe('');
    expect(getCurrencySymbol({})).toBe('');
  });
});

describe('extractCurrencyMeta', () => {
  it('extracts from nested currency_meta', () => {
    const src = { currency_meta: { currency_code: 'GBP', currency_symbol: '£', scale: 'GBP', is_specified: true } };
    expect(extractCurrencyMeta(src)).toMatchObject({ currency_code: 'GBP', currency_symbol: '£', scale: 'GBP', is_specified: true });
  });
  it('falls back to direct properties', () => {
    const src = { currency: 'CAD', currency_symbol: 'C$', scale: 'CAD' };
    expect(extractCurrencyMeta(src)).toMatchObject({ currency_code: 'CAD', currency_symbol: 'C$', scale: 'CAD', is_specified: true });
  });
  it('returns defaults when no data', () => {
    expect(extractCurrencyMeta(null)).toMatchObject({ currency_code: null, currency_symbol: null, scale: null, is_specified: false });
  });
});
