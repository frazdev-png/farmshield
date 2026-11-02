import React, { useEffect, useState } from 'react';
import {
  CloudSun,
  CloudRain,
  Sun,
  Wind,
  Droplets,
  Thermometer,
  AlertCircle,
  RefreshCw,
  Building,
  CheckCircle,
  Loader2,
} from 'lucide-react';
import type { Farm, WeatherObservation, DailyForecastItem } from '../../types';
import { api } from '../../services/api';

export const WeatherPlaceholder: React.FC = () => {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState<string | null>(null);
  const [weather, setWeather] = useState<WeatherObservation | null>(null);
  const [forecast, setForecast] = useState<DailyForecastItem[]>([]);
  const [isLoadingFarms, setIsLoadingFarms] = useState(true);
  const [isLoadingWeather, setIsLoadingWeather] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const selectedFarm = farms.find((f) => f.id === selectedFarmId) || farms[0] || null;

  // 1. Load farms
  const loadFarms = async () => {
    setIsLoadingFarms(true);
    try {
      const data = await api.farms.list();
      setFarms(data);
      if (data.length > 0 && !selectedFarmId) {
        setSelectedFarmId(data[0].id);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load farms.');
    } finally {
      setIsLoadingFarms(false);
    }
  };

  // 2. Load weather for selected farm
  const loadWeather = async (farmId: string, refresh = false) => {
    if (refresh) {
      setIsRefreshing(true);
    } else {
      setIsLoadingWeather(true);
    }
    setErrorMessage(null);
    try {
      const obs = refresh
        ? await api.weather.refresh(farmId)
        : await api.weather.getCurrent(farmId);
      setWeather(obs);
      if (obs.forecast_data && Array.isArray(obs.forecast_data)) {
        setForecast(obs.forecast_data);
      } else {
        const fcRes = await api.weather.getForecast(farmId);
        setForecast(fcRes.forecast || []);
      }
      if (refresh) {
        setSuccessMessage('Weather telemetry refreshed successfully from Open-Meteo!');
        setTimeout(() => setSuccessMessage(null), 3500);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to retrieve live weather data.');
    } finally {
      setIsLoadingWeather(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadFarms();
  }, []);

  useEffect(() => {
    if (selectedFarmId) {
      loadWeather(selectedFarmId);
    }
  }, [selectedFarmId]);

  const handleManualRefresh = () => {
    if (selectedFarmId) {
      loadWeather(selectedFarmId, true);
    }
  };

  const formatTimestamp = (ts?: string | null) => {
    if (!ts) return 'N/A';
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' UTC';
    } catch {
      return ts;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Farm Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Micro-Climate & Agro-Meteorology
            </h1>
            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 px-2.5 py-0.5 rounded-full flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse"></span>
              <span>LIVE PROVIDER: OPEN-METEO</span>
            </span>
          </div>
          {selectedFarm ? (
            <p className="text-xs text-slate-600 mt-1">
              Farm: <strong className="text-slate-800">{selectedFarm.farm_name}</strong> • {selectedFarm.village}, {selectedFarm.district} • Coordinates: {selectedFarm.latitude.toFixed(4)}° N, {selectedFarm.longitude.toFixed(4)}° E
            </p>
          ) : (
            <p className="text-xs text-slate-500 mt-1">No farm selected</p>
          )}
        </div>

        {/* Farm Selector & Refresh Button */}
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
            onClick={handleManualRefresh}
            disabled={isRefreshing || !selectedFarmId}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 shadow-xs flex items-center space-x-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh Weather'}</span>
          </button>
        </div>
      </div>

      {/* Alerts & Notifications */}
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

      {/* No Farm Warning */}
      {!isLoadingFarms && farms.length === 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-center space-y-2">
          <Building className="w-10 h-10 text-amber-600 mx-auto" />
          <h3 className="font-bold text-slate-800 text-sm">No Registered Farms Found</h3>
          <p className="text-xs text-slate-600 max-w-md mx-auto">
            Live weather monitoring requires registered farm coordinates. Please register your farm in the Profile / My Farm page to connect agro-meteorology data.
          </p>
        </div>
      )}

      {/* Live Current Weather Metrics (Real Open-Meteo Data) */}
      {selectedFarm && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
              <span>Real-Time Weather Telemetry</span>
              <span className="text-[10px] font-normal text-slate-500 lowercase bg-slate-100 px-2 py-0.5 rounded-md">
                Updated: {formatTimestamp(weather?.fetched_at)}
              </span>
            </h2>
          </div>

          {isLoadingWeather ? (
            <div className="p-8 bg-white rounded-2xl border border-slate-200 text-center flex flex-col items-center justify-center space-y-2">
              <Loader2 className="w-6 h-6 text-emerald-600 animate-spin" />
              <p className="text-xs text-slate-500">Querying Open-Meteo satellite & weather station grid...</p>
            </div>
          ) : weather ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* Temperature */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between text-slate-600 text-xs font-medium">
                  <div className="flex items-center space-x-1.5">
                    <Thermometer className="w-4 h-4 text-emerald-600" />
                    <span>Temperature</span>
                  </div>
                  <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                    REAL
                  </span>
                </div>
                <p className="text-2xl font-bold text-slate-900 mt-2">
                  {weather.temperature !== null && weather.temperature !== undefined ? `${weather.temperature.toFixed(1)}°C` : 'N/A'}
                </p>
                <p className="text-[11px] text-slate-500 font-medium mt-1">
                  Condition: <strong className="text-slate-800">{weather.weather_condition || 'Normal'}</strong>
                </p>
              </div>

              {/* Relative Humidity */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between text-slate-600 text-xs font-medium">
                  <div className="flex items-center space-x-1.5">
                    <Droplets className="w-4 h-4 text-blue-500" />
                    <span>Relative Humidity</span>
                  </div>
                  <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
                    REAL
                  </span>
                </div>
                <p className="text-2xl font-bold text-slate-900 mt-2">
                  {weather.relative_humidity !== null && weather.relative_humidity !== undefined ? `${weather.relative_humidity.toFixed(0)}%` : 'N/A'}
                </p>
                <p className="text-[11px] text-slate-500 font-medium mt-1">
                  Atmospheric moisture index
                </p>
              </div>

              {/* Precipitation */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between text-slate-600 text-xs font-medium">
                  <div className="flex items-center space-x-1.5">
                    <CloudRain className="w-4 h-4 text-indigo-500" />
                    <span>Precipitation</span>
                  </div>
                  <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded">
                    REAL
                  </span>
                </div>
                <p className="text-2xl font-bold text-slate-900 mt-2">
                  {weather.precipitation !== null && weather.precipitation !== undefined ? `${weather.precipitation.toFixed(1)} mm` : '0.0 mm'}
                </p>
                <p className="text-[11px] text-slate-500 font-medium mt-1">
                  Current rainfall rate
                </p>
              </div>

              {/* Wind Speed */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between text-slate-600 text-xs font-medium">
                  <div className="flex items-center space-x-1.5">
                    <Wind className="w-4 h-4 text-amber-500" />
                    <span>Wind Speed</span>
                  </div>
                  <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">
                    REAL
                  </span>
                </div>
                <p className="text-2xl font-bold text-slate-900 mt-2">
                  {weather.wind_speed !== null && weather.wind_speed !== undefined ? `${weather.wind_speed.toFixed(1)} km/h` : 'N/A'}
                </p>
                <p className="text-[11px] text-slate-500 font-medium mt-1">
                  10m above ground surface
                </p>
              </div>
            </div>
          ) : (
            <div className="p-6 bg-slate-50 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
              Weather data unavailable. Click "Refresh Weather" to fetch live data.
            </div>
          )}
        </div>
      )}

      {/* 7-Day Localized Farm Forecast (Real Open-Meteo Data) */}
      {selectedFarm && forecast.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-900 text-base">
              7-Day Localized Forecast (Open-Meteo)
            </h2>
            <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
              VERIFIED FEED
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {forecast.map((item, idx) => {
              const isCold = (item.temperature_min ?? 15) <= 4;
              const isWet = (item.precipitation_sum ?? 0) >= 15;
              return (
                <div
                  key={idx}
                  className={`p-3.5 rounded-xl border text-center flex flex-col justify-between ${
                    isCold
                      ? 'border-rose-300 bg-rose-50/50'
                      : isWet
                      ? 'border-blue-200 bg-blue-50/40'
                      : 'border-slate-200 bg-slate-50/60'
                  }`}
                >
                  <div>
                    <p className="font-bold text-slate-800 text-xs">
                      {idx === 0 ? 'Today' : idx === 1 ? 'Tomorrow' : item.date}
                    </p>
                    <p className="text-[10px] text-slate-500">{item.date}</p>
                  </div>

                  <div className="my-3 flex justify-center">
                    {isWet ? (
                      <CloudRain className="w-8 h-8 text-blue-500" />
                    ) : item.weather_condition.includes('Clear') || item.weather_condition.includes('Sun') ? (
                      <Sun className="w-8 h-8 text-amber-500" />
                    ) : (
                      <CloudSun className="w-8 h-8 text-emerald-600" />
                    )}
                  </div>

                  <div className="space-y-1">
                    <p className="text-sm font-bold text-slate-900">
                      {item.temperature_max !== null && item.temperature_max !== undefined ? `${item.temperature_max.toFixed(0)}°` : '--'} /{' '}
                      <span className="text-slate-500 font-normal">
                        {item.temperature_min !== null && item.temperature_min !== undefined ? `${item.temperature_min.toFixed(0)}°` : '--'}
                      </span>
                    </p>
                    <p className="text-[10px] text-slate-600 leading-tight">
                      {item.weather_condition}
                    </p>
                    <div className="text-[10px] font-medium text-blue-600 pt-1">
                      🌧 {item.precipitation_sum !== null && item.precipitation_sum !== undefined ? `${item.precipitation_sum.toFixed(1)} mm` : '0 mm'}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
