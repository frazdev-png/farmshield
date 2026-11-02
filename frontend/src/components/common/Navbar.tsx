import React, { useState } from 'react';
import { Shield, Sprout, Menu, X, ShieldCheck, ChevronRight, LogOut, User as UserIcon } from 'lucide-react';
import type { NavigationTab } from '../../types';
import { useAuth } from '../../context/useAuth';

interface NavbarProps {
  currentTab: NavigationTab;
  onNavigate: (tab: NavigationTab) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, onNavigate }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();

  const isFarmerSection = currentTab.startsWith('farmer-');
  const isAdminSection = currentTab.startsWith('admin-');
  const isAuthPage = currentTab === 'login' || currentTab === 'register';

  const handleLogout = () => {
    logout();
    try {
      localStorage.removeItem('farmshield_active_tab');
      window.location.hash = 'landing';
    } catch {
      // ignore
    }
    onNavigate('landing');
  };

  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <button
            onClick={() => onNavigate('landing')}
            className="flex items-center space-x-2.5 group focus:outline-hidden text-left"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-green-700 flex items-center justify-center text-white shadow-md shadow-emerald-500/20 group-hover:scale-105 transition-transform">
              <Shield className="w-5 h-5 absolute" />
              <Sprout className="w-3.5 h-3.5 text-emerald-200 relative z-10 translate-y-0.5" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-extrabold text-lg tracking-tight text-slate-900 group-hover:text-emerald-700 transition-colors">
                  FarmShield
                </span>
                <span className="text-[11px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded">
                  AI
                </span>
              </div>
              <p className="text-[10px] text-slate-600 font-medium tracking-wide">
                Agritech Intelligence
              </p>
            </div>
          </button>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            <button
              onClick={() => onNavigate('landing')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                currentTab === 'landing'
                  ? 'bg-slate-100 text-emerald-700 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              Overview
            </button>

            {(!user || user.role === 'farmer') && (
              <button
                onClick={() => onNavigate('farmer-overview')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  isFarmerSection
                    ? 'bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200/50'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Sprout className="w-4 h-4 text-emerald-600" />
                <span>Farmer Portal</span>
                {user && user.role === 'farmer' && (
                  <span className="text-[10px] bg-emerald-200 text-emerald-900 font-bold px-1.5 py-0.2 rounded-full">
                    Active
                  </span>
                )}
              </button>
            )}

            {(!user || user.role === 'admin') && (
              <button
                onClick={() => onNavigate('admin-overview')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  isAdminSection
                    ? 'bg-purple-50 text-purple-700 font-semibold border border-purple-200/50'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <ShieldCheck className="w-4 h-4 text-purple-600" />
                <span>Admin Console</span>
                {user && user.role === 'admin' && (
                  <span className="text-[10px] bg-purple-200 text-purple-900 font-bold px-1.5 py-0.2 rounded-full">
                    Active
                  </span>
                )}
              </button>
            )}
          </nav>

          {/* Right Action Bar */}
          <div className="hidden md:flex items-center space-x-3">
            {user ? (
              <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
                <div className="text-right">
                  <div className="flex items-center space-x-1 text-xs font-bold text-slate-800">
                    <UserIcon className="w-3.5 h-3.5 text-slate-500" />
                    <span>{user.full_name}</span>
                  </div>
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.2 rounded ${
                      user.role === 'admin'
                        ? 'bg-purple-100 text-purple-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}
                  >
                    {user.role}
                  </span>
                </div>

                <button
                  onClick={handleLogout}
                  className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-slate-100 transition-colors"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : isAuthPage ? (
              <button
                onClick={() => onNavigate('landing')}
                className="text-xs font-medium text-slate-600 hover:text-emerald-700 px-3 py-1.5"
              >
                Back to Home
              </button>
            ) : (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => onNavigate('login')}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
                >
                  Log in
                </button>
                <button
                  onClick={() => onNavigate('register')}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm transition-colors flex items-center space-x-1"
                >
                  <span>Register Farm</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center space-x-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-600 hover:bg-slate-100"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-5 space-y-2">
          {user && (
            <div className="p-3 bg-slate-50 rounded-xl mb-2 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-slate-800">{user.full_name}</p>
                <p className="text-[11px] text-slate-500">{user.email}</p>
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">
                {user.role}
              </span>
            </div>
          )}

          <button
            onClick={() => {
              onNavigate('landing');
              setMobileMenuOpen(false);
            }}
            className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Overview
          </button>
          <button
            onClick={() => {
              onNavigate('farmer-overview');
              setMobileMenuOpen(false);
            }}
            className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium text-emerald-700 bg-emerald-50 flex items-center justify-between"
          >
            <span className="flex items-center space-x-2">
              <Sprout className="w-4 h-4 text-emerald-600" />
              <span>Farmer Dashboard</span>
            </span>
            {user?.role === 'farmer' && (
              <span className="text-[10px] bg-emerald-200 text-emerald-900 font-bold px-1.5 py-0.5 rounded">
                Active
              </span>
            )}
          </button>
          <button
            onClick={() => {
              onNavigate('admin-overview');
              setMobileMenuOpen(false);
            }}
            className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 flex items-center justify-between"
          >
            <span className="flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Admin Console</span>
            </span>
            {user?.role === 'admin' && (
              <span className="text-[10px] bg-purple-200 text-purple-900 font-bold px-1.5 py-0.5 rounded">
                Active
              </span>
            )}
          </button>

          <div className="pt-3 border-t border-slate-100 flex flex-col space-y-2">
            {user ? (
              <button
                onClick={() => {
                  handleLogout();
                  setMobileMenuOpen(false);
                }}
                className="w-full text-center py-2 text-sm font-medium text-rose-600 bg-rose-50 rounded-lg flex items-center justify-center space-x-2"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign Out</span>
              </button>
            ) : (
              <>
                <button
                  onClick={() => {
                    onNavigate('login');
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-center py-2 text-sm font-medium text-slate-700 border border-slate-200 rounded-lg"
                >
                  Log in
                </button>
                <button
                  onClick={() => {
                    onNavigate('register');
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-center py-2 text-sm font-semibold text-white bg-emerald-600 rounded-lg"
                >
                  Register Farm
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
