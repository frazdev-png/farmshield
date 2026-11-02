import React, { useState } from 'react';
import {
  Sprout,
  MapPin,
  Mail,
  Phone,
  User as UserIcon,
  Wheat,
  CheckCircle,
  ArrowRight,
  Info,
  Lock,
  XCircle,
  Loader2,
  Navigation,
} from 'lucide-react';
import type { NavigationTab, User } from '../../types';
import { useAuth } from '../../context/useAuth';

interface RegisterPageProps {
  onNavigate: (tab: NavigationTab) => void;
}

const REGIONAL_COORDINATES: Record<string, { lat: number; lon: number }> = {
  Lahore: { lat: 31.5204, lon: 74.3587 },
  Multan: { lat: 30.1575, lon: 71.5249 },
  Faisalabad: { lat: 31.4187, lon: 73.0791 },
  Sahiwal: { lat: 30.6682, lon: 73.1114 },
  Sargodha: { lat: 32.0836, lon: 72.6711 },
  Gujranwala: { lat: 32.1877, lon: 74.1945 },
  Rawalpindi: { lat: 33.5651, lon: 73.0169 },
  Peshawar: { lat: 34.0151, lon: 71.5249 },
  Quetta: { lat: 30.1798, lon: 66.9750 },
  Karachi: { lat: 24.8607, lon: 67.0011 },
  Hyderabad: { lat: 25.3960, lon: 68.3578 },
  Kasur: { lat: 31.1167, lon: 74.4500 },
  Vehari: { lat: 30.0452, lon: 72.3489 },
  Other: { lat: 31.5204, lon: 74.3587 },
};

