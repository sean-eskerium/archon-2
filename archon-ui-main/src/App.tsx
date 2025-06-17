import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { KnowledgeBasePage } from './pages/KnowledgeBasePage';
import { SettingsPage } from './pages/SettingsPage';
import { MCPPage } from './pages/MCPPage';
import { MainLayout } from './components/layouts/MainLayout';
import { ThemeProvider } from './contexts/ThemeContext';
import { ToastProvider } from './contexts/ToastContext';
import { SettingsProvider, useSettings } from './contexts/SettingsContext';
import { ProjectPage } from './pages/ProjectPage';
import { ScreensaverOverlay } from './components/ScreensaverOverlay';
import { serverHealthService } from './services/serverHealthService';

const AppRoutes = () => {
  const { projectsEnabled } = useSettings();
  
  return (
    <Routes>
      <Route path="/" element={<KnowledgeBasePage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/mcp" element={<MCPPage />} />
      {projectsEnabled ? (
        <Route path="/projects" element={<ProjectPage />} />
      ) : (
        <Route path="/projects" element={<Navigate to="/" replace />} />
      )}
    </Routes>
  );
};

const AppContent = () => {
  const [screensaverActive, setScreensaverActive] = useState(false);
  const [screensaverDismissed, setScreensaverDismissed] = useState(false);
  const [screensaverSettings, setScreensaverSettings] = useState({
    enabled: true,
    style: 'quantum-flux' as const,
    delay: 10000
  });

  useEffect(() => {
    // Load initial settings
    const settings = serverHealthService.getSettings();
    setScreensaverSettings(settings);

    // Start health monitoring
    serverHealthService.startMonitoring({
      onDisconnected: () => {
        console.log('Server disconnected - activating screensaver');
        if (!screensaverDismissed) {
          setScreensaverActive(true);
        }
      },
      onReconnected: () => {
        console.log('Server reconnected');
        setScreensaverActive(false);
        setScreensaverDismissed(false);
      }
    });

    return () => {
      serverHealthService.stopMonitoring();
    };
  }, [screensaverDismissed]);

  const handleDismissScreensaver = () => {
    setScreensaverActive(false);
    setScreensaverDismissed(true);
  };

  return (
    <>
      <Router>
        <MainLayout>
          <AppRoutes />
        </MainLayout>
      </Router>
      <ScreensaverOverlay
        isActive={screensaverActive && screensaverSettings.enabled}
        style={screensaverSettings.style}
        onDismiss={handleDismissScreensaver}
      />
    </>
  );
};

export function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <SettingsProvider>
          <AppContent />
        </SettingsProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}