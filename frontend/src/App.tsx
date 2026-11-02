import { useState, useEffect } from 'react';
import { ShieldAlert, ArrowLeft, Loader2 } from 'lucide-react';
import type { NavigationTab } from './types';
import { Navbar } from './components/common/Navbar';
import { FarmerLayout } from './components/layouts/FarmerLayout';
import { AdminLayout } from './components/layouts/AdminLayout';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/useAuth';

// Public Pages
import { LandingPage } from './pages/public/LandingPage';
import { LoginPage } from './pages/public/LoginPage';
import { RegisterPage } from './pages/public/RegisterPage';

// Farmer Dashboard Pages
import { FarmerOverview } from './pages/farmer/FarmerOverview';
import { WeatherPlaceholder } from './pages/farmer/WeatherPlaceholder';
import { CropFarmPlaceholder } from './pages/farmer/CropFarmPlaceholder';
import { RiskAlerts } from './pages/farmer/RiskAlerts';
import { FarmerNotifications } from './pages/farmer/FarmerNotifications';
import { AIAssistantChat } from './pages/farmer/AIAssistantChat';
import { FarmProfile } from './pages/farmer/FarmProfile';

// Admin Dashboard Pages
import { AdminOverview } from './pages/admin/AdminOverview';
import { FarmersManagement } from './pages/admin/FarmersManagement';
import { RiskMonitoring } from './pages/admin/RiskMonitoring';
import { AdminNotifications } from './pages/admin/AdminNotifications';
import { AgentActivity } from './pages/admin/AgentActivity';

const VALID_TABS: NavigationTab[] = [
  'landing',
  'login',
  'register',
  'farmer-overview',
  'farmer-weather',
  'farmer-crops',
  'farmer-risks',
  'farmer-notifications',
  'farmer-ai',
  'farmer-profile',
  'admin-overview',
  'admin-farmers',
  'admin-risks',
  'admin-notifications',
  'admin-agent',
];

function getInitialTab(): NavigationTab {
  const hash = window.location.hash.replace('#', '') as NavigationTab;
  if (VALID_TABS.includes(hash)) return hash;

  try {
    const saved = localStorage.getItem('farmshield_active_tab') as NavigationTab;
    if (VALID_TABS.includes(saved)) return saved;
  } catch {
    // ignore
  }

  return 'landing';
}

