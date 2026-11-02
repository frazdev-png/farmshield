import React, { useEffect, useState } from 'react';
import { RefreshCw, XCircle, Database, Server } from 'lucide-react';
import { api, API_BASE_URL } from '../../services/api';
import type { BackendHealthState } from '../../types';

export const BackendStatusBadge: React.FC = () => {
  const [health, setHealth] = useState<BackendHealthState>({
    data: null,
    loading: true,
    error: null,
    lastChecked: null,
    latencyMs: null,
  });
  const [isOpen, setIsOpen] = useState(false);

  const checkStatus = async () => {
    try {
      const { data, latencyMs } = await api.checkHealth();
      setHealth({
        data,
        loading: false,
        error: null,
        lastChecked: new Date(),
        latencyMs,
      });
    } catch (err: unknown) {
      setHealth({
        data: null,
        loading: false,
        error: err instanceof Error ? err.message : 'Unknown connection error',
        lastChecked: new Date(),
        latencyMs: null,
      });
    }
  };

  useEffect(() => {
    let isMounted = true;

    const runHealthCheck = async () => {
      try {
        const { data, latencyMs } = await api.checkHealth();
        if (isMounted) {
          setHealth({
            data,
            loading: false,
            error: null,
            lastChecked: new Date(),
            latencyMs,
          });
        }
      } catch (err: unknown) {
        if (isMounted) {
          setHealth({
            data: null,
            loading: false,
            error: err instanceof Error ? err.message : 'Unknown connection error',
            lastChecked: new Date(),
            latencyMs: null,
          });
        }
      }
    };

    runHealthCheck();
    const interval = setInterval(runHealthCheck, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all border bg-white/90 hover:bg-white shadow-xs focus:outline-hidden"
        title="Click to view Backend Connection Details"
      >
        {health.loading && !health.data ? (
          <>
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-slate-600">Connecting...</span>
          </>
        ) : health.error ? (
          <>
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span className="text-rose-700 font-semibold">Backend Offline</span>
          </>
        ) : health.data?.status === 'healthy' ? (
          <>
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-emerald-700 font-semibold">FastAPI Connected</span>
            {health.latencyMs !== null && (
              <span className="text-slate-600 hidden sm:inline">({health.latencyMs}ms)</span>
            )}
          </>
        ) : (
          <>
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span className="text-amber-700 font-semibold">Degraded</span>
          </>
        )}
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-xl border border-slate-200 p-4 z-50 text-xs text-slate-700">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2 font-semibold text-slate-900">
                <Server className="w-4 h-4 text-emerald-600" />
                <span>Backend Health Monitor</span>
              </div>
              <button
                onClick={checkStatus}
                disabled={health.loading}
                className="p-1 text-slate-400 hover:text-emerald-600 rounded transition-colors"
                title="Refresh Health Check"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${health.loading ? 'animate-spin text-emerald-600' : ''}`} />
              </button>
            </div>

            <div className="mt-3 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">API Host:</span>
                <span className="font-mono text-[11px] text-slate-900 bg-slate-100 px-2 py-0.5 rounded">
                  {API_BASE_URL}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-600">Endpoint:</span>
                <span className="font-mono text-[11px] text-slate-700">/api/v1/health</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-600">Service:</span>
                <span className="font-medium text-slate-900">
                  {health.data?.service || 'FarmShield AI API'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-600">Version:</span>
                <span className="font-mono text-slate-900">{health.data?.version || '0.1.0'}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-600">Environment:</span>
                <span className="capitalize font-medium text-slate-900">
                  {health.data?.environment || 'development'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-600 flex items-center space-x-1">
                  <Database className="w-3.5 h-3.5 text-slate-400" />
                  <span>Database:</span>
                </span>
                <span
                  className={`font-medium ${
                    health.data?.database === 'operational'
                      ? 'text-emerald-600'
                      : 'text-amber-600'
                  }`}
                >
                  {health.data?.database || (health.error ? 'Unavailable' : 'Connecting')}
                </span>
              </div>

              {health.latencyMs !== null && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Roundtrip Latency:</span>
                  <span className="text-slate-900 font-mono">{health.latencyMs} ms</span>
                </div>
              )}

              {health.lastChecked && (
                <div className="flex items-center justify-between text-[11px] text-slate-600 pt-2 border-t border-slate-100">
                  <span>Last Checked:</span>
                  <span>{health.lastChecked.toLocaleTimeString()}</span>
                </div>
              )}

              {health.error && (
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-[11px] space-y-1 mt-2">
                  <div className="font-semibold flex items-center space-x-1">
                    <XCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                    <span>Connection Diagnostic</span>
                  </div>
                  <p>{health.error}</p>
                  <p className="text-slate-600 font-mono pt-1">
                    Run: <code className="bg-rose-100/60 px-1 py-0.5 rounded text-rose-900">uvicorn app.main:app --reload</code>
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