export const RegisterPage: React.FC<RegisterPageProps> = ({ onNavigate }) => {
  const { register } = useAuth();

  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    farmName: '',
    district: 'Lahore',
    village: '',
    latitude: 31.5204,
    longitude: 74.3587,
    acreage: '20',
    primaryCrops: 'Wheat, Rice',
    soilType: 'Loam',
  });

  const [isLocating, setIsLocating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [registeredUser, setRegisteredUser] = useState<User | null>(null);

  const handleDistrictChange = (districtName: string) => {
    const coords = REGIONAL_COORDINATES[districtName];
    if (coords) {
      setFormData((prev) => ({
        ...prev,
        district: districtName,
        latitude: coords.lat,
        longitude: coords.lon,
      }));
    } else {
      setFormData((prev) => ({ ...prev, district: districtName }));
    }
  };

  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      setErrorMessage('Geolocation is not supported by your browser.');
      return;
    }

    setIsLocating(true);
    setErrorMessage(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsLocating(false);
        const lat = parseFloat(pos.coords.latitude.toFixed(4));
        const lon = parseFloat(pos.coords.longitude.toFixed(4));
        setFormData((prev) => ({
          ...prev,
          latitude: lat,
          longitude: lon,
          district: prev.district || 'My GPS Location',
        }));
      },
      (err) => {
        setIsLocating(false);
        setErrorMessage(`Unable to retrieve GPS coordinates: ${err.message}. You can enter them manually.`);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (formData.password.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    if (!formData.farmName.trim()) {
      setErrorMessage('Please provide your farm name.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await register({
        full_name: formData.fullName.trim(),
        email: formData.email.trim(),
        phone_number: formData.phone.trim(),
        password: formData.password,
        farm_name: formData.farmName.trim(),
        district: formData.district.trim(),
        village: formData.village.trim() || 'Central',
        region: formData.district.trim(),
        latitude: Number(formData.latitude),
        longitude: Number(formData.longitude),
        total_area: parseFloat(formData.acreage) || 10.0,
        acreage: formData.acreage,
        primary_crops: formData.primaryCrops.trim(),
        soil_type: formData.soilType.trim(),
      });
      setRegisteredUser(user);
      try {
        sessionStorage.setItem(
          'farmshield_reg_notice',
          `Account created successfully! Welcome, ${user.full_name}. Please sign in to access your live farm dashboard.`
        );
        sessionStorage.setItem('farmshield_reg_email', formData.email.trim());
      } catch {
        // ignore
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Registration failed. Please check form inputs.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-4 py-12">
      <div className="max-w-2xl w-full bg-white rounded-2xl border border-slate-200 shadow-xl p-6 sm:p-10 space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-emerald-600 text-white shadow-md shadow-emerald-500/20">
            <Sprout className="w-6 h-6" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Register Real Farmer Account
          </h2>
          <p className="text-xs sm:text-sm text-slate-600">
            Set up your credentials and register your farm with GPS coordinates for live Open-Meteo weather.
          </p>
        </div>

        {/* Live Open-Meteo Connection Indicator */}
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 text-xs text-emerald-900 flex items-start space-x-3">
          <Info className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-emerald-900">Real Location Weather Integration</p>
            <p className="text-emerald-800 text-[11px] mt-0.5">
              The latitude and longitude you choose below will be used by Open-Meteo to fetch actual live weather, humidity, and rainfall forecasts for your farm.
            </p>
          </div>
        </div>

        {errorMessage && (
          <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2.5">
            <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {registeredUser ? (
          <div className="text-center py-8 space-y-4 bg-emerald-50/60 border border-emerald-200 rounded-2xl p-6">
            <div className="w-14 h-14 bg-emerald-600 text-white rounded-full flex items-center justify-center mx-auto shadow-lg shadow-emerald-600/30">
              <CheckCircle className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Account & Farm Registered!</h3>
            <p className="text-xs text-slate-600 max-w-md mx-auto">
              Welcome, <strong className="text-slate-800">{registeredUser.full_name}</strong>! Your account (<span className="font-mono text-emerald-700">{registeredUser.email}</span>) and farm location have been saved in the database.
            </p>
            <p className="text-xs text-emerald-800">
              You can now sign in to view live Open-Meteo weather telemetry and risk assessments for your farm.
            </p>
            <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => onNavigate('login')}
                className="w-full sm:w-auto px-6 py-2.5 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-md transition-all flex items-center justify-center space-x-1.5"
              >
                <span>Proceed to Sign In</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5 text-xs">
            <div className="border-b border-slate-100 pb-2">
              <h4 className="font-bold uppercase text-[11px] tracking-wider text-emerald-800">
                1. Farmer Contact & Credentials
              </h4>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Your Full Name</label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ahmad Faraz"
                    value={formData.fullName}
                    onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Email Address</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="email"
                    required
                    placeholder="e.g. faraz@example.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">Phone Number (SMS Hazard Alerts)</label>
                <div className="relative">
                  <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="tel"
                    required
                    placeholder="+92 300 1234567"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Password (min 8 chars)</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Confirm Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    placeholder="••••••••"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>
            </div>

            <div className="border-b border-slate-100 pb-2 pt-2">
              <h4 className="font-bold uppercase text-[11px] tracking-wider text-emerald-800">
                2. Farm Location & Real GPS Coordinates
              </h4>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Farm Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Faraz Model Farm"
                  value={formData.farmName}
                  onChange={(e) => setFormData({ ...formData, farmName: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">City / District Location</label>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <select
                    value={formData.district}
                    onChange={(e) => handleDistrictChange(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 bg-white focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                  >
                    {Object.keys(REGIONAL_COORDINATES).map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Village / Sector</label>
                <input
                  type="text"
                  placeholder="e.g. Chak 42 or Raiwind"
                  value={formData.village}
                  onChange={(e) => setFormData({ ...formData, village: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block font-medium text-slate-700">GPS Coordinates</label>
                  <button
                    type="button"
                    onClick={handleDetectLocation}
                    disabled={isLocating}
                    className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 flex items-center space-x-1"
                  >
                    <Navigation className={`w-3 h-3 ${isLocating ? 'animate-spin' : ''}`} />
                    <span>{isLocating ? 'Detecting...' : 'Detect GPS'}</span>
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number"
                    step="0.0001"
                    required
                    title="Latitude"
                    placeholder="Latitude"
                    value={formData.latitude}
                    onChange={(e) => setFormData({ ...formData, latitude: parseFloat(e.target.value) || 0 })}
                    className="w-full px-2.5 py-2 border border-slate-300 rounded-lg text-xs font-mono text-slate-800 focus:ring-2 focus:ring-emerald-500"
                  />
                  <input
                    type="number"
                    step="0.0001"
                    required
                    title="Longitude"
                    placeholder="Longitude"
                    value={formData.longitude}
                    onChange={(e) => setFormData({ ...formData, longitude: parseFloat(e.target.value) || 0 })}
                    className="w-full px-2.5 py-2 border border-slate-300 rounded-lg text-xs font-mono text-slate-800 focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Total Acreage</label>
                <input
                  type="number"
                  required
                  placeholder="e.g. 20"
                  value={formData.acreage}
                  onChange={(e) => setFormData({ ...formData, acreage: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Primary Crops</label>
                <div className="relative">
                  <Wheat className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Wheat, Rice, Cotton"
                    value={formData.primaryCrops}
                    onChange={(e) => setFormData({ ...formData, primaryCrops: e.target.value })}
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 rounded-xl text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60 shadow-md shadow-emerald-600/20 transition-all flex items-center justify-center space-x-2 mt-4"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Registering Account & Farm in Database...</span>
                </>
              ) : (
                <>
                  <span>Create Account & Register Farm</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        )}

        <div className="pt-2 border-t border-slate-100 text-center text-xs text-slate-600">
          <span>Already have registered credentials? </span>
          <button
            type="button"
            onClick={() => onNavigate('login')}
            className="font-semibold text-emerald-600 hover:underline"
          >
            Sign in to existing account
          </button>
        </div>
      </div>
    </div>
  );
};
