// src/tests/components/FinnyLandingPage.test.jsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { FinnyLandingPage } from '../../pages/FinnyLandingPage.jsx';
import { LoginPage } from '../../pages/LoginPage.jsx';
import { AuthProvider } from '../../services/authContext.jsx';

describe('FinnyLandingPage component', () => {
  it('does not auto-redirect and stays on the logo page', async () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}> 
          <Routes>
            <Route path="/" element={<FinnyLandingPage />} />
            <Route path="/login" element={<LoginPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    // Verify logo and title are present
    expect(screen.getAllByText(/FINNY/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Your Financial/i)).toBeInTheDocument();

    // Verify login page content is not shown
    expect(screen.queryByText(/Secure Review Authentication/i)).not.toBeInTheDocument();

    // Wait a brief period to ensure no automatic redirect occurs
    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(screen.getAllByText(/FINNY/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Secure Review Authentication/i)).not.toBeInTheDocument();
  });

  it('navigates to login when user clicks sign in', async () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}> 
          <Routes>
            <Route path="/" element={<FinnyLandingPage />} />
            <Route path="/login" element={<LoginPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );
    // Verify logo text is present
    const logoMatches = screen.getAllByText(/FINNY/i);
    expect(logoMatches.length).toBeGreaterThan(0);

    // Verify sign in button is present
    const signInButtons = screen.getAllByRole('button', { name: /sign in/i });
    expect(signInButtons.length).toBeGreaterThan(0);

    // Click Sign In
    fireEvent.click(signInButtons[0]);
    await waitFor(() => expect(screen.getByText(/Secure Review Authentication/i)).toBeInTheDocument());
  });
});
