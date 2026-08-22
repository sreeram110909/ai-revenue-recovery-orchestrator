import React, { useState } from 'react';
import { DashboardShell, TabType } from './components/DashboardShell';
import { Dashboard } from './pages/Dashboard';
import { Cases } from './pages/Cases';
import { CaseView } from './pages/CaseView';
import { Evaluation } from './pages/Evaluation';

export default function App() {
  const [currentTab, setCurrentTab] = useState<TabType>('dashboard');
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseId(caseId);
    setCurrentTab('case-view');
  };

  return (
    <DashboardShell
      currentTab={currentTab}
      onTabChange={setCurrentTab}
      selectedCaseId={selectedCaseId}
    >
      {currentTab === 'dashboard' && (
        <Dashboard
          onNavigateToCase={handleSelectCase}
          onNavigateToCases={() => setCurrentTab('cases')}
          onNavigateToEval={() => setCurrentTab('evaluation')}
        />
      )}

      {currentTab === 'cases' && (
        <Cases onSelectCase={handleSelectCase} />
      )}

      {currentTab === 'case-view' && (
        <CaseView
          caseId={selectedCaseId}
          onBackToCases={() => setCurrentTab('cases')}
          onSelectCase={setSelectedCaseId}
        />
      )}

      {currentTab === 'evaluation' && (
        <Evaluation />
      )}
    </DashboardShell>
  );
}
