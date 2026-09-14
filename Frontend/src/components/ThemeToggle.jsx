import React from 'react';
import { useFinnyTheme } from '../services/useFinnyTheme';

/**
 * Visual Theme Toggle Button matching the original finny-agent-ui design.
 * Renders a frosted glass circle with smooth rotate and scale hover effect.
 * Uses ☀ for Dark mode (indicating click to switch to Light) and ☾ for Light mode.
 */
export const ThemeToggle = ({ className = '' }) => {
  const { isLight, toggleTheme } = useFinnyTheme();

  return (
    <button
      type="button"
      className={`theme-toggle ${className}`}
      onClick={toggleTheme}
      title={isLight ? 'Switch to Dark theme' : 'Switch to Light theme'}
      aria-label="Toggle visual theme"
    >
      <span id="themeIcon" className="select-none">
        {isLight ? '☾' : '☀'}
      </span>
    </button>
  );
};
