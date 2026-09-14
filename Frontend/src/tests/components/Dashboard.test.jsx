// src/tests/components/Dashboard.test.jsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, test, expect } from 'vitest';
import { DashboardPage } from '../../pages/DashboardPage.jsx';
import { AuthProvider } from '../../services/authContext.jsx';
import { DocumentProvider } from '../../services/documentContext.jsx';
import { BrowserRouter } from 'react-router-dom';

describe('Dashboard Component', () => {
  test('renders dashboard component without crashing', () => {
    render(
      <AuthProvider>
        <DocumentProvider>
          <BrowserRouter>
            <DashboardPage />
          </BrowserRouter>
        </DocumentProvider>
      </AuthProvider>
    );
    expect(screen.getByText(/FINNY DASHBOARD/i)).toBeInTheDocument();
  });
});

