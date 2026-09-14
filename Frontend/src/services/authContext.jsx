import React, { createContext, useContext, useState } from 'react';
import api from './api';

const AuthContext = createContext(null);

const getStoredToken = () => {
  return localStorage.getItem('fsra_token') || sessionStorage.getItem('fsra_token') || null;
};

const getStoredUser = () => {
  const savedUser = localStorage.getItem('fsra_user') || sessionStorage.getItem('fsra_user');
  return savedUser ? JSON.parse(savedUser) : null;
};

const storeSession = (access_token, userData, rememberMe = false) => {
  localStorage.setItem('fsra_token', access_token);
  localStorage.setItem('fsra_user', JSON.stringify(userData));
  sessionStorage.setItem('fsra_token', access_token);
  sessionStorage.setItem('fsra_user', JSON.stringify(userData));
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => getStoredUser());
  const [token, setToken] = useState(() => getStoredToken());
  const [loginLoading, setLoginLoading] = useState(false);
  const [signupLoading, setSignupLoading] = useState(false);

  const updateUser = (updatedData) => {
    setUser(updatedData);
    localStorage.setItem('fsra_user', JSON.stringify(updatedData));
    sessionStorage.setItem('fsra_user', JSON.stringify(updatedData));
  };

  const updateSession = (newToken, updatedUser) => {
    if (newToken) {
      setToken(newToken);
      localStorage.setItem('fsra_token', newToken);
      sessionStorage.setItem('fsra_token', newToken);
    }
    if (updatedUser) {
      updateUser(updatedUser);
    }
  };

  const login = async (email, password, rememberMe = true) => {
    setLoginLoading(true);
    try {
      const trimmedEmail = email.trim().toLowerCase();
      const namePart = trimmedEmail.split('@')[0];
      const formattedName = namePart
        .replace(/[._]/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase()) || 'Demo Auditor';

      const demoUser = {
        id: 'demo-user-1',
        email: trimmedEmail,
        full_name: formattedName,
        role: 'Senior Financial Analyst',
        auth_provider: 'local',
      };
      const demoToken = `demo_token_${Date.now()}`;

      setToken(demoToken);
      setUser(demoUser);
      storeSession(demoToken, demoUser, rememberMe);
      return { success: true };
    } catch (err) {
      return {
        success: false,
        error: 'Invalid email or password.',
      };
    } finally {
      setLoginLoading(false);
    }
  };

  const loginWithGoogle = async (googleCredential = null, rememberMe = true) => {
    setLoginLoading(true);
    try {
      if (googleCredential && typeof googleCredential === 'string') {
        // Exchange real Google ID token with backend
        const response = await api.post('/auth/google', { id_token: googleCredential });
        const { access_token, user: apiUser } = response.data;
        const normalizedUser = {
          id: apiUser.id,
          email: apiUser.email,
          full_name: apiUser.name || apiUser.email.split('@')[0],
          role: 'Senior Financial Analyst',
          auth_provider: 'google',
          picture_url: apiUser.picture_url,
        };
        setToken(access_token);
        setUser(normalizedUser);
        storeSession(access_token, normalizedUser, rememberMe);
        return { success: true };
      }

      // Offline / Developer Demo Fallback
      const demoUser = {
        id: 'demo-google-user',
        email: 'alex.morgan.auditor@gmail.com',
        full_name: 'Alex Morgan, CPA',
        role: 'Senior Financial Analyst',
        auth_provider: 'google',
      };
      const demoToken = `demo_google_token_${Date.now()}`;

      setToken(demoToken);
      setUser(demoUser);
      storeSession(demoToken, demoUser, rememberMe);
      return { success: true };
    } catch (err) {
      const errorMsg =
        err?.response?.data?.detail ||
        (err?.code === 'ERR_NETWORK'
          ? 'Authentication server is unreachable. Please verify the backend is running on port 8001.'
          : null) ||
        (err?.message && !err.message.includes('token') && !err.message.includes('secret')
          ? err.message
          : 'Google authentication failed. Please try again.');
      return {
        success: false,
        error: errorMsg,
      };
    } finally {
      setLoginLoading(false);
    }
  };

  const signup = async (full_name, email, password, confirm_password, rememberMe = true) => {
    setSignupLoading(true);
    try {
      const trimmedEmail = email.trim().toLowerCase();
      const demoUser = {
        id: `demo-user-${Date.now()}`,
        email: trimmedEmail,
        full_name: full_name.trim() || 'Demo Auditor',
        role: 'Senior Financial Analyst',
        auth_provider: 'local',
      };
      const demoToken = `demo_token_${Date.now()}`;

      setToken(demoToken);
      setUser(demoUser);
      storeSession(demoToken, demoUser, rememberMe);
      return { success: true };
    } catch (err) {
      return {
        success: false,
        error: 'Registration failed. Please try again.',
      };
    } finally {
      setSignupLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('fsra_token');
    localStorage.removeItem('fsra_user');
    sessionStorage.removeItem('fsra_token');
    sessionStorage.removeItem('fsra_user');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        updateUser,
        updateSession,
        token,
        loading: loginLoading || signupLoading,
        loginLoading,
        signupLoading,
        login,
        loginWithGoogle,
        signup,
        logout,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
