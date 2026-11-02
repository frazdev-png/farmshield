import React from 'react';
import {
  ShieldCheck,
  CloudLightning,
  Bot,
  Layers,
  ArrowRight,
  Database,
  Cpu,
} from 'lucide-react';
import type { NavigationTab } from '../../types';
import { useAuth } from '../../context/useAuth';

interface LandingPageProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
  const { user } = useAuth();

  return (
    <div className="space-y-16 pb-20">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-16 bg-gradient-to-b from-emerald-50/70 via-white to-slate-50 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <div className="inline-flex items-center space-x-2 bg-emerald-100/80 border border-emerald-200 px-3 py-1 rounded-full text-xs font-semibold text-emerald-800 mb-6">
            <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse"></span>
            <span>Real Open-Meteo Meteorology • Deterministic Risk Engine</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight max-w-4xl mx-auto">
            Intelligent Agro-Defense & <span className="text-emerald-600">Crop Resilience</span> Powered by AI
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
            FarmShield AI provides automated micro-climate alerts, predictive pest and disease detection, and generative agronomy advisory to protect crop yields before risks turn into losses.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            {user?.role === 'admin' ? (
              <button
                onClick={() => onNavigate('admin-overview')}
                className="w-full sm:w-auto px-6 py-3.5 rounded-xl font-semibold bg-purple-700 text-white hover:bg-purple-800 shadow-md shadow-purple-600/20 transition-all flex items-center justify-center space-x-2 group"
              >
                <span>Enter Admin Console</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            ) : user?.role === 'farmer' ? (
              <button
                onClick={() => onNavigate('farmer-overview')}
                className="w-full sm:w-auto px-6 py-3.5 rounded-xl font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-md shadow-emerald-600/20 transition-all flex items-center justify-center space-x-2 group"
              >
                <span>Enter Farmer Dashboard</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            ) : (
              <>
                <button
                  onClick={() => onNavigate('login')}
                  className="w-full sm:w-auto px-6 py-3.5 rounded-xl font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-md shadow-emerald-600/20 transition-all flex items-center justify-center space-x-2 group"
                >
                  <span>Sign In to Dashboard</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  onClick={() => onNavigate('register')}
                  className="w-full sm:w-auto px-6 py-3.5 rounded-xl font-semibold bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 transition-all"
                >
                  Register Farm Account
                </button>
              </>
            )}
          </div>

          {/* Platform Pillars */}
          <div className="mt-14 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
            <div className="bg-white/80 backdrop-blur-xs p-4 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">LIVE API</span>
              <p className="text-xl font-extrabold text-emerald-700 mt-1">Open-Meteo</p>
              <p className="text-xs text-slate-600 mt-1 font-medium">Real Farm Coordinates</p>
            </div>
            <div className="bg-white/80 backdrop-blur-xs p-4 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold text-blue-700 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded">ALGORITHMIC</span>
              <p className="text-xl font-extrabold text-slate-900 mt-1">5 Risk Rules</p>
              <p className="text-xs text-slate-600 mt-1 font-medium">Deterministic Engine</p>
            </div>
            <div className="bg-white/80 backdrop-blur-xs p-4 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold text-purple-700 bg-purple-50 border border-purple-200 px-1.5 py-0.5 rounded">AI ADVISOR</span>
              <p className="text-xl font-extrabold text-purple-700 mt-1">Strands Agents</p>
              <p className="text-xs text-slate-600 mt-1 font-medium">Bedrock Model Provider</p>
            </div>
            <div className="bg-white/80 backdrop-blur-xs p-4 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold text-slate-700 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded">DATABASE</span>
              <p className="text-xl font-extrabold text-slate-900 mt-1">PostgreSQL</p>
              <p className="text-xs text-slate-600 mt-1 font-medium">Strict Tenant Isolation</p>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-xs uppercase font-bold tracking-widest text-emerald-700">
            Engineered For Agriculture
          </h2>
          <p className="text-3xl font-extrabold text-slate-900 mt-2">
            Proactive Field Intelligence At Every Growth Stage
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs hover:border-emerald-300 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
              <CloudLightning className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Predictive Micro-Climate</h3>
            <p className="text-slate-600 text-sm mt-2 leading-relaxed">
              Localized farm-tier weather intelligence, frost triggers, heat stress indexes, and precipitation forecasts calibrated for your exact acreage.
            </p>
            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center text-xs font-semibold text-emerald-700">
              <span>View Weather Module</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs hover:border-emerald-300 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-4">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Automated Risk Detection</h3>
            <p className="text-slate-600 text-sm mt-2 leading-relaxed">
              Continuous anomaly scanning for armyworm infestations, fungal spores, drought stress, and root saturation with actionable treatment regimens.
            </p>
            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center text-xs font-semibold text-emerald-700">
              <span>View Risk Engine</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs hover:border-emerald-300 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-4">
              <Bot className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">GenAI Agronomist Bot</h3>
            <p className="text-slate-600 text-sm mt-2 leading-relaxed">
              Natural language consultation for fertilizer dosing, pesticide selection, crop rotation advice, and compliance reporting in plain farmer language.
            </p>
            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center text-xs font-semibold text-emerald-700">
              <span>Test AI Assistant</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>
        </div>
      </section>

      {/* Tech Stack & Architectural Readiness */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-950 rounded-3xl p-8 sm:p-12 text-white">
          <div className="max-w-3xl">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 bg-emerald-950/80 px-2.5 py-1 rounded-md border border-emerald-800">
              Robust Engineering Foundation
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold mt-4">
              Enterprise Technology Stack & AWS Cloud Readiness
            </h2>
            <p className="mt-3 text-slate-300 text-sm leading-relaxed">
              Designed from ground up with clear service boundaries, containerization, typed schemas, connection pooling, and multi-AZ database resilience.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
            <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
              <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-sm">
                <Cpu className="w-4 h-4" />
                <span>FastAPI Backend</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">
                Asynchronous Python framework with Pydantic v2 settings validation and automated OpenAPI docs.
              </p>
            </div>

            <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
              <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-sm">
                <Database className="w-4 h-4" />
                <span>SQLAlchemy 2.x & Alembic</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">
                PostgreSQL support with connection pooling, declarative base mapping, and declarative migrations.
              </p>
            </div>

            <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
              <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-sm">
                <Layers className="w-4 h-4" />
                <span>React + Vite Frontend</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">
                TypeScript compilation with Tailwind CSS styling and Lucide icons for blazing-fast client rendering.
              </p>
            </div>

            <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
              <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-sm">
                <ShieldCheck className="w-4 h-4" />
                <span>AWS Ready</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">
                Standardized Dockerfile, health checks for ALB routing, environment-based configuration, and deployment guide.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
