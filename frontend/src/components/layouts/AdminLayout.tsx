import React from 'react';
import {
  ShieldAlert,
  Users,
  Radio,
  Send,
  Cpu,
  ArrowLeft,
  Building2,
} from 'lucide-react';
import type { NavigationTab } from '../../types';
import { useAuth } from '../../context/useAuth';

interface AdminLayoutProps {
  currentTab: NavigationTab;
  onNavigate: (tab: NavigationTab) => void;
  children: React.ReactNode;
}

export const AdminLayout: React.FC<AdminLayoutProps> = ({
  currentTab,
  onNavigate,
  children,
}) => {
  const { user } = useAuth();

  const navItems = [
    { id: 'admin-overview', label: 'Admin Overview', icon: ShieldAlert },
    { id: 'admin-farmers', label: 'Farmers Management', icon: Users, badge: '1,240' },
    { id: 'admin-risks', label: 'Risk Monitoring', icon: Radio, badge: 'Live' },
    { id: 'admin-notifications', label: 'Broadcast Console', icon: Send },
    { id: 'admin-agent', label: 'Agent Activity', icon: Cpu, badge: '99.4%' },
  ];

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col md:flex-row bg-slate-50">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-slate-900 text-slate-200 border-r border-slate-800 shrink-0">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-950/80 border border-emerald-800/40 px-2 py-0.5 rounded">
              Verified Administrator
            </span>
            <div className="flex items-center space-x-2 mt-1.5">
              <Building2 className="w-4 h-4 text-emerald-400" />
              <h2 className="font-bold text-white text-sm">
                {user ? user.full_name : 'FarmShield Operations'}
              </h2>
            </div>
            <p className="text-xs text-slate-400 truncate max-w-[190px]">
              {user ? user.email : 'Regional Cluster: North-East'}
            </p>
          </div>
          <button
            onClick={() => onNavigate('landing')}
            className="p-1.5 text-slate-400 hover:text-white rounded-md hover:bg-slate-800 md:hidden"
            title="Exit to home"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
        </div>

        <nav className="p-2 md:p-3 flex md:flex-col overflow-x-auto md:overflow-visible gap-1.5 md:gap-0 md:space-y-1 border-b md:border-b-0 border-slate-800 scrollbar-none">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id as NavigationTab)}
                className={`flex items-center justify-between px-3 py-2 md:py-2.5 rounded-lg text-xs md:text-sm font-medium shrink-0 md:shrink md:w-full transition-all ${
                  isActive
                    ? 'bg-emerald-600 text-white font-semibold shadow-xs'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800 bg-slate-800/60 md:bg-transparent'
                }`}
              >
                <div className="flex items-center space-x-2 md:space-x-3">
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span className="whitespace-nowrap">{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                      isActive
                        ? 'bg-emerald-800 text-emerald-100'
                        : item.badge === 'Live'
                        ? 'bg-rose-950 text-rose-300 border border-rose-800'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="hidden md:block p-3 mx-3 my-4 bg-slate-800/80 border border-slate-700 rounded-xl text-xs text-slate-300">
          <p className="font-semibold text-[11px] uppercase tracking-wide text-slate-200">
            Control Authority Active
          </p>
          <p className="mt-1 text-[11px] text-slate-400 leading-relaxed">
            Authenticated via backend JWT. Administrative policy permissions granted for regional management.
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
