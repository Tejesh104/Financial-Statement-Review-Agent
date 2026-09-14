// src/tests/components/GoogleAuth.test.jsx
// Unit tests for Google Sign-In flow in LoginPage and authContext
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { AuthProvider, useAuth } from '../../services/authContext.jsx';
import { DocumentProvider } from '../../services/documentContext.jsx';

// -----------------------------------------------------------------------
// Mock axios to intercept API calls without a real network
// -----------------------------------------------------------------------
vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    post: vi.fn(),
    get: vi.fn(),
    defaults: { headers: { common: {} } },
  };
  return { default: mockAxios };
});

// -----------------------------------------------------------------------
// Helper: minimal wrapper providing all providers a component needs
// -----------------------------------------------------------------------
const Wrapper = ({ children }) => (
  <AuthProvider>
    <DocumentProvider>
      <MemoryRouter initialEntries={['/login']}>{children}</MemoryRouter>
    </DocumentProvider>
  </AuthProvider>
);

// -----------------------------------------------------------------------
// Tests for authContext.loginWithGoogle()
// -----------------------------------------------------------------------
describe('authContext.loginWithGoogle()', () => {
  let getAuth;

  const AuthConsumer = () => {
    getAuth = useAuth();
    return null;
  };

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  test('demo fallback: loginWithGoogle(null) succeeds and sets auth state', async () => {
    render(
      <Wrapper>
        <AuthConsumer />
      </Wrapper>
    );

    let result;
    await act(async () => {
      result = await getAuth.loginWithGoogle(null, false);
    });

    expect(result.success).toBe(true);
    expect(getAuth.isAuthenticated).toBe(true);
    expect(getAuth.user).not.toBeNull();
    expect(getAuth.user.auth_provider).toBe('google');
  });

  test('demo fallback: token is stored in localStorage', async () => {
    render(
      <Wrapper>
        <AuthConsumer />
      </Wrapper>
    );

    await act(async () => {
      await getAuth.loginWithGoogle(null, false);
    });

    const storedToken = localStorage.getItem('fsra_token');
    expect(storedToken).toBeTruthy();
    expect(storedToken).toMatch(/^demo_google_token_/);
  });

  test('real credential path: sends id_token to backend and stores JWT', async () => {
    const axios = (await import('axios')).default;
    axios.post.mockResolvedValueOnce({
      data: {
        access_token: 'real-jwt-token-from-backend',
        user: {
          id: 'user-123',
          email: 'test@example.com',
          name: 'Test User',
          picture_url: null,
        },
      },
    });

    render(
      <Wrapper>
        <AuthConsumer />
      </Wrapper>
    );

    let result;
    await act(async () => {
      result = await getAuth.loginWithGoogle('fake-google-id-token', false);
    });

    expect(result.success).toBe(true);
    expect(axios.post).toHaveBeenCalledWith(
      '/auth/google',
      { id_token: 'fake-google-id-token' }
    );
    const storedToken = localStorage.getItem('fsra_token');
    expect(storedToken).toBe('real-jwt-token-from-backend');
    expect(getAuth.user.email).toBe('test@example.com');
    expect(getAuth.user.auth_provider).toBe('google');
  });

  test('real credential path: backend error returns success=false with message', async () => {
    const axios = (await import('axios')).default;
    axios.post.mockRejectedValueOnce({
      response: { data: { detail: 'Invalid or expired Google ID token.' } },
    });

    render(
      <Wrapper>
        <AuthConsumer />
      </Wrapper>
    );

    let result;
    await act(async () => {
      result = await getAuth.loginWithGoogle('bad-token', false);
    });

    expect(result.success).toBe(false);
    expect(result.error).toBe('Invalid or expired Google ID token.');
    expect(getAuth.isAuthenticated).toBe(false);
  });

  test('logout clears auth state and storage', async () => {
    render(
      <Wrapper>
        <AuthConsumer />
      </Wrapper>
    );

    await act(async () => {
      await getAuth.loginWithGoogle(null, false);
    });
    expect(getAuth.isAuthenticated).toBe(true);

    act(() => {
      getAuth.logout();
    });

    expect(getAuth.isAuthenticated).toBe(false);
    expect(getAuth.user).toBeNull();
    expect(localStorage.getItem('fsra_token')).toBeNull();
    expect(sessionStorage.getItem('fsra_token')).toBeNull();
  });
});

// -----------------------------------------------------------------------
// Tests for demo login (should not be broken)
// -----------------------------------------------------------------------
describe('authContext.login() demo flow', () => {
  let getAuth;

  const AuthConsumer = () => {
    getAuth = useAuth();
    return null;
  };

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  test('demo login with email/password succeeds', async () => {
    render(
      <Wrapper>
        <AuthConsumer />
      </Wrapper>
    );

    let result;
    await act(async () => {
      result = await getAuth.login('auditor@example.com', 'anypassword', false);
    });

    expect(result.success).toBe(true);
    expect(getAuth.isAuthenticated).toBe(true);
    expect(getAuth.user.email).toBe('auditor@example.com');
    expect(getAuth.user.auth_provider).toBe('local');
  });
});
