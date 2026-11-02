import React from 'react';
import {
  LayoutDashboard,
  CloudSun,
  Wheat,
  AlertTriangle,
  Bell,
  BotMessageSquare,
  User as UserIcon,
  ArrowLeft,
} from 'lucide-react';
import type { NavigationTab } from '../../types';
import { useAuth } from '../../context/useAuth';

interface FarmerLayoutProps {
  currentTab: NavigationTab;
  onNavigate: (tab: NavigationTab) => void;
  children: React.ReactNode;
}

export const FarmerLayout: React.FC<FarmerLayoutProps> = ({
  currentTab,
  onNavigate,
  children,
}) => {
  const { user } = useAuth();

  const navItems = [
    { id: 'farmer-overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'farmer-weather', label: 'Weather Forecast', icon: CloudSun },
    { id: 'farmer-crops', label: 'Crops & Fields', icon: Wheat },
    { id: 'farmer-risks', label: 'Risks & Alerts', icon: AlertTriangle, badge: '2 Active' },
    { id: 'farmer-notifications', label: 'Notifications', icon: Bell, badge: '3' },
    { id: 'farmer-ai', label: 'AI Farm Advisor', icon: BotMessageSquare, badge: 'AI' },
    { id: 'farmer-profile', label: 'My Farm Profile', icon: UserIcon },
  ];

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col md:flex-row bg-slate-50">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-white border-r border-slate-200 shrink-0">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
              Farmer Workspace (Auth)
            </span>
            <h2 className="font-bold text-slate-900 text-sm mt-1">
              {user ? user.full_name : 'Green Valley Ranch'}
            </h2>
            <p className="text-xs text-slate-500 truncate max-w-[190px]">
              {user ? user.email : 'ID: FMR-8201 • 350 Acres'}
            </p>
          </div>
          <button
            onClick={() => onNavigate('landing')}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-md hover:bg-slate-100 md:hidden"
            title="Exit to home"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
        </div>

        <nav className="p-2 md:p-3 flex md:flex-col overflow-x-auto md:overflow-visible gap-1.5 md:gap-0 md:space-y-1 border-b md:border-b-0 border-slate-100 scrollbar-none">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id as NavigationTab)}
                className={`flex items-center justify-between px-3 py-2 md:py-2.5 rounded-lg text-xs md:text-sm font-medium shrink-0 md:shrink md:w-full transition-all ${
                  isActive
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 bg-slate-50/60 md:bg-transparent'
                }`}
              >
                <div className="flex items-center space-x-2 md:space-x-3">
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-600'}`} />
                  <span className="whitespace-nowrap">{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                      isActive
                        ? 'bg-emerald-800 text-emerald-100'
                        : item.badge === 'AI'
                        ? 'bg-purple-100 text-purple-700'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Auth Status callout in sidebar */}
        <div className="hidden md:block p-3 mx-3 my-4 bg-emerald-50/70 border border-emerald-100 rounded-xl text-xs text-emerald-900">
          <p className="font-semibold text-[11px] uppercase tracking-wide text-emerald-800">
            Authenticated Farmer Session
          </p>
          <p className="mt-1 text-[11px] text-emerald-700 leading-relaxed">
            Connected via signed bearer token. Live Open-Meteo telemetry & PostgreSQL risk engine active.
          </p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
        <div className="max-w-6xl mx-auto">{children}</div>
      </main>
    </div>
  );
};
