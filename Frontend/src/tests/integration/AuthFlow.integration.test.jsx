// src/tests/integration/AuthFlow.integration.test.jsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, test, expect } from 'vitest';
import { LoginPage } from '../../pages/LoginPage.jsx';
import { AuthProvider } from '../../services/authContext.jsx';

describe('Auth Integration Test', () => {
  test('successful login redirects to dashboard', async () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<div>Dashboard Destination</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    const emailInput = screen.getByPlaceholderText(/enter your email/i);
    const passwordInput = screen.getByPlaceholderText(/••••••••••••/i);
    fireEvent.change(emailInput, { target: { value: 'demo@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    const loginButton = screen.getByRole('button', { name: /sign in to finny/i });
    fireEvent.click(loginButton);

    await waitFor(() => {
      expect(screen.getByText('Dashboard Destination')).toBeInTheDocument();
    });
  });
});

