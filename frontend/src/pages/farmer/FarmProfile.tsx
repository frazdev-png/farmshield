import React, { useEffect, useState } from 'react';
import {
  User as UserIcon,
  Building,
  Phone,
  Mail,
  Save,
  CheckCircle,
  Plus,
  Trash2,
  Loader2,
  XCircle,
} from 'lucide-react';
import type { Farm, FarmCreatePayload, FarmUpdatePayload } from '../../types';
import { api } from '../../services/api';
import { useAuth } from '../../context/useAuth';

export const FarmProfile: React.FC = () => {
  const { user } = useAuth();

  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // New Farm Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newFarm, setNewFarm] = useState<FarmCreatePayload>({
    farm_name: '',
    district: 'Lahore',
    village: '',
    address: '',
    latitude: 31.5204,
    longitude: 74.3587,
    total_area: 25.0,
    area_unit: 'acres',
    soil_type: 'Loam',
  });

  // Edit Farm Form State
  const [editForm, setEditForm] = useState<FarmUpdatePayload>({});

  const selectedFarm = farms.find((f) => f.id === selectedFarmId) || farms[0] || null;

  const loadFarms = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await api.farms.list();
      setFarms(data);
      if (data.length > 0 && !selectedFarmId) {
        setSelectedFarmId(data[0].id);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load farms.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadFarms();
  }, []);

  useEffect(() => {
    if (selectedFarm) {
      setEditForm({
        farm_name: selectedFarm.farm_name,
        district: selectedFarm.district,
        village: selectedFarm.village,
        address: selectedFarm.address || '',
        latitude: selectedFarm.latitude,
        longitude: selectedFarm.longitude,
        total_area: selectedFarm.total_area,
        area_unit: selectedFarm.area_unit,
        soil_type: selectedFarm.soil_type || '',
      });
    }
  }, [selectedFarmId, farms]);

  const handleCreateFarm = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setErrorMessage(null);
    try {
      const created = await api.farms.create(newFarm);
      setShowCreateModal(false);
      setSuccessMessage(`Farm "${created.farm_name}" created successfully!`);
      await loadFarms();
      setSelectedFarmId(created.id);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to create farm.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateFarm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFarm) return;
    setIsSaving(true);
    setErrorMessage(null);
    try {
      const updated = await api.farms.update(selectedFarm.id, editForm);
      setSuccessMessage(`Farm "${updated.farm_name}" updated successfully!`);
      await loadFarms();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update farm.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteFarm = async (farmId: string, farmName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${farmName}" and all associated crops?`)) {
      return;
    }
    setIsSaving(true);
    setErrorMessage(null);
    try {
      await api.farms.delete(farmId);
      setSuccessMessage(`Farm "${farmName}" was deleted.`);
      setSelectedFarmId(null);
      await loadFarms();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to delete farm.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              My Farm & Operator Profile
            </h1>
            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-full">
              LIVE POSTGRESQL APIS
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Manage your agricultural properties, spatial coordinates, and operator contact credentials
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm transition-colors flex items-center space-x-1.5 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Add New Farm</span>
        </button>
      </div>

      {/* Notifications / Alerts */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2.5">
          <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center space-x-2.5">
          <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Operator Contact Details (Auth User) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <h2 className="font-bold text-slate-900 text-sm flex items-center space-x-2">
          <UserIcon className="w-4 h-4 text-emerald-600" />
          <span>Authenticated Operator Information</span>
        </h2>

        <div className="grid sm:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="block text-slate-500 font-medium mb-1">Full Name</label>
            <p className="font-semibold text-slate-900 text-sm">{user?.full_name || 'Loading...'}</p>
          </div>
          <div>
            <label className="block text-slate-500 font-medium mb-1">Email Address</label>
            <div className="flex items-center space-x-1.5 text-slate-800 font-mono">
              <Mail className="w-3.5 h-3.5 text-slate-400" />
              <span>{user?.email || 'Loading...'}</span>
            </div>
          </div>
          <div>
            <label className="block text-slate-500 font-medium mb-1">Phone Number</label>
            <div className="flex items-center space-x-1.5 text-slate-800 font-mono">
              <Phone className="w-3.5 h-3.5 text-slate-400" />
              <span>{user?.phone_number || 'Loading...'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Farms List / Selector */}
      {isLoading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
          <Loader2 className="w-6 h-6 text-emerald-600 animate-spin mx-auto mb-2" />
          <p className="text-xs text-slate-600 font-medium">Loading your registered farms...</p>
        </div>
      ) : farms.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-10 text-center space-y-3">
          <Building className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="font-bold text-slate-800 text-base">No Registered Farms Found</h3>
          <p className="text-xs text-slate-600 max-w-sm mx-auto">
            You haven't registered any farm holdings yet. Click below to add your first property.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm transition-colors inline-flex items-center space-x-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Register Your First Farm</span>
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Farm Switcher Tabs */}
          <div className="flex items-center space-x-2 overflow-x-auto pb-1">
            {farms.map((farm) => {
              const isSelected = selectedFarm?.id === farm.id;
              return (
                <button
                  key={farm.id}
                  onClick={() => setSelectedFarmId(farm.id)}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all shrink-0 flex items-center space-x-2 border ${
                    isSelected
                      ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <Building className="w-3.5 h-3.5" />
                  <span>{farm.farm_name}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                      isSelected ? 'bg-emerald-800 text-white' : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {farm.total_area} {farm.area_unit}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Edit Selected Farm Form */}
          {selectedFarm && (
            <form onSubmit={handleUpdateFarm} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">
                    Farm Property Specifications: {selectedFarm.farm_name}
                  </h3>
                  <p className="text-[11px] text-slate-500 font-mono">
                    ID: {selectedFarm.id} • Registered {new Date(selectedFarm.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteFarm(selectedFarm.id, selectedFarm.farm_name)}
                  disabled={isSaving}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition-colors flex items-center space-x-1.5 self-start sm:self-auto"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete Farm</span>
                </button>
              </div>

              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Farm Name</label>
                  <input
                    type="text"
                    required
                    value={editForm.farm_name || ''}
                    onChange={(e) => setEditForm({ ...editForm, farm_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">District / County</label>
                  <input
                    type="text"
                    required
                    value={editForm.district || ''}
                    onChange={(e) => setEditForm({ ...editForm, district: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Village / Locality</label>
                  <input
                    type="text"
                    required
                    value={editForm.village || ''}
                    onChange={(e) => setEditForm({ ...editForm, village: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Street Address / Landmark</label>
                  <input
                    type="text"
                    value={editForm.address || ''}
                    onChange={(e) => setEditForm({ ...editForm, address: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Latitude Coordinate</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    value={editForm.latitude ?? ''}
                    onChange={(e) => setEditForm({ ...editForm, latitude: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 font-mono focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Longitude Coordinate</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    value={editForm.longitude ?? ''}
                    onChange={(e) => setEditForm({ ...editForm, longitude: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 font-mono focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Total Land Area</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    required
                    value={editForm.total_area ?? ''}
                    onChange={(e) => setEditForm({ ...editForm, total_area: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Area Unit</label>
                  <select
                    value={editForm.area_unit || 'acres'}
                    onChange={(e) => setEditForm({ ...editForm, area_unit: e.target.value as 'acres' | 'hectares' })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="acres">Acres</option>
                    <option value="hectares">Hectares</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-600 font-medium mb-1">Soil Classification</label>
                  <input
                    type="text"
                    value={editForm.soil_type || ''}
                    onChange={(e) => setEditForm({ ...editForm, soil_type: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              {/* Cultivated Area Summary */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-2">
                <div>
                  <span className="font-semibold text-slate-700">Crop Utilization: </span>
                  <span className="font-bold text-emerald-800">
                    {selectedFarm.total_cultivated_area} {selectedFarm.area_unit} cultivated
                  </span>
                  <span className="text-slate-500"> ({selectedFarm.crops_count} active crops)</span>
                </div>
                <div className="text-slate-600">
                  Remaining available: <strong>{Math.max(0, roundTwo(selectedFarm.total_area - selectedFarm.total_cultivated_area))} {selectedFarm.area_unit}</strong>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-6 py-2.5 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60 shadow-md shadow-emerald-600/20 transition-all flex items-center space-x-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  <span>Save Farm Changes</span>
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* Modal: Create Farm */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Building className="w-5 h-5 text-emerald-600" />
                <h3 className="font-bold text-slate-900 text-base">Register New Farm</h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateFarm} className="p-6 space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 font-medium mb-1">Farm Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Sunny Prairie Farm"
                  value={newFarm.farm_name}
                  onChange={(e) => setNewFarm({ ...newFarm, farm_name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-medium mb-1">District / County *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Story County"
                    value={newFarm.district}
                    onChange={(e) => setNewFarm({ ...newFarm, district: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-medium mb-1">Village / Town *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ames"
                    value={newFarm.village}
                    onChange={(e) => setNewFarm({ ...newFarm, village: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Street Address</label>
                <input
                  type="text"
                  placeholder="e.g. 1420 Country Road B"
                  value={newFarm.address}
                  onChange={(e) => setNewFarm({ ...newFarm, address: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-medium mb-1">Total Area *</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    required
                    value={newFarm.total_area}
                    onChange={(e) => setNewFarm({ ...newFarm, total_area: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-medium mb-1">Area Unit</label>
                  <select
                    value={newFarm.area_unit}
                    onChange={(e) => setNewFarm({ ...newFarm, area_unit: e.target.value as 'acres' | 'hectares' })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="acres">Acres</option>
                    <option value="hectares">Hectares</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-medium mb-1">Latitude (-90 to 90) *</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    value={newFarm.latitude}
                    onChange={(e) => setNewFarm({ ...newFarm, latitude: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 font-mono focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-medium mb-1">Longitude (-180 to 180) *</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    value={newFarm.longitude}
                    onChange={(e) => setNewFarm({ ...newFarm, longitude: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 font-mono focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Dominant Soil Type</label>
                <input
                  type="text"
                  placeholder="e.g. Silt Loam"
                  value={newFarm.soil_type || ''}
                  onChange={(e) => setNewFarm({ ...newFarm, soil_type: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60 shadow-md shadow-emerald-600/20 transition-all flex items-center space-x-1.5"
                >
                  {isSaving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Register Farm</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

function roundTwo(num: number): number {
  return Math.round(num * 100) / 100;
}
