import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { HealthCheckResponse } from '../types/api';

export type TabType = 'dashboard' | 'cases' | 'case-view' | 'evaluation';

interface DashboardShellProps {
  currentTab: TabType;
  onTabChange: (tab: TabType) => void;
  selectedCaseId?: string | null;
  children: React.ReactNode;
}

export const DashboardShell: React.FC<DashboardShellProps> = ({
  currentTab,
  onTabChange,
  children,
}) => {
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [healthError, setHealthError] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const res = await api.getHealth();
        if (isMounted) {
          setHealth(res);
          setHealthError(false);
        }
      } catch {
        if (isMounted) {
          setHealth(null);
          setHealthError(true);
        }
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems: { id: TabType; label: string }[] = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'cases', label: 'Cases' },
    { id: 'evaluation', label: 'Evaluation' },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased flex flex-col selection:bg-slate-700 selection:text-white">
      {/* Top Header */}
      <header className="border-b border-slate-800/80 bg-slate-950 sticky top-0 z-30">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-14 items-center justify-between">
            {/* Logo / Product Name */}
            <div className="flex items-center gap-2.5">
              <div className="h-6 w-6 rounded bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-xs">
                R
              </div>
              <span className="text-sm font-semibold text-white tracking-tight">
                Revenue Recovery
              </span>
            </div>

            {/* Navigation */}
            <nav className="flex space-x-1">
              {navItems.map((item) => {
                const isActive =
                  currentTab === item.id || (item.id === 'cases' && currentTab === 'case-view');
                return (
                  <button
                    key={item.id}
                    onClick={() => onTabChange(item.id)}
                    className={`px-3 py-1.5 text-xs font-medium rounded transition-colors cursor-pointer ${
                      isActive
                        ? 'bg-slate-800 text-white font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                    }`}
                  >
                    {item.label}
                  </button>
                );
              })}
            </nav>

            {/* Right Side: Gateway & API status */}
            <div className="flex items-center gap-3 text-xs">
              <span className="px-2 py-0.5 rounded text-[11px] font-sans font-medium bg-slate-900 border border-slate-800 text-slate-400">
                Razorpay Test Mode
              </span>
              <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    healthError ? 'bg-rose-500' : 'bg-emerald-400'
                  }`}
                />
                <span>{healthError ? 'API Disconnected' : 'API Connected'}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content View */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-xs text-slate-500">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-2">
          <span>AI Revenue Recovery Orchestrator • Policy-Gated Revenue Recovery System</span>
          <span>Verified Gateway Settlement</span>
        </div>
      </footer>
    </div>
  );
};
