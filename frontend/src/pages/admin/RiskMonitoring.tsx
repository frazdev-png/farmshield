import React, { useState, useEffect, useCallback } from 'react';
import { Radio, MapPin, RefreshCw, AlertTriangle, ShieldCheck } from 'lucide-react';
import { api } from '../../services/api';
import type { AdminRiskMonitoringItem } from '../../types';

export const RiskMonitoring: React.FC = () => {
  const [risks, setRisks] = useState<AdminRiskMonitoringItem[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRisks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.admin.listRisks({
        severity: severityFilter === 'all' ? undefined : severityFilter,
        limit: 50,
      });
      setRisks(data);
    } catch (err: any) {
      console.error('Failed to load risk surveillance:', err);
      setError(err?.message || 'Failed to retrieve risk evaluations from database.');
    } finally {
      setIsLoading(false);
    }
  }, [severityFilter]);

  useEffect(() => {
    loadRisks();
  }, [loadRisks]);

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

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Regional Risk & Anomaly Surveillance
            </h1>
            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-full">
              REAL_API & DATABASE
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Aggregated deterministic risk evaluations calculated from live Open-Meteo observations
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-xl text-xs bg-white text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500 font-medium"
          >
            <option value="all">All Risk Levels</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Only</option>
            <option value="MODERATE">Moderate Only</option>
            <option value="LOW">Low Only</option>
          </select>
          <button
            onClick={() => loadRisks()}
            className="p-2 text-slate-500 hover:text-emerald-700 hover:bg-slate-100 rounded-xl transition-colors border border-slate-200"
            title="Refresh risk surveillance"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Geospatial Threat Matrix */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <h2 className="font-bold text-slate-900 text-sm flex items-center space-x-2">
          <Radio className="w-4 h-4 text-emerald-600" />
          <span>Regional Agro-Climatic Threats by Parcel</span>
        </h2>

        {isLoading && risks.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs flex flex-col items-center justify-center space-y-2">
            <RefreshCw className="w-5 h-5 animate-spin text-emerald-600" />
            <span>Loading active threat matrix...</span>
          </div>
        ) : risks.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs space-y-2">
            <ShieldCheck className="w-8 h-8 text-emerald-500 mx-auto" />
            <p className="font-semibold text-slate-700">No active threats found</p>
            <p className="text-[11px] text-slate-500">
              {severityFilter !== 'all'
                ? `No current risks matching ${severityFilter} severity.`
                : 'All farm parcels are operating within safe meteorological bounds.'}
            </p>
          </div>
        ) : (
          <div className="grid gap-3">
            {risks.map((z, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 hover:bg-white transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-start space-x-3">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                      z.highest_risk_level === 'CRITICAL'
                        ? 'bg-rose-100 text-rose-600'
                        : z.highest_risk_level === 'HIGH'
                        ? 'bg-amber-100 text-amber-600'
                        : z.highest_risk_level === 'MODERATE'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-emerald-100 text-emerald-600'
                    }`}
                  >
                    <MapPin className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">{z.farm_name}</h3>
                    <p className="text-slate-600 mt-0.5">District: {z.district}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Evaluated Threat: <strong className="text-slate-700">{z.risk_category}</strong> (Score {z.risk_score.toFixed(1)}/100)
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-3 self-end md:self-center">
                  <span className="font-mono text-slate-500 text-[10px]">
                    Assessed: {formatTimestamp(z.assessed_at)}
                  </span>
                  <span
                    className={`font-bold px-2.5 py-1 rounded-full text-[10px] ${
                      z.highest_risk_level === 'CRITICAL'
                        ? 'bg-rose-600 text-white'
                        : z.highest_risk_level === 'HIGH'
                        ? 'bg-amber-600 text-white'
                        : z.highest_risk_level === 'MODERATE'
                        ? 'bg-yellow-500 text-white'
                        : 'bg-emerald-600 text-white'
                    }`}
                  >
                    {z.highest_risk_level}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
