import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './services/authContext';
import { DocumentProvider } from './services/documentContext';
import { DashboardLayout } from './layouts/DashboardLayout';

import { FinnyLandingPage } from './pages/FinnyLandingPage';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { DashboardPage } from './pages/DashboardPage';
import { UploadPage } from './pages/UploadPage';
import { VerificationPage } from './pages/VerificationPage';
import { AgentProcessingPage } from './pages/AgentProcessingPage';
import { AnalysisDashboardPage } from './pages/AnalysisDashboardPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';
import { HistoryPage } from './pages/HistoryPage';
import { RiskAnalysisPage } from './pages/RiskAnalysisPage';

function RequireAuth({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function App() {
  return (
    <AuthProvider>
      <DocumentProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Finny Agent landing and authentication entry points */}
            <Route path="/" element={<FinnyLandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            {/* Authenticated Dashboard Workflow Layout */}
            <Route element={<RequireAuth><DashboardLayout /></RequireAuth>}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/verification" element={<VerificationPage />} />
              <Route path="/agent-processing" element={<AgentProcessingPage />} />
              <Route path="/review" element={<AgentProcessingPage />} />
              <Route path="/analysis" element={<AnalysisDashboardPage />} />
              <Route path="/previous-year-analysis" element={<AnalysisDashboardPage />} />
              <Route path="/risk" element={<RiskAnalysisPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>

            {/* Fallback to Login */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </DocumentProvider>
    </AuthProvider>
  );
}

export default App;
