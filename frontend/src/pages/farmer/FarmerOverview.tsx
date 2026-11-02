import React, { useEffect, useState, useCallback } from 'react';
import {
  Wheat,
  CloudSun,
  AlertTriangle,
  Bot,
  TrendingUp,
  ArrowRight,
  Droplet,
  Building,
  ShieldAlert,
} from 'lucide-react';
import type { NavigationTab, Farm, WeatherObservation, RiskSummary } from '../../types';
import { api } from '../../services/api';

interface FarmerOverviewProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const FarmerOverview: React.FC<FarmerOverviewProps> = ({ onNavigate }) => {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState<string | null>(null);
  const [weather, setWeather] = useState<WeatherObservation | null>(null);
  const [riskSummary, setRiskSummary] = useState<RiskSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const selectedFarm = farms.find((f) => f.id === selectedFarmId) || farms[0] || null;

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const farmsList = await api.farms.list();
      setFarms(farmsList);
      if (farmsList.length > 0) {
        const activeId = selectedFarmId || farmsList[0].id;
        setSelectedFarmId(activeId);
        const [w, r] = await Promise.allSettled([
          api.weather.getCurrent(activeId),
          api.risks.getLatest(activeId),
        ]);
        if (w.status === 'fulfilled') setWeather(w.value);
        if (r.status === 'fulfilled') setRiskSummary(r.value);
      }
    } catch {
      // Ignore or log error
    } finally {
      setIsLoading(false);
    }
  }, [selectedFarmId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleFarmChange = async (farmId: string) => {
    setSelectedFarmId(farmId);
    try {
      const [w, r] = await Promise.allSettled([
        api.weather.getCurrent(farmId),
        api.risks.getLatest(farmId),
      ]);
      if (w.status === 'fulfilled') setWeather(w.value);
      if (r.status === 'fulfilled') setRiskSummary(r.value);
    } catch {
      // Ignore error
    }
  };

  const getRiskBadgeColor = (level?: string) => {
    switch (level) {
      case 'CRITICAL':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'HIGH':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'MODERATE':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'LOW':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Farm Health Command Center
            </h1>
            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-full">
              LIVE METEOROLOGY & THREAT ENGINE
            </span>
          </div>
          {selectedFarm ? (
            <p className="text-xs text-slate-600 mt-1">
              Active Farm: <strong className="text-slate-800">{selectedFarm.farm_name}</strong> • {selectedFarm.village}, {selectedFarm.district} • ({selectedFarm.latitude.toFixed(2)}°, {selectedFarm.longitude.toFixed(2)}°)
            </p>
          ) : (
            <p className="text-xs text-slate-500 mt-1">No registered farms</p>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {farms.length > 0 && (
            <div className="flex items-center space-x-2 bg-white px-3 py-1.5 rounded-xl border border-slate-200 shadow-xs">
              <Building className="w-4 h-4 text-emerald-600 shrink-0" />
              <select
                aria-label="Active Farm Selection"
                value={selectedFarmId || ''}
                onChange={(e) => handleFarmChange(e.target.value)}
                className="text-xs font-semibold text-slate-800 bg-transparent focus:outline-hidden cursor-pointer"
              >
                {farms.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.farm_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => onNavigate('farmer-ai')}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-xs flex items-center space-x-1.5"
          >
            <Bot className="w-4 h-4" />
            <span>Consult AI Advisor</span>
          </button>
          <button
            onClick={() => onNavigate('farmer-risks')}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-amber-500/10 text-amber-800 border border-amber-300 hover:bg-amber-500/20 flex items-center space-x-1.5"
          >
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>
              {riskSummary
                ? `${riskSummary.assessments.filter((a) => a.risk_level === 'CRITICAL' || a.risk_level === 'HIGH').length} Elevated Risks`
                : 'View Risk Alerts'}
            </span>
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Acreage */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600">Total Farm Area</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Wheat className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {selectedFarm ? `${selectedFarm.total_area} ${selectedFarm.area_unit}` : '--'}
          </p>
          <div className="flex items-center text-[11px] text-emerald-600 font-medium mt-1">
            <span>
              {selectedFarm ? `${selectedFarm.crops_count} active crop plot(s)` : 'Register a farm to begin'}
            </span>
          </div>
        </div>

        {/* Enrolled Crop Plots (Real DB Data) */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600">Cultivated Crop Plots</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2 mt-2">
            <p className="text-2xl font-bold text-slate-900">
              {selectedFarm ? `${selectedFarm.crops_count} Plots` : '--'}
            </p>
          </div>
          <div className="flex items-center text-[11px] text-slate-500 mt-1">
            <span>Enrolled in farm crop store</span>
          </div>
        </div>

        {/* Active Threat Index (Real Deterministic Engine) */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600">Agro-Threat Level</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-center space-x-2 mt-2">
            <p className="text-2xl font-bold text-slate-900">
              {riskSummary ? riskSummary.overall_risk_level : 'Evaluating...'}
            </p>
            {riskSummary && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getRiskBadgeColor(riskSummary.overall_risk_level)}`}>
                Score: {riskSummary.highest_risk_score.toFixed(0)}
              </span>
            )}
          </div>
          <div className="flex items-center text-[11px] text-slate-600 mt-1">
            <span>Deterministic rule evaluation</span>
          </div>
        </div>

        {/* Micro-Climate Status (Real Open-Meteo) */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600">Weather Status</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <CloudSun className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {weather && weather.temperature !== null && weather.temperature !== undefined
              ? `${weather.temperature.toFixed(1)}°C`
              : '--'}
          </p>
          <div className="flex items-center text-[11px] text-slate-600 mt-1">
            <span>
              {weather?.weather_condition || 'Weather telemetry ready'} • Open-Meteo
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid: Active Alerts & Weather Forecast Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Threats Preview */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              <h2 className="font-bold text-slate-900 text-base">Prioritized Agro-Threats</h2>
            </div>
            <button
              onClick={() => onNavigate('farmer-risks')}
              className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 flex items-center space-x-1"
            >
              <span>View All 5 Categories</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3">
            {riskSummary && riskSummary.assessments.length > 0 ? (
              riskSummary.assessments
                .slice(0, 3)
                .map((a) => (
                  <div
                    key={a.id}
                    className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                      a.risk_level === 'CRITICAL'
                        ? 'border-rose-200 bg-rose-50/50'
                        : a.risk_level === 'HIGH'
                        ? 'border-amber-200 bg-amber-50/50'
                        : 'border-slate-200 bg-slate-50/60'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${getRiskBadgeColor(a.risk_level)}`}>
                          {a.risk_level} (Score {a.risk_score.toFixed(0)})
                        </span>
                        <span className="text-xs font-semibold text-slate-800">
                          {a.risk_category}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 leading-snug">
                        {a.explanation}
                      </p>
                    </div>
                    <button
                      onClick={() => onNavigate('farmer-risks')}
                      className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors"
                    >
                      Precaution
                    </button>
                  </div>
                ))
            ) : (
              <div className="p-6 bg-slate-50 rounded-xl text-center text-xs text-slate-500">
                {isLoading ? 'Loading threat evaluations...' : 'No active threats detected.'}
              </div>
            )}
          </div>
        </div>

        {/* Quick Weather Snapshot */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CloudSun className="w-5 h-5 text-emerald-600" />
              <h2 className="font-bold text-slate-900 text-base">Weather Feed</h2>
            </div>
            <button
              onClick={() => onNavigate('farmer-weather')}
              className="text-xs font-semibold text-emerald-700 hover:text-emerald-800"
            >
              7-Day Forecast
            </button>
          </div>

          {weather ? (
            <div className="p-4 bg-gradient-to-br from-emerald-600 to-green-800 text-white rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-emerald-100 font-medium">Open-Meteo Provider</p>
                  <p className="text-3xl font-extrabold mt-1">
                    {weather.temperature !== null && weather.temperature !== undefined ? `${weather.temperature.toFixed(1)}°C` : '--'}
                  </p>
                  <p className="text-xs text-emerald-100 mt-0.5">{weather.weather_condition}</p>
                </div>
                <CloudSun className="w-12 h-12 text-emerald-200" />
              </div>

              <div className="grid grid-cols-3 gap-2 pt-3 border-t border-emerald-400/30 text-center text-xs">
                <div>
                  <span className="text-emerald-200 text-[10px] block">Humidity</span>
                  <span className="font-bold">{weather.relative_humidity?.toFixed(0) ?? '--'}%</span>
                </div>
                <div>
                  <span className="text-emerald-200 text-[10px] block">Precipitation</span>
                  <span className="font-bold">{weather.precipitation?.toFixed(1) ?? '0'} mm</span>
                </div>
                <div>
                  <span className="text-emerald-200 text-[10px] block">Wind</span>
                  <span className="font-bold">{weather.wind_speed?.toFixed(1) ?? '--'} km/h</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 bg-slate-50 rounded-xl text-center text-xs text-slate-500">
              Weather telemetry unavailable. Connect to a registered farm.
            </div>
          )}

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <Droplet className="w-4 h-4 text-blue-500" />
              <span className="text-slate-700 font-medium">Spray Drift Condition:</span>
            </div>
            <span className="font-bold text-emerald-700">
              {weather && (weather.wind_speed ?? 0) <= 15 ? 'Safe Window' : 'Caution / High Drift'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
