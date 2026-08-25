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
    <div className="min-h-screen bg-[#0B0D10] text-[#ECEFF3] font-sans antialiased flex flex-col selection:bg-[#262B33] selection:text-white">
      {/* Top Header */}
      <header className="border-b border-[#262B33] bg-[#0B0D10] sticky top-0 z-30">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-14 items-center justify-between">
            {/* Logo / Product Name */}
            <div className="flex items-center gap-2.5">
              <div className="h-6 w-6 rounded bg-[#2DBE8F]/20 border border-[#2DBE8F]/30 flex items-center justify-center text-[#2DBE8F] font-bold text-xs">
                R
              </div>
              <span className="text-sm font-semibold text-[#ECEFF3] tracking-tight font-heading">
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
                        ? 'bg-[#14171C] text-[#ECEFF3] font-semibold'
                        : 'text-[#8B93A1] hover:text-[#ECEFF3] hover:bg-[#14171C]/60'
                    }`}
                  >
                    {item.label}
                  </button>
                );
              })}
            </nav>

            {/* Right Side: Gateway & API status */}
            <div className="flex items-center gap-3 text-xs">
              <span
                className={`px-2 py-0.5 rounded text-[11px] font-sans font-medium border transition-colors ${
                  !health || healthError
                    ? 'bg-[#14171C]/60 border-[#262B33] text-[#8B93A1]'
                    : health.razorpay_configured
                    ? 'bg-[#14171C] border-[#262B33] text-[#ECEFF3]/80'
                    : 'bg-[#E8A33D]/10 border-[#E8A33D]/20 text-[#E8A33D]'
                }`}
              >
                {!health || healthError
                  ? 'Gateway: Checking...'
                  : health.razorpay_configured
                  ? 'Razorpay Test Mode'
                  : 'Mocked Gateway (No Keys)'}
              </span>
              <div className="flex items-center gap-1.5 text-[11px] text-[#8B93A1]">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    healthError
                      ? 'bg-[#C24C4C]'
                      : !health
                      ? 'bg-[#8B93A1] animate-pulse'
                      : 'bg-[#2DBE8F]'
                  }`}
                />
                <span>
                  {healthError
                    ? 'API Disconnected'
                    : !health
                    ? 'Connecting...'
                    : 'API Connected'}
                </span>
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
      <footer className="border-t border-[#262B33]/60 bg-[#0B0D10] py-4 text-xs text-[#8B93A1]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-2">
          <span>AI Revenue Recovery Orchestrator • Policy-Gated Revenue Recovery System</span>
          <span>Verified Gateway Settlement</span>
        </div>
      </footer>
    </div>
  );
};
