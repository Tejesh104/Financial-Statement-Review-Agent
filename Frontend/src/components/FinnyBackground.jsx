import React from 'react';

export const FinnyBackground = () => (
  <div className="finny-app-background" aria-hidden="true">
    {/* Static decorative layers reuse the landing page's starfield atmosphere without
        adding a second render loop to authenticated financial pages. */}
    <div className="finny-app-stars finny-app-stars-primary" />
    <div className="finny-app-stars finny-app-stars-secondary" />
    <div className="finny-app-orb" />
  </div>
);
