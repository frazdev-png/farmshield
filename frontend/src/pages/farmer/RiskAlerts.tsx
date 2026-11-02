import React, { useEffect, useState, useCallback } from 'react';
import {
  ShieldAlert,
  CheckCircle,
  AlertCircle,
  Building,
  RefreshCw,
  Activity,
  Droplets,
  Wind,
  Thermometer,
  CloudRain,
  HelpCircle,
} from 'lucide-react';
import type { Farm, RiskSummary, RiskLevel } from '../../types';
import { api } from '../../services/api';

export const RiskAlerts: React.FC = () => {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState<string | null>(null);
  const [summary, setSummary] = useState<RiskSummary | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>('All');
  const [isLoadingFarms, setIsLoadingFarms] = useState(true);
  const [isLoadingRisks, setIsLoadingRisks] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const selectedFarm = farms.find((f) => f.id === selectedFarmId) || farms[0] || null;

  // 1. Load farms
  const loadFarms = useCallback(async () => {
    setIsLoadingFarms(true);
    try {
      const data = await api.farms.list();
      setFarms(data);
      if (data.length > 0) {
        const farmExists = data.some((f) => f.id === selectedFarmId);
        if (!selectedFarmId || !farmExists) {
          setSelectedFarmId(data[0].id);
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load farms.');
    } finally {
      setIsLoadingFarms(false);
    }
  }, [selectedFarmId]);

  // 2. Load latest risks for farm
  const loadRisks = useCallback(async (farmId: string, evaluate = false) => {
    if (evaluate) {
      setIsEvaluating(true);
    } else {
      setIsLoadingRisks(true);
    }
    setErrorMessage(null);
    try {
      const data = evaluate
        ? await api.risks.evaluate(farmId)
        : await api.risks.getLatest(farmId);
      setSummary(data);
      if (evaluate) {
        setSuccessMessage('Deterministic risk rules evaluated successfully!');
        setTimeout(() => setSuccessMessage(null), 3500);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to retrieve agro-climatic risk assessments.');
    } finally {
      setIsLoadingRisks(false);
      setIsEvaluating(false);
    }
  }, []);

  useEffect(() => {
    loadFarms();
  }, [loadFarms]);

  useEffect(() => {
    if (selectedFarmId) {
      loadRisks(selectedFarmId);
    }
  }, [selectedFarmId, loadRisks]);

  const handleEvaluate = () => {
    if (selectedFarmId) {
      loadRisks(selectedFarmId, true);
    }
  };

  const assessments = summary?.assessments || [];
  const filteredAssessments =
    filterSeverity === 'All'
      ? assessments
      : assessments.filter((a) => a.risk_level === filterSeverity);

  const getLevelBadge = (level: RiskLevel) => {
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
        return 'bg-slate-100 text-slate-800 border-slate-300';
    }
  };

  const getScoreBarColor = (score: number) => {
    if (score >= 85) return 'bg-rose-600';
    if (score >= 65) return 'bg-amber-500';
    if (score >= 35) return 'bg-yellow-500';
    return 'bg-emerald-500';
  };

  const getCategoryIcon = (cat: string) => {
    if (cat.includes('Rain')) return <CloudRain className="w-4 h-4 text-blue-500 shrink-0" />;
    if (cat.includes('Wind')) return <Wind className="w-4 h-4 text-amber-500 shrink-0" />;
    if (cat.includes('Heat')) return <Thermometer className="w-4 h-4 text-rose-500 shrink-0" />;
    if (cat.includes('Low Temperature')) return <Thermometer className="w-4 h-4 text-indigo-500 shrink-0" />;
    return <Droplets className="w-4 h-4 text-purple-500 shrink-0" />;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Agro-Threats & Deterministic Risk Engine
            </h1>
            <span className="text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-300 px-2 py-0.5 rounded-full flex items-center space-x-1">
              <Activity className="w-3 h-3 text-blue-600" />
              <span>DETERMINISTIC PYTHON RULES (NO LLM)</span>
            </span>
          </div>
          {selectedFarm ? (
            <p className="text-xs text-slate-600 mt-1">
              Target Farm: <strong className="text-slate-800">{selectedFarm.farm_name}</strong> • {selectedFarm.village}, {selectedFarm.district} • Area: {selectedFarm.total_area} {selectedFarm.area_unit}
            </p>
          ) : (
            <p className="text-xs text-slate-500 mt-1">No farm selected</p>
          )}
        </div>

        {/* Farm Switcher & Evaluate Action */}
        <div className="flex items-center space-x-3">
          {farms.length > 0 && (
            <div className="flex items-center space-x-2 bg-white px-3 py-1.5 rounded-xl border border-slate-200 shadow-xs">
              <Building className="w-4 h-4 text-emerald-600 shrink-0" />
              <select
                aria-label="Active Farm Selection"
                value={selectedFarmId || ''}
                onChange={(e) => setSelectedFarmId(e.target.value)}
                className="text-xs font-semibold text-slate-800 bg-transparent focus:outline-hidden cursor-pointer"
              >
                {farms.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.farm_name} ({f.district})
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={handleEvaluate}
            disabled={isEvaluating || !selectedFarmId}
            className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 shadow-xs flex items-center space-x-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isEvaluating ? 'animate-spin' : ''}`} />
            <span>{isEvaluating ? 'Evaluating...' : 'Evaluate Current Risks'}</span>
          </button>
        </div>
      </div>

      {/* Messages */}
      {errorMessage && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs text-rose-800 flex items-center space-x-2.5">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {successMessage && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-xs text-emerald-800 flex items-center space-x-2.5">
          <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Disclaimer Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-xs text-blue-900 flex items-start space-x-2.5">
        <HelpCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <p className="font-semibold">Deterministic Agronomic Rules Engine</p>
          <p className="text-[11px] text-blue-800">
            Risk scores and alert levels are generated strictly from measurable weather station observations and registered crop metadata. Generic thresholds are preliminary rules requiring local agronomic validation. Does not provide chemical/pesticide recommendations.
          </p>
        </div>
      </div>

      {/* No Farm Warning */}
      {!isLoadingFarms && farms.length === 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-center space-y-2">
          <Building className="w-10 h-10 text-amber-600 mx-auto" />
          <h3 className="font-bold text-slate-800 text-sm">No Registered Farms Found</h3>
          <p className="text-xs text-slate-600 max-w-md mx-auto">
            Please register your farm in Farm Profile to enable risk evaluation against real meteorological station feeds.
          </p>
        </div>
      )}

      {/* Overall Risk Summary Banner */}
      {selectedFarm && summary && (
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              summary.overall_risk_level === 'CRITICAL'
                ? 'bg-rose-100 text-rose-700'
                : summary.overall_risk_level === 'HIGH'
                ? 'bg-amber-100 text-amber-700'
                : summary.overall_risk_level === 'MODERATE'
                ? 'bg-yellow-100 text-yellow-700'
                : 'bg-emerald-100 text-emerald-700'
            }`}>
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-500 font-medium">Aggregate Farm Risk:</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${getLevelBadge(summary.overall_risk_level)}`}>
                  {summary.overall_risk_level}
                </span>
              </div>
              <p className="text-lg font-bold text-slate-900 mt-0.5">
                Highest Risk Severity Score: {summary.highest_risk_score.toFixed(1)} / 100
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 text-xs">
            <span className="text-slate-500 font-medium">Filter Severity:</span>
            {['All', 'CRITICAL', 'HIGH', 'MODERATE', 'LOW'].map((lvl) => (
              <button
                key={lvl}
                onClick={() => setFilterSeverity(lvl)}
                className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                  filterSeverity === lvl
                    ? 'bg-slate-900 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Risk Assessments Grid */}
      {selectedFarm && (
        <div className="space-y-4">
          {isLoadingRisks ? (
            <div className="p-8 bg-white rounded-2xl border border-slate-200 text-center flex flex-col items-center justify-center space-y-2">
              <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin" />
              <p className="text-xs text-slate-500">Evaluating deterministic agro-threat algorithms...</p>
            </div>
          ) : filteredAssessments.length === 0 ? (
            <div className="p-8 bg-white rounded-2xl border border-slate-200 text-center space-y-2">
              <CheckCircle className="w-8 h-8 text-emerald-600 mx-auto" />
              <p className="text-xs font-bold text-slate-700">No risk alerts in this severity category.</p>
              <p className="text-[11px] text-slate-500">Conditions are either within safe baseline bounds or evidence has been filtered.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredAssessments.map((a) => (
                <div
                  key={a.id}
                  className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3 flex flex-col justify-between"
                >
                  <div className="space-y-2.5">
                    {/* Title & Level Badge */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center space-x-2">
                        {getCategoryIcon(a.risk_category)}
                        <h3 className="font-bold text-slate-900 text-sm">{a.risk_category}</h3>
                      </div>
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${getLevelBadge(a.risk_level)}`}>
                        {a.risk_level}
                      </span>
                    </div>

                    {/* Score Bar */}
                    <div>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-slate-500 font-medium">Risk Intensity Score:</span>
                        <strong className="text-slate-800">{a.risk_score.toFixed(1)} / 100</strong>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-2 rounded-full transition-all duration-300 ${getScoreBarColor(a.risk_score)}`}
                          style={{ width: `${Math.min(100, Math.max(5, a.risk_score))}%` }}
                        />
                      </div>
                    </div>

                    {/* Explanation */}
                    <div className="bg-slate-50 rounded-xl p-3 border border-slate-100 text-xs text-slate-700">
                      <p className="font-semibold text-slate-800 text-[11px] mb-1">Observed Diagnostics:</p>
                      <p className="leading-relaxed">{a.explanation}</p>
                    </div>

                    {/* Recommended Precaution */}
                    <div className="bg-emerald-50/60 rounded-xl p-3 border border-emerald-100 text-xs text-emerald-900">
                      <p className="font-semibold text-emerald-800 text-[11px] mb-1 flex items-center space-x-1">
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Recommended Agronomic Precaution:</span>
                      </p>
                      <p className="leading-relaxed text-[11px]">{a.recommended_precaution}</p>
                    </div>
                  </div>

                  {/* Evidence Metrics Footer */}
                  <div className="pt-2 border-t border-slate-100 text-[10px] text-slate-500 flex items-center justify-between">
                    <span>Assessed: {new Date(a.assessed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} UTC</span>
                    <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                      Verified Rule
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
