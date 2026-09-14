import { useState, useEffect } from 'react';

/**
 * Reads the current theme from persistence.
 * Checks both 'finny_theme' and 'finny-theme' for complete compatibility.
 * Default theme is 'dark'.
 */
export const getSavedTheme = () => {
  if (typeof window === 'undefined') return 'dark';
  return localStorage.getItem('finny_theme') || localStorage.getItem('finny-theme') || 'dark';
};

/**
 * Applies the given theme to document.documentElement and document.body,
 * updates localStorage (both keys), and dispatches an event for cross-component reactivity.
 */
export const applyTheme = (theme) => {
  if (typeof window === 'undefined') return;
  const isLight = theme === 'light';
  const targetTheme = isLight ? 'light' : 'dark';

  localStorage.setItem('finny_theme', targetTheme);
  localStorage.setItem('finny-theme', targetTheme);

  if (isLight) {
    document.documentElement.classList.remove('dark');
    document.documentElement.classList.add('light');
    document.body.classList.remove('dark');
    document.body.classList.add('light');
  } else {
    document.documentElement.classList.remove('light');
    document.documentElement.classList.add('dark');
    document.body.classList.remove('light');
    document.body.classList.add('dark');
  }

  window.dispatchEvent(new CustomEvent('finny-theme-change', { detail: targetTheme }));
};

/**
 * Shared React hook for managing the Finny application theme.
 * Guarantees a single source of truth across all components and pages.
 */
export const useFinnyTheme = () => {
  const [theme, setTheme] = useState(getSavedTheme);

  useEffect(() => {
    const handleThemeChange = (event) => {
      if (event.detail) {
        setTheme(event.detail);
      }
    };

    const handleStorage = (event) => {
      if (event.key === 'finny_theme' || event.key === 'finny-theme') {
        const updated = event.newValue || 'dark';
        setTheme(updated);
        applyTheme(updated);
      }
    };

    window.addEventListener('finny-theme-change', handleThemeChange);
    window.addEventListener('storage', handleStorage);

    return () => {
      window.removeEventListener('finny-theme-change', handleThemeChange);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const changeTheme = (newTheme) => {
    applyTheme(newTheme);
    setTheme(newTheme);
  };

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light';
    changeTheme(nextTheme);
  };

  return {
    theme,
    isLight: theme === 'light',
    changeTheme,
    toggleTheme,
  };
};
