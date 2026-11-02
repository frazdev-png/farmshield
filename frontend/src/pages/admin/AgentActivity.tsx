import React, { useState, useEffect, useCallback } from 'react';
import { Cpu, Bot, Zap, RefreshCw, AlertTriangle, MessageSquare } from 'lucide-react';
import { api } from '../../services/api';
import type { AdminAgentActivityItem } from '../../types';

export const AgentActivity: React.FC = () => {
  const [activities, setActivities] = useState<AdminAgentActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadActivity = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.admin.listAgentActivity();
      setActivities(data);
    } catch (err: any) {
      console.error('Failed to load agent activity:', err);
      setError(err?.message || 'Failed to retrieve agent reasoning activity from database.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadActivity();
  }, [loadActivity]);

  const formatTimestamp = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const totalQueries = activities.reduce((acc, curr) => acc + curr.messages_count, 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              AI Agent Telemetry & Reasoning Hub
            </h1>
            <span className="text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-300 px-2 py-0.5 rounded-full">
              REAL DATABASE
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Strands AI Agronomy runtime monitor • Bedrock multi-turn conversation logs
          </p>
        </div>

        <button
          onClick={() => loadActivity()}
          className="p-2 text-slate-500 hover:text-purple-700 hover:bg-slate-100 rounded-xl transition-colors border border-slate-200 self-start sm:self-auto"
          title="Refresh agent sessions"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center space-x-2 text-slate-600 text-xs font-medium">
            <Bot className="w-4 h-4 text-purple-600" />
            <span>Active Conversations</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-1.5">{activities.length}</p>
          <p className="text-[11px] text-purple-600 font-medium">Recorded in DB</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center space-x-2 text-slate-600 text-xs font-medium">
            <MessageSquare className="w-4 h-4 text-blue-500" />
            <span>Total Messages Exchanged</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-1.5">{totalQueries}</p>
          <p className="text-[11px] text-blue-600 font-medium">Multi-turn history</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center space-x-2 text-slate-600 text-xs font-medium">
            <Zap className="w-4 h-4 text-amber-500" />
            <span>Agronomic Model</span>
          </div>
          <p className="text-sm font-bold text-slate-900 mt-2 font-mono truncate">Claude 3 Haiku</p>
          <p className="text-[11px] text-slate-500 font-medium">Amazon Bedrock</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center space-x-2 text-slate-600 text-xs font-medium">
            <Cpu className="w-4 h-4 text-emerald-600" />
            <span>Farmers Consulted</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-1.5">
            {new Set(activities.map((a) => a.farmer_name)).size}
          </p>
          <p className="text-[11px] text-emerald-700 font-medium">Distinct operators served</p>
        </div>
      </div>

      {/* Query Activity Feed */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider">
            Recent Inbound Agronomy Reasoning Sessions
          </h3>
          <span className="text-[11px] text-slate-500">Live conversation store</span>
        </div>

        {isLoading && activities.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs flex flex-col items-center justify-center space-y-2">
            <RefreshCw className="w-5 h-5 animate-spin text-purple-600" />
            <span>Loading reasoning activity logs...</span>
          </div>
        ) : activities.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs space-y-2">
            <Bot className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="font-semibold text-slate-700">No agent sessions recorded yet</p>
            <p className="text-[11px] text-slate-500">
              When farmers chat with the Strands AI advisor, their agronomy sessions will be logged here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 text-[10px] uppercase font-semibold">
                <tr>
                  <th className="py-2.5 px-4">Session Title</th>
                  <th className="py-2.5 px-4">Farmer Operator</th>
                  <th className="py-2.5 px-4">Farm Plot</th>
                  <th className="py-2.5 px-4">Latest Inbound Query</th>
                  <th className="py-2.5 px-4">Messages</th>
                  <th className="py-2.5 px-4 text-right">Last Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {activities.map((q) => (
                  <tr key={q.session_id} className="hover:bg-slate-50/60">
                    <td className="py-3 px-4 font-semibold text-slate-900 max-w-xs truncate">
                      {q.title}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800">{q.farmer_name}</td>
                    <td className="py-3 px-4 text-slate-600">{q.farm_name}</td>
                    <td className="py-3 px-4 text-slate-600 max-w-sm truncate font-mono text-[11px]">
                      {q.last_query_snippet || 'No query text'}
                    </td>
                    <td className="py-3 px-4 font-semibold text-purple-700">
                      {q.messages_count} msgs
                    </td>
                    <td className="py-3 px-4 text-right text-slate-500">
                      {formatTimestamp(q.last_activity_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
