import React, { useEffect, useState } from 'react';
import {
  Wheat,
  Plus,
  Trash2,
  Edit2,
  Building,
  CheckCircle,
  XCircle,
  Loader2,
} from 'lucide-react';
import type { Farm, FarmCrop, FarmCropCreatePayload } from '../../types';
import { api } from '../../services/api';

export const CropFarmPlaceholder: React.FC = () => {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState<string | null>(null);
  const [crops, setCrops] = useState<FarmCrop[]>([]);
  const [isLoadingFarms, setIsLoadingFarms] = useState(true);
  const [isLoadingCrops, setIsLoadingCrops] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Crop Modal state
  const [showCropModal, setShowCropModal] = useState(false);
  const [editingCropId, setEditingCropId] = useState<string | null>(null);
  const [cropForm, setCropForm] = useState<FarmCropCreatePayload>(() => ({
    crop_name: '',
    variety: '',
    cultivated_area: 25.0,
    area_unit: 'acres',
    sowing_date: '2026-03-01',
  }));

  const selectedFarm = farms.find((f) => f.id === selectedFarmId) || farms[0] || null;

  // Load farmer's farms
  const loadFarms = async () => {
    setIsLoadingFarms(true);
    setErrorMessage(null);
    try {
      const farmList = await api.farms.list();
      setFarms(farmList);
      if (farmList.length > 0 && !selectedFarmId) {
        setSelectedFarmId(farmList[0].id);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load farms.');
    } finally {
      setIsLoadingFarms(false);
    }
  };

  useEffect(() => {
    loadFarms();
  }, []);

  // Load crops for selected farm
  const loadCrops = async (farmId: string) => {
    setIsLoadingCrops(true);
    setErrorMessage(null);
    try {
      const cropList = await api.farms.crops.list(farmId);
      setCrops(cropList);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load crops for selected farm.');
    } finally {
      setIsLoadingCrops(false);
    }
  };

  useEffect(() => {
    if (selectedFarmId) {
      loadCrops(selectedFarmId);
    } else {
      setCrops([]);
    }
  }, [selectedFarmId]);

  const handleOpenAddCrop = () => {
    setEditingCropId(null);
    setCropForm({
      crop_name: '',
      variety: '',
      cultivated_area: 20.0,
      area_unit: selectedFarm ? selectedFarm.area_unit : 'acres',
      sowing_date: new Date().toISOString().split('T')[0],
    });
    setShowCropModal(true);
  };

  const handleOpenEditCrop = (crop: FarmCrop) => {
    setEditingCropId(crop.id);
    setCropForm({
      crop_name: crop.crop_name,
      variety: crop.variety || '',
      cultivated_area: crop.cultivated_area,
      area_unit: crop.area_unit,
      sowing_date: crop.sowing_date || '',
    });
    setShowCropModal(true);
  };

  const handleSaveCrop = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFarmId) return;
    setIsSaving(true);
    setErrorMessage(null);

    try {
      if (editingCropId) {
        await api.farms.crops.update(selectedFarmId, editingCropId, cropForm);
        setSuccessMessage(`Crop "${cropForm.crop_name}" updated successfully!`);
      } else {
        await api.farms.crops.create(selectedFarmId, cropForm);
        setSuccessMessage(`Crop "${cropForm.crop_name}" planted and recorded!`);
      }
      setShowCropModal(false);
      await loadCrops(selectedFarmId);
      await loadFarms(); // Refresh totals on farm object
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to save crop.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteCrop = async (cropId: string, cropName: string) => {
    if (!selectedFarmId) return;
    if (!window.confirm(`Are you sure you want to remove crop plot "${cropName}"?`)) return;

    setIsSaving(true);
    setErrorMessage(null);
    try {
      await api.farms.crops.delete(selectedFarmId, cropId);
      setSuccessMessage(`Crop plot "${cropName}" removed.`);
      await loadCrops(selectedFarmId);
      await loadFarms();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to remove crop.');
    } finally {
      setIsSaving(false);
    }
  };

  // Calculate total cultivated area of current crops
  const totalCultivatedArea = crops.reduce((acc, c) => acc + c.cultivated_area, 0);
  const totalFarmArea = selectedFarm ? selectedFarm.total_area : 0;
  const cultivationPercent = totalFarmArea > 0 ? Math.min(100, Math.round((totalCultivatedArea / totalFarmArea) * 100)) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Crops & Cultivated Land Parcels
            </h1>
            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-full">
              LIVE POSTGRESQL APIS
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Real-time crop inventory, seed varieties, sown acreage, and parcel allocations
          </p>
        </div>

        {selectedFarm && (
          <button
            onClick={handleOpenAddCrop}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm transition-colors flex items-center space-x-1.5 self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Add Crop Plot</span>
          </button>
        )}
      </div>

      {/* Notifications */}
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

      {/* Farm Selector Bar */}
      {isLoadingFarms ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center">
          <Loader2 className="w-6 h-6 text-emerald-600 animate-spin mx-auto mb-2" />
          <p className="text-xs text-slate-600 font-medium">Loading farms...</p>
        </div>
      ) : farms.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-10 text-center space-y-3">
          <Building className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="font-bold text-slate-800 text-base">No Farms Available</h3>
          <p className="text-xs text-slate-600 max-w-sm mx-auto">
            You must register a farm property before planting crops. Navigate to "My Farm Profile" to create one.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Farm Switcher */}
          <div className="flex items-center space-x-2 overflow-x-auto pb-1">
            <span className="text-xs font-bold text-slate-600 uppercase tracking-wider shrink-0 mr-1">
              Select Farm:
            </span>
            {farms.map((farm) => {
              const isSelected = selectedFarm?.id === farm.id;
              return (
                <button
                  key={farm.id}
                  onClick={() => setSelectedFarmId(farm.id)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all shrink-0 flex items-center space-x-2 border ${
                    isSelected
                      ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <Building className="w-3.5 h-3.5" />
                  <span>{farm.farm_name}</span>
                </button>
              );
            })}
          </div>

          {/* Farm Utilization Card */}
          {selectedFarm && (
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                <div>
                  <h2 className="text-base font-bold text-slate-900">{selectedFarm.farm_name}</h2>
                  <p className="text-xs text-slate-500">
                    Location: {selectedFarm.village}, {selectedFarm.district} • Total Area: <strong>{selectedFarm.total_area} {selectedFarm.area_unit}</strong>
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-slate-900">
                    {totalCultivatedArea} / {selectedFarm.total_area} {selectedFarm.area_unit} Cultivated
                  </span>
                  <span className="text-xs text-slate-500 ml-2">({cultivationPercent}%)</span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                <div
                  className={`h-2.5 rounded-full transition-all duration-500 ${
                    cultivationPercent > 95
                      ? 'bg-rose-500'
                      : cultivationPercent > 75
                      ? 'bg-amber-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${cultivationPercent}%` }}
                />
              </div>
            </div>
          )}

          {/* Crops Grid */}
          {isLoadingCrops ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
              <Loader2 className="w-6 h-6 text-emerald-600 animate-spin mx-auto mb-2" />
              <p className="text-xs text-slate-600 font-medium">Loading crops on this farm...</p>
            </div>
          ) : crops.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-10 text-center space-y-3">
              <Wheat className="w-10 h-10 text-slate-300 mx-auto" />
              <h3 className="font-bold text-slate-800 text-base">No Crops Planted Yet</h3>
              <p className="text-xs text-slate-600 max-w-sm mx-auto">
                No crops have been allocated to <strong>{selectedFarm?.farm_name}</strong>. Click below to add your first crop plot.
              </p>
              <button
                onClick={handleOpenAddCrop}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm transition-colors inline-flex items-center space-x-1.5"
              >
                <Plus className="w-4 h-4" />
                <span>Add First Crop Plot</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {crops.map((crop) => (
                <div
                  key={crop.id}
                  className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs hover:border-emerald-300 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded truncate max-w-[150px]">
                        {crop.id.slice(0, 8)}...
                      </span>
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => handleOpenEditCrop(crop)}
                          className="p-1 text-slate-400 hover:text-emerald-700 transition-colors"
                          title="Edit crop details"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteCrop(crop.id, crop.crop_name)}
                          className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
                          title="Delete crop plot"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center space-x-2">
                      <Wheat className="w-5 h-5 text-emerald-600" />
                      <h3 className="font-bold text-slate-900 text-base">{crop.crop_name}</h3>
                    </div>
                    {crop.variety && (
                      <p className="text-xs text-slate-600 mt-0.5">Variety: {crop.variety}</p>
                    )}

                    <div className="mt-4 pt-3 border-t border-slate-100 space-y-2 text-xs">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Cultivated Area:</span>
                        <span className="font-bold text-slate-900">
                          {crop.cultivated_area} {crop.area_unit}
                        </span>
                      </div>

                      {crop.sowing_date && (
                        <div className="flex justify-between">
                          <span className="text-slate-500">Sown / Planted:</span>
                          <span className="text-slate-700 font-medium">{crop.sowing_date}</span>
                        </div>
                      )}

                      <div className="flex justify-between">
                        <span className="text-slate-500">Recorded:</span>
                        <span className="text-slate-500 text-[11px]">
                          {new Date(crop.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
                    <span className="text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded">
                      Active Plot
                    </span>
                    <span className="text-slate-400 font-mono">
                      {Math.round((crop.cultivated_area / (selectedFarm?.total_area || 1)) * 100)}% of farm
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Sensor Telemetry Placeholder (Clearly Marked DEMO) */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">
                Soil Chemistry & Micro-Station Sensor Feed
              </h3>
              <span className="text-[10px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full border border-amber-300">
                DEMO TELEMETRY
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Live multi-spectral NDVI imagery and in-ground IoT probe calibrations will connect in Step 4.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-slate-600 text-[11px] block">Soil pH Index</span>
                <span className="text-xl font-bold text-slate-900">6.5 pH</span>
                <span className="text-[10px] text-emerald-600 font-medium block mt-0.5">Optimal for {crops[0]?.crop_name || 'Crops'}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-slate-600 text-[11px] block">Soil Moisture</span>
                <span className="text-xl font-bold text-slate-900">32%</span>
                <span className="text-[10px] text-emerald-600 font-medium block mt-0.5">Sufficient moisture</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-slate-600 text-[11px] block">Nitrogen Available</span>
                <span className="text-xl font-bold text-slate-900">45 ppm</span>
                <span className="text-[10px] text-amber-600 font-medium block mt-0.5">Seasonal baseline</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-slate-600 text-[11px] block">NDVI Canopy Health</span>
                <span className="text-xl font-bold text-slate-900">0.78</span>
                <span className="text-[10px] text-emerald-600 font-medium block mt-0.5">High vigor</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Add/Edit Crop */}
      {showCropModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Wheat className="w-5 h-5 text-emerald-600" />
                <h3 className="font-bold text-slate-900 text-base">
                  {editingCropId ? 'Edit Crop Plot' : 'Add Crop to Farm'}
                </h3>
              </div>
              <button
                onClick={() => setShowCropModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveCrop} className="p-6 space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 font-medium mb-1">Crop Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Maize, Hard Red Winter Wheat, Soybeans"
                  value={cropForm.crop_name}
                  onChange={(e) => setCropForm({ ...cropForm, crop_name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Seed Variety / Cultivar</label>
                <input
                  type="text"
                  placeholder="e.g. Pioneer P1197AM, Asgrow AG27XF1"
                  value={cropForm.variety || ''}
                  onChange={(e) => setCropForm({ ...cropForm, variety: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-medium mb-1">Cultivated Area *</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    required
                    value={cropForm.cultivated_area}
                    onChange={(e) => setCropForm({ ...cropForm, cultivated_area: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-medium mb-1">Area Unit</label>
                  <select
                    value={cropForm.area_unit}
                    onChange={(e) => setCropForm({ ...cropForm, area_unit: e.target.value as 'acres' | 'hectares' })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="acres">Acres</option>
                    <option value="hectares">Hectares</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Sowing / Planting Date</label>
                <input
                  type="date"
                  value={cropForm.sowing_date || ''}
                  onChange={(e) => setCropForm({ ...cropForm, sowing_date: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowCropModal(false)}
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
                  <span>{editingCropId ? 'Save Changes' : 'Record Crop Plot'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
