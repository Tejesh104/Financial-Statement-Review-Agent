/**
 * Centralized Currency Formatting & Metadata Utility for FINNY
 *
 * Ensures all financial figures render using the uploaded statement's detected currency
 * (e.g. ₹ / INR, € / EUR, £ / GBP, $ / USD) without hardcoding USD or inventing currencies.
 */

export const CURRENCY_SYMBOLS = {
  INR: '₹',
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
  CAD: 'C$',
  AUD: 'A$',
  CHF: 'CHF',
  CNY: '¥',
};

/**
 * Extracts and normalizes currency metadata from a document, analysis, or statement object.
 */
export const extractCurrencyMeta = (source) => {
  if (!source) {
    return {
      currency_code: null,
      currency_symbol: null,
      currency_name: null,
      scale: null,
      is_specified: false,
    };
  }

  // 1. Check nested currency_meta
  if (source.currency_meta && typeof source.currency_meta === 'object') {
    return {
      currency_code: source.currency_meta.currency_code || null,
      currency_symbol: source.currency_meta.currency_symbol || null,
      currency_name: source.currency_meta.currency_name || null,
      scale: source.currency_meta.scale || null,
      is_specified: Boolean(source.currency_meta.is_specified),
    };
  }

  // 2. Check details.currency_meta
  if (source.details && source.details.currency_meta && typeof source.details.currency_meta === 'object') {
    return {
      currency_code: source.details.currency_meta.currency_code || null,
      currency_symbol: source.details.currency_meta.currency_symbol || null,
      currency_name: source.details.currency_meta.currency_name || null,
      scale: source.details.currency_meta.scale || null,
      is_specified: Boolean(source.details.currency_meta.is_specified),
    };
  }

  // 3. Fallback to direct properties on statement or document
  const code = source.currency || source.currency_code || null;
  const sym = source.currency_symbol || (code ? CURRENCY_SYMBOLS[code] : null) || null;
  const scale = source.monetary_scale || source.scale || null;
  const isSpecified = Boolean(code || sym);

  return {
    currency_code: code,
    currency_symbol: sym,
    currency_name: code,
    scale,
    is_specified: isSpecified,
  };
};

/**
 * Returns the detected currency symbol or empty string.
 */
export const getCurrencySymbol = (currencyMeta) => {
  const meta = extractCurrencyMeta(currencyMeta);
  return meta.currency_symbol || '';
};

/**
 * Formats a monetary value dynamically using the detected statement currency and scale.
 * When currency is unspecified, renders neutrally without hardcoded dollar signs.
 */
export const formatCurrency = (value, currencyMeta = null, options = {}) => {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
    return 'N/A';
  }

  const {
    compact = false,
    precision = 2,
    includeScale = true,
  } = options;

  const num = Number(value);
  const meta = extractCurrencyMeta(currencyMeta);
  const symbol = meta.currency_symbol || '';
  const scale = meta.scale;

  const absVal = Math.abs(num);
  const sign = num < 0 ? '-' : '';
  let numStr = '';

  const isMagnitudeScale = Boolean(scale && /million|thousand|billion|crore|lakh/i.test(scale));
  if (compact && !isMagnitudeScale) {
    if (absVal >= 1_000_000_000) {
      numStr = `${(absVal / 1_000_000_000).toFixed(2)}B`;
    } else if (absVal >= 1_000_000) {
      numStr = `${(absVal / 1_000_000).toFixed(2)}M`;
    } else if (absVal >= 1_000) {
      numStr = `${(absVal / 1_000).toFixed(1)}K`;
    } else {
      numStr = absVal.toLocaleString(undefined, {
        minimumFractionDigits: precision,
        maximumFractionDigits: precision,
      });
    }
  } else {
    numStr = absVal.toLocaleString(undefined, {
      minimumFractionDigits: precision,
      maximumFractionDigits: precision,
    });
  }

  const formatted = symbol ? `${sign}${symbol}${numStr}` : `${sign}${numStr}`;

  if (includeScale && scale) {
    return `${formatted} ${scale}`;
  }

  return formatted;
};

/**
 * Returns a human-readable badge configuration for the detected currency.
 */
export const getCurrencyBadgeInfo = (currencyMeta) => {
  const meta = extractCurrencyMeta(currencyMeta);
  if (!meta.is_specified) {
    return {
      text: 'Currency not specified',
      code: 'UNSPECIFIED',
      symbol: '',
      scale: meta.scale || null,
      isSpecified: false,
    };
  }

  const code = meta.currency_code || 'CURRENCY';
  const sym = meta.currency_symbol ? ` (${meta.currency_symbol})` : '';
  const scale = meta.scale ? ` · ${meta.scale}` : '';

  return {
    text: `${code}${sym}${scale}`,
    code: meta.currency_code,
    symbol: meta.currency_symbol,
    scale: meta.scale,
    isSpecified: true,
  };
};
