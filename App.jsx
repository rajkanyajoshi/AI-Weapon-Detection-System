import React, { useState } from 'react';
import { ThemeProvider } from './lib/ThemeContext';
import { WelcomePage } from './components/WelcomePage';
import { LoginPage } from './components/LoginPage';
import { Sidebar } from './components/Sidebar';
import { TopNavbar } from './components/TopNavbar';
import { HomePage } from './components/HomePage';
import { AlertsPage } from './components/AlertsPage';
import { AnalyticsPage } from './components/AnalyticsPage';
import { EmergencyServicesPage } from './components/EmergencyServicesPage';
import { SettingsPage } from './components/SettingsPage';
import { AlertDetailView } from './components/AlertDetailView';

function AppContent() {
  const [currentScreen, setCurrentScreen] = useState('welcome');
  const [activeTab, setActiveTab] = useState('home');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [alerts, setAlerts] = useState([
    {
      id: '1',
      weaponType: 'Handgun Detected',
      cameraId: 'CAM-001',
      location: 'Main Entrance',
      timestamp: '2 minutes ago',
      confidence: 96,
      status: 'new',
      severity: 'high',
    },
    {
      id: '2',
      weaponType: 'Knife Detected',
      cameraId: 'CAM-003',
      location: 'Parking Lot B',
      timestamp: '15 minutes ago',
      confidence: 87,
      status: 'acknowledged',
      severity: 'medium',
    },
    {
      id: '3',
      weaponType: 'Suspicious Object',
      cameraId: 'CAM-005',
      location: 'Loading Dock',
      timestamp: '1 hour ago',
      confidence: 72,
      status: 'new',
      severity: 'medium',
    },
  ]);

  const handleAlertClick = (alert) => {
    setSelectedAlert(alert);
  };

  const handleAcknowledge = (id) => {
    setAlerts(
      alerts.map((alert) =>
        alert.id === id ? { ...alert, status: 'acknowledged' } : alert
      )
    );
    if (selectedAlert?.id === id) {
      setSelectedAlert({ ...selectedAlert, status: 'acknowledged' });
    }
  };

  const handleDismiss = (id) => {
    setAlerts(
      alerts.map((alert) =>
        alert.id === id ? { ...alert, status: 'dismissed' } : alert
      )
    );
    if (selectedAlert?.id === id) {
      setSelectedAlert({ ...selectedAlert, status: 'dismissed' });
    }
  };

  const handleLogout = () => {
    setCurrentScreen('welcome');
    setActiveTab('home');
  };

  return (
    <>
      {currentScreen === 'welcome' && (
        <WelcomePage
          onGetStarted={() => setCurrentScreen('login')}
          onLearnMore={() => setCurrentScreen('login')}
        />
      )}

      {currentScreen === 'login' && (
        <LoginPage onLogin={() => setCurrentScreen('dashboard')} />
      )}

      {currentScreen === 'dashboard' && (
        <div className="flex h-screen overflow-hidden">
          <Sidebar
            isCollapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
            activeTab={activeTab}
            onTabChange={(tab) => setActiveTab(tab)}
          />

          <div className="flex-1 flex flex-col overflow-hidden">
            <TopNavbar onLogout={handleLogout} />

            <main className="flex-1 overflow-auto">
              {activeTab === 'home' && <HomePage />}
              {activeTab === 'alerts' && (
                <AlertsPage
                  alerts={alerts}
                  onAlertClick={handleAlertClick}
                  onAcknowledge={handleAcknowledge}
                  onDismiss={handleDismiss}
                />
              )}
              {activeTab === 'analytics' && <AnalyticsPage />}
              {activeTab === 'emergency' && <EmergencyServicesPage />}
              {activeTab === 'settings' && <SettingsPage />}
            </main>
          </div>
        </div>
      )}

      {selectedAlert && (
        <AlertDetailView
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onAcknowledge={handleAcknowledge}
          onDismiss={handleDismiss}
        />
      )}
    </>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}
