import React, { useState, useEffect } from 'react';
import { Shield, Lock, Mail, ArrowRight, Info, XCircle, CheckCircle, Loader2 } from 'lucide-react';
import type { NavigationTab } from '../../types';
import { useAuth } from '../../context/useAuth';

interface LoginPageProps {
  onNavigate: (tab: NavigationTab) => void;
  targetNotice?: string | null;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onNavigate, targetNotice }) => {
  const { login } = useAuth();
  const isDev = import.meta.env.DEV;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    try {
      const regNotice = sessionStorage.getItem('farmshield_reg_notice');
      const regEmail = sessionStorage.getItem('farmshield_reg_email');
      if (regNotice) {
        setSuccessMessage(regNotice);
        sessionStorage.removeItem('farmshield_reg_notice');
      }
      if (regEmail) {
        setEmail(regEmail);
        sessionStorage.removeItem('farmshield_reg_email');
      }
    } catch {
      // ignore storage access errors
    }
  }, []);

  const handlePresetSelect = (presetEmail: string, presetPass: string) => {
    setEmail(presetEmail);
    setPassword(presetPass);
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsLoading(true);

    try {
      const user = await login({ email, password });
      setSuccessMessage(`Login successful! Welcome back, ${user.full_name || 'Farmer'}. Redirecting to dashboard...`);
      // Role-based routing strictly determined by backend verification
      setTimeout(() => {
        if (user.role === 'admin') {
          onNavigate('admin-overview');
        } else {
          onNavigate('farmer-overview');
        }
      }, 700);
    } catch (err: any) {
      setErrorMessage(err.message || 'Invalid email or password.');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-4 py-12">
      <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200 shadow-xl p-6 sm:p-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-emerald-600 text-white shadow-md shadow-emerald-500/20">
            <Shield className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Sign in to FarmShield AI
          </h2>
          <p className="text-xs text-slate-600">
            Secure authentication verified with Argon2 & JWT
          </p>
        </div>

        {targetNotice && (
          <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center space-x-2">
            <Info className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{targetNotice}</span>
          </div>
        )}

        {successMessage && (
          <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs flex items-center space-x-2.5 shadow-xs animate-in fade-in">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-medium">{successMessage}</span>
          </div>
        )}

        {errorMessage && (
          <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2.5">
            <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Quick Helper Presets (Development Only - Hidden in Production) */}
        {isDev && (
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider block">
                Platform Administrator Login:
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Password: Password123!</span>
            </div>
            <button
              type="button"
              onClick={() => handlePresetSelect('admin@farmshield.ai', 'Password123!')}
              className="w-full py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 hover:border-purple-500 hover:text-purple-700 text-left font-medium text-[11px] flex items-center justify-between transition-colors"
            >
              <div className="flex items-center space-x-2">
                <Shield className="w-4 h-4 text-purple-600 shrink-0" />
                <div>
                  <span className="block font-semibold">Fill Admin Credentials</span>
                  <span className="text-[10px] text-slate-400 block font-mono">admin@farmshield.ai</span>
                </div>
              </div>
              <span className="text-[10px] bg-purple-50 text-purple-700 px-2 py-0.5 rounded font-bold">ADMIN CONSOLE</span>
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-slate-700 mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm text-slate-800"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="font-medium text-slate-700">Password</label>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm text-slate-800"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60 shadow-md shadow-emerald-600/20 transition-all flex items-center justify-center space-x-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Authenticating with Backend...</span>
              </>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="pt-2 border-t border-slate-100 text-center text-xs text-slate-600">
          <span>Need a new farm account? </span>
          <button
            type="button"
            onClick={() => onNavigate('register')}
            className="font-semibold text-emerald-600 hover:underline"
          >
            Register your farm here
          </button>
        </div>
      </div>
    </div>
  );
};
