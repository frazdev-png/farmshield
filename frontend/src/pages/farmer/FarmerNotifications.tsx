import React, { useState, useEffect, useCallback } from 'react';
import {
  Bell,
  AlertTriangle,
  Check,
  CheckCheck,
  Smartphone,
  ShieldCheck,
  RefreshCw,
  Info,
  Flame,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { api } from '../../services/api';
import type { NotificationItem, FarmerPreference } from '../../types';

export const FarmerNotifications: React.FC = () => {
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [preference, setPreference] = useState<FarmerPreference | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSavingPref, setIsSavingPref] = useState<boolean>(false);
  const [prefSuccessMsg, setPrefSuccessMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [notifsRes, prefRes] = await Promise.all([
        api.notifications.list({ limit: 100 }),
        api.notifications.getPreferences(),
      ]);
      setNotifications(notifsRes.items || []);
      setPreference(prefRes);
    } catch (err: any) {
      console.error('Failed to load notifications:', err);
      setError(err?.message || 'Failed to load notifications feed from server.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleToggleConsent = async () => {
    if (!preference) return;
    setIsSavingPref(true);
    setPrefSuccessMsg(null);
    const newConsent = !preference.sms_consent;
    try {
      const updated = await api.notifications.updatePreferences({
        sms_consent: newConsent,
        language_preference: preference.language_preference || 'en',
      });
      setPreference(updated);
      setPrefSuccessMsg(
        newConsent
          ? 'SMS alert dispatch enabled. Critical and High agricultural hazards will be forwarded to your mobile handset.'
          : 'SMS alerts disabled. You will continue to receive secure in-app alerts on your dashboard.'
      );
      setTimeout(() => setPrefSuccessMsg(null), 5000);
    } catch (err: any) {
      setError(err?.message || 'Failed to update SMS consent preference.');
    } finally {
      setIsSavingPref(false);
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      await api.notifications.markRead(id);
      setNotifications((prev) =>
        prev.map((item) => (item.id === id ? { ...item, is_read: true } : item))
      );
    } catch (err: any) {
      console.error('Failed to mark notification read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.notifications.markAllRead();
      setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));
    } catch (err: any) {
      console.error('Failed to mark all notifications read:', err);
    }
  };

  const visibleNotifications =
    filter === 'unread' ? notifications.filter((n) => !n.is_read) : notifications;

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const formatTimestamp = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleString(undefined, {
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
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Farm Notifications & Advisory Feed
            </h1>
            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 px-2.5 py-0.5 rounded-full">
              AWS SNS CONNECTED
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Real-time agro-climatic hazard alerts • Multi-channel delivery with AWS SNS
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => loadData()}
            className="p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
            title="Refresh feed"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setFilter(filter === 'all' ? 'unread' : 'all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === 'unread'
                ? 'bg-emerald-600 text-white'
                : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {filter === 'unread' ? `Showing Unread (${unreadCount})` : `Show Only Unread (${unreadCount})`}
          </button>
          <button
            onClick={handleMarkAllRead}
            disabled={unreadCount === 0}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-emerald-700 bg-white border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
          >
            <CheckCheck className="w-3.5 h-3.5" />
            <span>Mark All Read</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {prefSuccessMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center space-x-2 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{prefSuccessMsg}</span>
        </div>
      )}

      {/* SMS Consent Card */}
      <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-2xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-xs">
              <Smartphone className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-sm font-bold text-slate-900">
                  SMS Emergency Hazard Notifications (AWS SNS)
                </h2>
                {preference?.sms_consent ? (
                  <span className="text-[10px] font-bold bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded-full flex items-center space-x-1">
                    <ShieldCheck className="w-3 h-3 inline" />
                    <span>CONSENT ACTIVE</span>
                  </span>
                ) : (
                  <span className="text-[10px] font-bold bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full">
                    OPTED OUT
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-600 mt-1 max-w-2xl leading-relaxed">
                When activated, critical agro-climatic advisories (frost, extreme heat, flood, pest outbreaks) are automatically dispatched to your verified mobile handset via AWS Simple Notification Service.
              </p>
              {preference?.sms_consent_at && (
                <p className="text-[10px] text-slate-500 mt-1.5 flex items-center space-x-1">
                  <Info className="w-3 h-3 text-emerald-600" />
                  <span>
                    Consent recorded: {formatTimestamp(preference.sms_consent_at)}
                  </span>
                </p>
              )}
            </div>
          </div>

          <div className="shrink-0 flex items-center space-x-3 sm:self-center">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={preference?.sms_consent || false}
                onChange={handleToggleConsent}
                disabled={isSavingPref || !preference}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-300 peer-focus:outline-hidden rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
            </label>
            <span className="text-xs font-semibold text-slate-800">
              {preference?.sms_consent ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>
      </div>

      {/* Notifications List */}
      <div className="space-y-3">
        {isLoading && notifications.length === 0 ? (
          <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 text-slate-600 text-xs flex flex-col items-center justify-center space-y-2">
            <RefreshCw className="w-5 h-5 animate-spin text-emerald-600" />
            <span>Loading notifications feed...</span>
          </div>
        ) : visibleNotifications.length === 0 ? (
          <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 text-slate-600 text-xs space-y-2">
            <Bell className="w-8 h-8 mx-auto text-slate-300" />
            <p className="font-semibold text-slate-700">No notifications to display</p>
            <p className="text-[11px] text-slate-500">
              {filter === 'unread'
                ? 'You have caught up with all risk advisories!'
                : 'As your weather observations and crop risks are evaluated, automated advisories will appear here.'}
            </p>
          </div>
        ) : (
          visibleNotifications.map((n) => {
            const isCritical = n.severity === 'CRITICAL';
            const isHigh = n.severity === 'HIGH';
            const isModerate = n.severity === 'MODERATE';

            return (
              <div
                key={n.id}
                className={`p-4 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-start justify-between gap-4 ${
                  !n.is_read
                    ? isCritical
                      ? 'bg-rose-50/40 border-rose-300 shadow-xs ring-1 ring-rose-500/20'
                      : isHigh
                      ? 'bg-amber-50/40 border-amber-300 shadow-xs ring-1 ring-amber-500/20'
                      : 'bg-white border-emerald-300 shadow-xs ring-1 ring-emerald-500/10'
                    : 'bg-slate-50/70 border-slate-200'
                }`}
              >
                <div className="flex items-start space-x-3.5">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                      isCritical
                        ? 'bg-rose-100 text-rose-600'
                        : isHigh
                        ? 'bg-amber-100 text-amber-700'
                        : isModerate
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-emerald-100 text-emerald-700'
                    }`}
                  >
                    {isCritical ? (
                      <Flame className="w-4 h-4" />
                    ) : isHigh ? (
                      <AlertTriangle className="w-4 h-4" />
                    ) : (
                      <Bell className="w-4 h-4" />
                    )}
                  </div>

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-xs font-bold text-slate-900">{n.title}</h3>
                      {!n.is_read && (
                        <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                      )}
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded-md uppercase ${
                          isCritical
                            ? 'bg-rose-100 text-rose-800 border border-rose-300'
                            : isHigh
                            ? 'bg-amber-100 text-amber-800 border border-amber-300'
                            : isModerate
                            ? 'bg-yellow-100 text-yellow-800 border border-yellow-300'
                            : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        }`}
                      >
                        {n.severity}
                      </span>
                      {n.channel === 'both' || n.channel === 'sms' ? (
                        <span className="text-[9px] font-medium bg-purple-100 text-purple-800 border border-purple-200 px-1.5 py-0.5 rounded-md flex items-center space-x-1">
                          <Smartphone className="w-2.5 h-2.5 inline" />
                          <span>SMS</span>
                        </span>
                      ) : (
                        <span className="text-[9px] font-medium bg-slate-100 text-slate-700 border border-slate-200 px-1.5 py-0.5 rounded-md">
                          In-App
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-slate-700 leading-relaxed">{n.message}</p>

                    {/* Metadata footer */}
                    <div className="flex flex-wrap items-center gap-3 pt-1 text-[10px] text-slate-500">
                      <span>{formatTimestamp(n.created_at)}</span>
                      {n.masked_phone_number && (
                        <span className="text-slate-600 font-mono">
                          To: {n.masked_phone_number}
                        </span>
                      )}
                      {n.sns_message_id && (
                        <span className="text-emerald-700 font-mono flex items-center space-x-0.5">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600 inline" />
                          <span>SNS Accepted</span>
                        </span>
                      )}
                      {n.status === 'failed' && n.error_message && (
                        <span className="text-rose-600 flex items-center space-x-0.5" title={n.error_message}>
                          <XCircle className="w-3 h-3 inline" />
                          <span>Dispatch Failed</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0 self-end sm:self-center">
                  {!n.is_read ? (
                    <button
                      onClick={() => handleMarkRead(n.id)}
                      className="px-2.5 py-1 text-xs text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg flex items-center space-x-1 transition-colors"
                      title="Mark as read"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Mark Read</span>
                    </button>
                  ) : (
                    <span className="text-[11px] text-slate-400 flex items-center space-x-1 px-2 py-1">
                      <CheckCheck className="w-3.5 h-3.5 text-slate-400" />
                      <span>Read</span>
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
