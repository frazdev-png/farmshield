import React, { useState, useEffect, useCallback } from 'react';
import {
  Send,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Smartphone,
  ShieldAlert,
  Eye,
  Check,
  RotateCcw,
} from 'lucide-react';
import { api } from '../../services/api';
import type {
  NotificationItem,
  AdminBroadcastResponse,
  AdminBroadcastPreviewResponse,
} from '../../types';

export const AdminNotifications: React.FC = () => {
  const [targetDistrict, setTargetDistrict] = useState('all');
  const [title, setTitle] = useState('Critical Agro-Climatic Warning');
  const [severity, setSeverity] = useState<'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW'>('CRITICAL');
  const [message, setMessage] = useState(
    'URGENT: Extreme weather threshold exceeded. Inspect field drainage and prepare protective crop treatments immediately.'
  );

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isPreviewing, setIsPreviewing] = useState<boolean>(false);
  const [isBroadcasting, setIsBroadcasting] = useState<boolean>(false);
  const [isRetrying, setIsRetrying] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<AdminBroadcastPreviewResponse | null>(null);
  const [broadcastResult, setBroadcastResult] = useState<AdminBroadcastResponse | null>(null);
  const [retryResult, setRetryResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadNotifications = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.admin.notifications.list({ limit: 50 });
      setNotifications(response.items || []);
    } catch (err: any) {
      console.error('Failed to load admin notifications:', err);
      setError(err?.message || 'Failed to retrieve notification records from server.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const handlePreview = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsPreviewing(true);
    setError(null);
    setBroadcastResult(null);

    try {
      const preview = await api.admin.notifications.preview({
        title,
        message,
        severity,
        district: targetDistrict === 'all' ? undefined : targetDistrict,
      });
      setPreviewData(preview);
    } catch (err: any) {
      console.error('Failed to preview broadcast:', err);
      setError(err?.message || 'Failed to generate audience preview.');
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleConfirmBroadcast = async () => {
    setIsBroadcasting(true);
    setError(null);

    try {
      const res = await api.admin.notifications.broadcast({
        title,
        message,
        severity,
        district: targetDistrict === 'all' ? undefined : targetDistrict,
        confirmed: true,
      });
      setBroadcastResult(res);
      setPreviewData(null);
      await loadNotifications();
    } catch (err: any) {
      console.error('Failed to dispatch broadcast:', err);
      setError(err?.message || 'Failed to dispatch regional emergency broadcast.');
    } finally {
      setIsBroadcasting(false);
    }
  };

  const handleRetryFailed = async () => {
    setIsRetrying(true);
    setRetryResult(null);
    setError(null);

    try {
      const res = await api.admin.notifications.retry(20);
      setRetryResult(`Successfully processed ${res.total} transient delivery attempts.`);
      await loadNotifications();
      setTimeout(() => setRetryResult(null), 5000);
    } catch (err: any) {
      setError(err?.message || 'Failed to retry transient failures.');
    } finally {
      setIsRetrying(false);
    }
  };

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
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Emergency Broadcast Console & Dispatch Logs
            </h1>
            <span className="text-[10px] font-bold bg-slate-900 text-emerald-400 border border-slate-700 px-2.5 py-0.5 rounded-full flex items-center space-x-1">
              <Smartphone className="w-3 h-3 inline text-emerald-400" />
              <span>AWS SNS OUTBOX READY</span>
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Dispatch bulk SMS advisories with 2-phase confirmation, preview safety, and audit logs
          </p>
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto">
          <button
            onClick={handleRetryFailed}
            disabled={isRetrying}
            className="px-3 py-1.5 text-xs text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-300 rounded-lg transition-colors flex items-center space-x-1 disabled:opacity-50"
            title="Retry transiently failed SMS dispatches"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
            <span>Retry Failed SMS</span>
          </button>
          <button
            onClick={() => loadNotifications()}
            className="p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
            title="Refresh dispatch logs"
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

      {retryResult && (
        <div className="p-3 bg-amber-50 border border-amber-300 text-amber-900 text-xs rounded-xl flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-amber-600" />
          <span>{retryResult}</span>
        </div>
      )}

      {broadcastResult && (
        <div className="p-4 bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center space-x-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <p className="font-bold text-emerald-900">{broadcastResult.message}</p>
              <p className="text-[11px] text-emerald-700 mt-0.5">
                Targeted Farmers: {broadcastResult.target_farmers_count} • In-App Queued: {broadcastResult.notifications_queued} • SMS Accepted by AWS SNS: {broadcastResult.sms_accepted_count}
              </p>
            </div>
          </div>
          <button
            onClick={() => setBroadcastResult(null)}
            className="text-[10px] text-emerald-700 hover:text-emerald-900 underline font-semibold shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Broadcast Form & Preview */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <h2 className="font-bold text-slate-900 text-sm flex items-center space-x-2">
          <Send className="w-4 h-4 text-emerald-600" />
          <span>Compose Regional Hazard Advisory (2-Step Safety Dispatch)</span>
        </h2>

        <form onSubmit={handlePreview} className="space-y-4 text-xs">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-slate-600 font-medium mb-1">Target District / Cluster</label>
              <select
                value={targetDistrict}
                onChange={(e) => {
                  setTargetDistrict(e.target.value);
                  setPreviewData(null);
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-800 focus:ring-2 focus:ring-emerald-500 bg-white"
              >
                <option value="all">All Enrolled Districts</option>
                <option value="Cedar Valley">Cedar Valley</option>
                <option value="Des Moines River">Des Moines River</option>
                <option value="Platte Valley">Platte Valley</option>
                <option value="Green District">Green District</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1">Advisory Subject / Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  setPreviewData(null);
                }}
                placeholder="Brief advisory headline"
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-800 focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1">Severity & Priority</label>
              <select
                value={severity}
                onChange={(e) => {
                  setSeverity(e.target.value as any);
                  setPreviewData(null);
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-800 focus:ring-2 focus:ring-emerald-500 bg-white"
              >
                <option value="CRITICAL">CRITICAL (Urgent SMS & Dashboard)</option>
                <option value="HIGH">HIGH (SMS to opted-in & Dashboard)</option>
                <option value="MODERATE">MODERATE (Dashboard Feed)</option>
                <option value="LOW">LOW (Informational)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-slate-600 font-medium mb-1">Advisory Message Content</label>
            <textarea
              rows={3}
              value={message}
              onChange={(e) => {
                setMessage(e.target.value);
                setPreviewData(null);
              }}
              required
              className="w-full p-3 border border-slate-300 rounded-xl text-slate-800 font-sans focus:ring-2 focus:ring-emerald-500 text-xs"
            />
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-slate-100">
            <span className="text-[11px] text-slate-500">
              Step 1: Preview recipient audience and verify consent prior to execution.
            </span>
            <button
              type="submit"
              disabled={isPreviewing}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-white hover:bg-slate-900 flex items-center space-x-1.5 disabled:opacity-50 transition-colors"
            >
              <Eye className={`w-3.5 h-3.5 ${isPreviewing ? 'animate-spin' : ''}`} />
              <span>{isPreviewing ? 'Previewing...' : 'Preview Audience Breakdown'}</span>
            </button>
          </div>
        </form>

        {/* Audience Preview & Confirmation Card */}
        {previewData && (
          <div className="mt-4 p-4 bg-amber-50/70 border border-amber-300 rounded-xl space-y-3 animate-fade-in text-xs">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-bold text-amber-950 flex items-center space-x-1.5">
                  <ShieldAlert className="w-4 h-4 text-amber-700" />
                  <span>Broadcast Dry-Run Safety Preview</span>
                </h3>
                <p className="text-[11px] text-amber-800 mt-0.5">
                  Review audience counts below before authorizing real dispatch.
                </p>
              </div>
              <span className="text-[10px] font-bold bg-amber-200 text-amber-900 px-2 py-0.5 rounded-full">
                CONFIRMATION REQUIRED
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 p-3 bg-white rounded-lg border border-amber-200">
              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Total Targeted</p>
                <p className="text-lg font-extrabold text-slate-900">{previewData.target_farmers_count}</p>
                <p className="text-[10px] text-slate-600">Farmers in region</p>
              </div>
              <div>
                <p className="text-[10px] text-emerald-600 uppercase font-semibold">SMS Consented</p>
                <p className="text-lg font-extrabold text-emerald-700">{previewData.sms_consented_count}</p>
                <p className="text-[10px] text-slate-600">Will receive AWS SMS</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">In-App Only (Opted Out)</p>
                <p className="text-lg font-extrabold text-slate-700">{previewData.in_app_only_count}</p>
                <p className="text-[10px] text-slate-600">Dashboard only</p>
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <button
                type="button"
                onClick={() => setPreviewData(null)}
                className="text-xs text-slate-500 hover:text-slate-800 underline"
              >
                Cancel & Edit
              </button>
              <button
                type="button"
                onClick={handleConfirmBroadcast}
                disabled={isBroadcasting}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-md shadow-emerald-600/20 flex items-center space-x-2 disabled:opacity-50 transition-colors"
              >
                <Check className={`w-3.5 h-3.5 ${isBroadcasting ? 'animate-spin' : ''}`} />
                <span>{isBroadcasting ? 'Authorizing Dispatch...' : 'Confirm & Dispatch Advisory'}</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Broadcast History & Dispatch Audit Log */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-emerald-600" />
            <span>Notification & SMS Dispatch Audit Log</span>
          </h3>
          <span className="text-[10px] text-slate-500">
            Total Logged: {notifications.length}
          </span>
        </div>

        {isLoading && notifications.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs flex items-center justify-center space-x-2">
            <RefreshCw className="w-4 h-4 animate-spin text-emerald-600" />
            <span>Loading dispatch logs...</span>
          </div>
        ) : notifications.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No notifications dispatched yet. Use the form above to dispatch an emergency broadcast advisory.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 text-[10px] uppercase font-semibold">
                <tr>
                  <th className="py-2.5 px-4">Subject</th>
                  <th className="py-2.5 px-4">Severity</th>
                  <th className="py-2.5 px-4">Channel</th>
                  <th className="py-2.5 px-4">Attempts</th>
                  <th className="py-2.5 px-4">Masked Recipient</th>
                  <th className="py-2.5 px-4">Dispatched At</th>
                  <th className="py-2.5 px-4 text-right">AWS SNS Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {notifications.map((n) => {
                  const isCritical = n.severity === 'CRITICAL';
                  const isHigh = n.severity === 'HIGH';

                  return (
                    <tr key={n.id} className="hover:bg-slate-50/60">
                      <td className="py-3 px-4 font-medium text-slate-900">
                        <div>
                          <span>{n.title}</span>
                          <p className="text-[10px] text-slate-500 line-clamp-1">{n.message}</p>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.5 rounded-md ${
                            isCritical
                              ? 'bg-rose-100 text-rose-800'
                              : isHigh
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}
                        >
                          {n.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-600 capitalize">
                        {n.channel}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600">
                        {n.delivery_attempts} / 3
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600">
                        {n.masked_phone_number || 'In-App Only'}
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {formatTimestamp(n.created_at)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {n.status === 'accepted' ? (
                          <span
                            className="font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full text-[10px]"
                            title={n.sns_message_id ? `SNS Message ID: ${n.sns_message_id}` : 'In-App Accepted'}
                          >
                            Accepted {n.sns_message_id ? '✓' : ''}
                          </span>
                        ) : n.status === 'failed' ? (
                          <span
                            className="font-medium text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-full text-[10px]"
                            title={n.error_message || 'Dispatch Failed'}
                          >
                            Failed
                          </span>
                        ) : n.status === 'sending' ? (
                          <span className="font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full text-[10px]">
                            Sending...
                          </span>
                        ) : (
                          <span className="font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full text-[10px] capitalize">
                            {n.status}
                          </span>
                        )}
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