function MainApp() {
  const [currentTab, setCurrentTabState] = useState<NavigationTab>(getInitialTab);
  const { user, isLoading } = useAuth();

  const setCurrentTab = (tab: NavigationTab) => {
    setCurrentTabState(tab);
    try {
      localStorage.setItem('farmshield_active_tab', tab);
      window.location.hash = tab;
    } catch {
      // ignore
    }
  };

  // Sync hash changes (e.g. browser back/forward buttons)
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as NavigationTab;
      if (VALID_TABS.includes(hash) && hash !== currentTab) {
        setCurrentTabState(hash);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [currentTab]);

  // Strict role-based navigation guard on session restoration & tab switches
  useEffect(() => {
    if (isLoading || !user) return;

    if (user.role === 'admin') {
      // Admins attempting to visit farmer portal routes are auto-routed to Admin Console
      if (currentTab.startsWith('farmer-') || currentTab === 'login' || currentTab === 'register') {
        setCurrentTab('admin-overview');
      }
    } else if (user.role === 'farmer') {
      // Farmers attempting to visit admin console routes are auto-routed to Farmer Portal
      if (currentTab.startsWith('admin-') || currentTab === 'login' || currentTab === 'register') {
        setCurrentTab('farmer-overview');
      }
    }
  }, [user, isLoading, currentTab]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center space-y-3">
          <Loader2 className="w-8 h-8 text-emerald-600 animate-spin" />
          <p className="text-xs text-slate-600 font-medium">Validating security session...</p>
        </div>
      </div>
    );
  }

  // Protected route enforcement
  const isFarmerRoute = currentTab.startsWith('farmer-');
  const isAdminRoute = currentTab.startsWith('admin-');

  // Farmer route protection: require login and non-admin role
  if (isFarmerRoute) {
    if (!user) {
      return (
        <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
          <Navbar currentTab={currentTab} onNavigate={setCurrentTab} />
          <div className="flex-1">
            <LoginPage
              onNavigate={setCurrentTab}
              targetNotice="Authentication required: Please sign in to access the Farmer Portal."
            />
          </div>
        </div>
      );
    }

    if (user.role !== 'farmer') {
      return (
        <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
          <Navbar currentTab={currentTab} onNavigate={setCurrentTab} />
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="max-w-md w-full bg-white rounded-2xl border border-amber-200 p-6 text-center space-y-4 shadow-lg">
              <div className="w-12 h-12 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center mx-auto">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-slate-900">Administrator Role Active</h2>
              <p className="text-xs text-slate-600 leading-relaxed">
                You are signed in as an Administrator (<span className="font-mono text-slate-800">{user.email}</span>). The Farmer Portal is reserved for registered agricultural operators with farm plots.
              </p>
              <div className="pt-2">
                <button
                  onClick={() => setCurrentTab('admin-overview')}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors inline-flex items-center space-x-1.5"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Go to Admin Console</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }
  }

  // Admin route protection: require login and admin role
  if (isAdminRoute) {
    if (!user) {
      return (
        <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
          <Navbar currentTab={currentTab} onNavigate={setCurrentTab} />
          <div className="flex-1">
            <LoginPage
              onNavigate={setCurrentTab}
              targetNotice="Administrator authentication required: Please sign in to access the Admin Console."
            />
          </div>
        </div>
      );
    }

    if (user.role !== 'admin') {
      return (
        <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
          <Navbar currentTab={currentTab} onNavigate={setCurrentTab} />
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="max-w-md w-full bg-white rounded-2xl border border-rose-200 p-6 text-center space-y-4 shadow-lg">
              <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-slate-900">Administrator Access Required</h2>
              <p className="text-xs text-slate-600 leading-relaxed">
                Your account (<span className="font-mono text-slate-800">{user.email}</span>) has the <strong className="uppercase">{user.role}</strong> role. You do not have permissions to access the Admin Console.
              </p>
              <div className="pt-2">
                <button
                  onClick={() => setCurrentTab('farmer-overview')}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors inline-flex items-center space-x-1.5"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Return to Farmer Dashboard</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }
  }

  const renderContent = () => {
    switch (currentTab) {
      // Public Screens
      case 'landing':
        return <LandingPage onNavigate={setCurrentTab} />;
      case 'login':
        return <LoginPage onNavigate={setCurrentTab} />;
      case 'register':
        return <RegisterPage onNavigate={setCurrentTab} />;

      // Farmer Dashboard Screens
      case 'farmer-overview':
        return (
          <FarmerLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <FarmerOverview onNavigate={setCurrentTab} />
          </FarmerLayout>
        );
      case 'farmer-weather':
        return (
          <FarmerLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <WeatherPlaceholder />
          </FarmerLayout>
        );
      case 'farmer-crops':
        return (
          <FarmerLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <CropFarmPlaceholder />
          </FarmerLayout>
        );
      case 'farmer-risks':
        return (
          <FarmerLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <RiskAlerts />
          </FarmerLayout>
        );
      case 'farmer-notifications':
        return (
          <FarmerLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <FarmerNotifications />
          </FarmerLayout>
        );
      case 'farmer-ai':
        return (
          <FarmerLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <AIAssistantChat />
          </FarmerLayout>
        );
      case 'farmer-profile':
        return (
          <FarmerLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <FarmProfile />
          </FarmerLayout>
        );

      // Admin Dashboard Screens
      case 'admin-overview':
        return (
          <AdminLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <AdminOverview onNavigate={setCurrentTab} />
          </AdminLayout>
        );
      case 'admin-farmers':
        return (
          <AdminLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <FarmersManagement />
          </AdminLayout>
        );
      case 'admin-risks':
        return (
          <AdminLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <RiskMonitoring />
          </AdminLayout>
        );
      case 'admin-notifications':
        return (
          <AdminLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <AdminNotifications />
          </AdminLayout>
        );
      case 'admin-agent':
        return (
          <AdminLayout currentTab={currentTab} onNavigate={setCurrentTab}>
            <AgentActivity />
          </AdminLayout>
        );

      default:
        return <LandingPage onNavigate={setCurrentTab} />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      <Navbar currentTab={currentTab} onNavigate={setCurrentTab} />
      <div className="flex-1">{renderContent()}</div>

      {/* Global Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-slate-800">FarmShield AI</span>
            <span>•</span>
            <span>PostgreSQL & Open-Meteo Active</span>
            <span>•</span>
            <span className="font-mono text-[11px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
              Role: {user ? user.role.toUpperCase() : 'GUEST'}
            </span>
          </div>

          <div className="flex items-center space-x-4">
            <button
              onClick={() => setCurrentTab('landing')}
              className="hover:text-emerald-700 transition-colors"
            >
              Landing
            </button>
            {(!user || user.role === 'farmer') && (
              <button
                onClick={() => setCurrentTab('farmer-overview')}
                className="hover:text-emerald-700 transition-colors"
              >
                Farmer Portal
              </button>
            )}
            {(!user || user.role === 'admin') && (
              <button
                onClick={() => setCurrentTab('admin-overview')}
                className="hover:text-emerald-700 transition-colors"
              >
                Admin Console
              </button>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
