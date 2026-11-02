import React, { useState, useEffect, useCallback } from 'react';
import { Search, RefreshCw, AlertTriangle, Users, Trash2, UserX, UserCheck, CheckCircle2, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import type { AdminFarmerItem } from '../../types';

export const FarmersManagement: React.FC = () => {
  const [farmers, setFarmers] = useState<AdminFarmerItem[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const loadFarmers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.admin.listFarmers();
      setFarmers(data);
    } catch (err: any) {
      console.error('Failed to load farmers list:', err);
      setError(err?.message || 'Failed to retrieve farmers from database.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFarmers();
  }, [loadFarmers]);

  const handleToggleStatus = async (farmer: AdminFarmerItem) => {
    const nextStatus = !farmer.is_active;
    const actionLabel = nextStatus ? 'activate' : 'suspend';
    if (!window.confirm(`Are you sure you want to ${actionLabel} farmer "${farmer.full_name}"?`)) {
      return;
    }

    setActionLoadingId(farmer.id);
    setError(null);
    setActionSuccess(null);
    try {
      const res = await api.admin.updateFarmerStatus(farmer.id, nextStatus);
      setFarmers((prev) =>
        prev.map((f) => (f.id === farmer.id ? { ...f, is_active: nextStatus } : f))
      );
      setActionSuccess(res.message);
    } catch (err: any) {
      setError(err?.message || `Failed to ${actionLabel} farmer.`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDeleteFarmer = async (farmer: AdminFarmerItem) => {
    if (
      !window.confirm(
        `Are you sure you want to permanently delete farmer "${farmer.full_name}"?\n\nThis will remove their account and all associated farms, crop plots, and risk records from the database.`
      )
    ) {
      return;
    }

    setActionLoadingId(farmer.id);
    setError(null);
    setActionSuccess(null);
    try {
      const res = await api.admin.deleteFarmer(farmer.id);
      setFarmers((prev) => prev.filter((f) => f.id !== farmer.id));
      setActionSuccess(res.message);
    } catch (err: any) {
      setError(err?.message || 'Failed to delete farmer.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const filtered = farmers.filter(
    (f) =>
      f.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.crops_summary.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatTimestamp = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
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
              Enrolled Farmers Directory
            </h1>
            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-full">
              REAL DATABASE
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Managing verified agricultural operators, statuses, and parcels registered in the system
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => loadFarmers()}
            className="p-2 text-slate-500 hover:text-emerald-700 hover:bg-slate-100 rounded-xl transition-colors border border-slate-200"
            title="Refresh farmers directory"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search farmer, email, or crop..."
              className="pl-9 pr-4 py-2 border border-slate-300 rounded-xl text-xs bg-white text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500 w-64"
            />
          </div>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs rounded-xl flex items-center justify-between shadow-xs">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            <span className="font-medium">{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-[11px] font-bold text-emerald-700 hover:text-emerald-900 ml-3"
          >
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Farmers Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {isLoading && farmers.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs flex flex-col items-center justify-center space-y-2">
            <RefreshCw className="w-5 h-5 animate-spin text-emerald-600" />
            <span>Loading enrolled farmers from database...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs space-y-2">
            <Users className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="font-semibold text-slate-700">No farmers found</p>
            <p className="text-[11px] text-slate-500">
              {searchTerm ? 'No registered operators matching search query.' : 'No farmers have registered yet.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 uppercase font-semibold text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4">Farmer / Operator</th>
                  <th className="py-3 px-4">Contact (Masked)</th>
                  <th className="py-3 px-4">Parcels</th>
                  <th className="py-3 px-4">Acreage</th>
                  <th className="py-3 px-4">Crops</th>
                  <th className="py-3 px-4">Highest Threat</th>
                  <th className="py-3 px-4">Enrolled Date</th>
                  <th className="py-3 px-4">Account Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((farmer) => {
                  const isOperating = actionLoadingId === farmer.id;
                  return (
                    <tr key={farmer.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4 font-semibold text-slate-900">
                        <div>{farmer.full_name}</div>
                        <span className="text-[10px] font-mono text-slate-500">{farmer.email}</span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-600">
                        {farmer.masked_phone}
                      </td>
                      <td className="py-3.5 px-4 font-medium text-slate-700">
                        {farmer.farms_count} Farm(s)
                      </td>
                      <td className="py-3.5 px-4 font-medium text-slate-900">
                        {farmer.total_acreage} ac
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 max-w-xs truncate">
                        {farmer.crops_summary}
                      </td>
                      <td className="py-3.5 px-4">
                        {farmer.highest_risk_level ? (
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              farmer.highest_risk_level === 'CRITICAL'
                                ? 'bg-rose-100 text-rose-700 border border-rose-300'
                                : farmer.highest_risk_level === 'HIGH'
                                ? 'bg-amber-100 text-amber-700 border border-amber-300'
                                : farmer.highest_risk_level === 'MODERATE'
                                ? 'bg-yellow-100 text-yellow-800 border border-yellow-300'
                                : 'bg-emerald-100 text-emerald-700 border border-emerald-300'
                            }`}
                          >
                            {farmer.highest_risk_level}
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-400">No Assessments</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-slate-500">
                        {formatTimestamp(farmer.created_at)}
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            farmer.is_active
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-rose-100 text-rose-700'
                          }`}
                        >
                          {farmer.is_active ? 'Active' : 'Suspended'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          {isOperating ? (
                            <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                          ) : (
                            <>
                              <button
                                onClick={() => handleToggleStatus(farmer)}
                                title={farmer.is_active ? 'Suspend farmer account' : 'Reactivate farmer account'}
                                className={`p-1.5 rounded-lg text-xs font-semibold transition-colors ${
                                  farmer.is_active
                                    ? 'text-amber-700 hover:bg-amber-50 hover:text-amber-800'
                                    : 'text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800'
                                }`}
                              >
                                {farmer.is_active ? (
                                  <UserX className="w-4 h-4" />
                                ) : (
                                  <UserCheck className="w-4 h-4" />
                                )}
                              </button>
                              <button
                                onClick={() => handleDeleteFarmer(farmer)}
                                title="Delete farmer and all associated data"
                                className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 hover:text-rose-800 transition-colors"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
