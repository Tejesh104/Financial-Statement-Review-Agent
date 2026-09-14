import React from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { TopBar } from '../components/TopBar';
import { FinnyAssistant } from '../components/FinnyAssistant';
import { FinnyBackground } from '../components/FinnyBackground';
import { ChevronRight, Home } from 'lucide-react';

export const DashboardLayout = () => {
  const location = useLocation();

  // Generate breadcrumbs from path
  const pathnames = location.pathname.split('/').filter((x) => x);
  const breadcrumbNameMap = {
    dashboard: 'Analytics Dashboard',
    upload: 'Upload Financial Statement',
    verification: 'Document Authenticity & Integrity Screening',
    'agent-processing': 'AI Agent Multi-Stage Pipeline',
    analysis: 'Previous-Year & Ratio Analysis',
    'previous-year-analysis': 'Previous-Year Analysis',
    risk: 'Risk & Anomalies',
    reports: 'Executive Review Reports',
    history: 'Filing History & Audit Log',
    settings: 'System & Model Settings',
  };

  return (
    <div className="flex h-screen bg-transparent text-slate-100 overflow-hidden font-sans antialiased">
      {/* Keep the authenticated workflow in the same Finny environment while
          leaving decorative animation behind navigation and page content. */}
      <FinnyBackground />

      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar />

        {/* Breadcrumb Bar */}
        <div className="h-10 bg-[#0B1120]/50 border-b border-slate-800/60 px-6 flex items-center space-x-2 text-xs text-slate-400">
          <Link to="/dashboard" className="flex items-center hover:text-slate-200 transition-colors">
            <Home className="w-3.5 h-3.5 mr-1 text-slate-400" />
            <span>Home</span>
          </Link>
          {pathnames.map((segment, index) => {
            const isLast = index === pathnames.length - 1;
            const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`;
            const title = breadcrumbNameMap[segment] || segment.replace('-', ' ');

            return (
              <React.Fragment key={routeTo}>
                <ChevronRight className="w-3 h-3 text-slate-400" />
                {isLast ? (
                  <span className="text-cyan-400 font-medium capitalize font-mono text-[11px]">{title}</span>
                ) : (
                  <Link to={routeTo} className="hover:text-slate-200 transition-colors capitalize">
                    {title}
                  </Link>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Page Body Viewport */}
        <main className="flex-1 overflow-y-auto p-6 relative z-10">
          <Outlet />
        </main>
      </div>

      {/* Persistent Finny AI Assistant Widget */}
      <FinnyAssistant />
    </div>
  );
};
