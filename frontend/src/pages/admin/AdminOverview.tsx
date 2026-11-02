import React, { useEffect, useState, useCallback } from 'react';
import {
  Users,
  ShieldAlert,
  Bot,
  Activity,
  Radio,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import type { NavigationTab, AdminOverviewStats } from '../../types';
import { api } from '../../services/api';

interface AdminOverviewProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const AdminOverview: React.FC<AdminOverviewProps> = ({ onNavigate }) => {
  const [stats, setStats] = useState<AdminOverviewStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.admin.getOverviewStats();
      setStats(data);
    } catch (err: any) {
      console.error('Failed to load admin overview metrics:', err);
      setError(err?.message || 'Unable to retrieve administrative operational statistics.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Administrative Control Operations
            </h1>
            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-full">
              REAL DATABASE
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Live PostgreSQL Telemetry • Multi-Farm Deterministic Aggregates
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => loadStats()}
            className="p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
            title="Refresh database metrics"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => onNavigate('admin-notifications')}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-xs flex items-center space-x-1.5"
          >
            <Radio className="w-4 h-4" />
            <span>Broadcast Regional Alert</span>
          </button>
          <button
            onClick={() => onNavigate('admin-farmers')}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 flex items-center space-x-1.5"
          >
            <Users className="w-4 h-4 text-slate-500" />
            <span>Manage Farmers</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {stats && stats.total_farmers === 0 && (
        <div className="p-4 bg-emerald-50/60 border border-emerald-200 rounded-2xl text-xs text-emerald-900 flex items-center space-x-3">
          <Users className="w-5 h-5 text-emerald-600 shrink-0" />
          <div>
            <p className="font-bold">No farmers registered yet</p>
            <p className="text-[11px] text-emerald-700">
              When farmers register via the portal, live acreage, weather observations, and risk surveillance will appear here automatically.
            </p>
          </div>
        </div>
      )}

      {/* Real Cluster Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Farmers */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600">Total Enrolled Farmers</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {stats ? `${stats.total_farmers} Operators` : '--'}
          </p>
          <div className="flex items-center space-x-1.5 text-[11px] text-emerald-700 mt-1 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Verified in PostgreSQL Users</span>
          </div>
        </div>

        {/* Total Monitored Acreage */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600">Monitored Crop Acreage</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {stats ? `${stats.total_monitored_acres.toLocaleString()} Acres` : '--'}
          </p>
          <div className="flex items-center space-x-1.5 text-[11px] text-slate-600 mt-1 font-medium">
            <span>Across {stats ? stats.total_farms : '--'} registered farms</span>
          </div>
        </div>

        {/* Active Threats */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600">Active High/Critical Threats</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-rose-600 mt-2">
            {stats ? `${stats.active_threats_count} Alerts` : '--'}
          </p>
          <span className="text-[11px] text-rose-700 font-medium">Deterministic Agro-Climatic triggers</span>
        </div>

        {/* AI Agent Queries */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600">Agronomy Consultations</span>
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-purple-700 mt-2">
            {stats ? `${stats.total_ai_queries_count} Queries` : '--'}
          </p>
          <span className="text-[11px] text-purple-600 font-medium">Strands Bedrock Ingestion Logged</span>
        </div>
      </div>

      {/* Administrative Operations Modules */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div
          onClick={() => onNavigate('admin-farmers')}
          className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs hover:border-emerald-500 hover:shadow-md cursor-pointer transition-all space-y-3"
        >
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center">
            <Users className="w-5 h-5" />
          </div>
          <h2 className="text-base font-bold text-slate-900">Enrolled Farmers Directory</h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            Inspect verified agricultural operators, view parcel acreage, crop plot variety, and individual risk statuses.
          </p>
        </div>

        <div
          onClick={() => onNavigate('admin-risks')}
          className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs hover:border-emerald-500 hover:shadow-md cursor-pointer transition-all space-y-3"
        >
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <h2 className="text-base font-bold text-slate-900">Risk Surveillance Monitor</h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            Live surveillance feed of frost, heat stress, pest risk, drought, and excessive moisture across all parcels.
          </p>
        </div>

        <div
          onClick={() => onNavigate('admin-agent')}
          className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs hover:border-emerald-500 hover:shadow-md cursor-pointer transition-all space-y-3"
        >
          <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-700 flex items-center justify-center">
            <Bot className="w-5 h-5" />
          </div>
          <h2 className="text-base font-bold text-slate-900">Agent Reasoning Activity</h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            Audit live Strands AI advisory sessions, farmer prompts, weather tool invocations, and response timestamps.
          </p>
        </div>
      </div>
    </div>
  );
};
