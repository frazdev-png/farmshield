import React, { useEffect, useState, useRef } from 'react';
import {
  Bot,
  User,
  Send,
  Sparkles,
  Building,
  RotateCcw,
  CloudSun,
  ShieldAlert,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import type { Farm, ConversationMessage } from '../../types';
import { api } from '../../services/api';
import { useAuth } from '../../context/useAuth';

export const AIAssistantChat: React.FC = () => {
  const { user } = useAuth();
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoadingFarms, setIsLoadingFarms] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isServiceUnavailable, setIsServiceUnavailable] = useState(false);
  const [lastUserMessage, setLastUserMessage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const selectedFarm = farms.find((f) => f.id === selectedFarmId) || farms[0] || null;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // 1. Load farms
  const loadFarms = async () => {
    setIsLoadingFarms(true);
    try {
      const data = await api.farms.list();
      setFarms(data);
      if (data.length > 0) {
        setSelectedFarmId(data[0].id);
      }
    } catch {
      setErrorMessage('Failed to load farms.');
    } finally {
      setIsLoadingFarms(false);
    }
  };

  // 2. Load conversations for the selected farm
  const loadExistingConversation = async (farmId: string) => {
    try {
      const convs = await api.assistant.listConversations(farmId);
      if (convs.length > 0) {
        const activeConv = await api.assistant.getConversation(convs[0].id);
        setConversationId(activeConv.id);
        setMessages(activeConv.messages);
      } else {
        setConversationId(null);
        setMessages([
          {
            id: 'welcome',
            sender: 'assistant',
            content: `Hello ${user?.full_name || 'Farmer'}! I am your FarmShield AI Agronomy Advisor powered by Strands Agents. I have live access to your farm's weather telemetry, crop records, and deterministic risk evaluations. How can I assist your crop operations today?`,
            created_at: new Date().toISOString(),
          },
        ]);
      }
    } catch {
      // Keep welcome message
    }
  };

  useEffect(() => {
    loadFarms();
  }, []);

  useEffect(() => {
    if (selectedFarmId) {
      loadExistingConversation(selectedFarmId);
    }
  }, [selectedFarmId]);

  const handleStartNewChat = () => {
    setConversationId(null);
    setErrorMessage(null);
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        sender: 'assistant',
        content: `Started a fresh advisory session for ${selectedFarm?.farm_name || 'your farm'}. Ask any question regarding weather risks, crop conditions, or physical field preparations.`,
        created_at: new Date().toISOString(),
      },
    ]);
  };

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || !selectedFarmId) return;

    setLastUserMessage(text);
    setInput('');
    setErrorMessage(null);
    setIsServiceUnavailable(false);

    const tempUserMsg: ConversationMessage = {
      id: `client-temp-${Date.now()}`,
      sender: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsTyping(true);

    try {
      const response = await api.assistant.chat({
        farm_id: selectedFarmId,
        message: text,
        conversation_id: conversationId || undefined,
      });

      setConversationId(response.conversation_id);

      const aiMsg: ConversationMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        content: response.assistant_message,
        metadata_json: {
          weather_timestamp: response.referenced_weather_timestamp,
          risk_assessments: response.referenced_risk_assessments || [],
        },
        created_at: response.response_timestamp || new Date().toISOString(),
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      const errMsg = err.message || 'Failed to communicate with AI Advisor.';
      setErrorMessage(errMsg);
      if (err.status === 503 || errMsg.includes('Amazon Bedrock') || errMsg.includes('credentials')) {
        setIsServiceUnavailable(true);
      }
    } finally {
      setIsTyping(false);
    }
  };

  const handleRetry = () => {
    if (lastUserMessage) {
      handleSend(lastUserMessage);
    }
  };

  const quickPrompts = [
    'What is the current weather on my farm?',
    'Summarize my latest deterministic risk assessments',
    'What precautions should I take for high winds?',
    'Fasal ke tahafuz ke liye kya zaroori ehtiyat karein?',
  ];

  return (
    <div className="space-y-6">
      {/* Top Header & Farm Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              AI Agronomy Advisor
            </h1>
            <span className="text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-300 px-2.5 py-0.5 rounded-full flex items-center space-x-1">
              <Sparkles className="w-3 h-3 text-purple-600" />
              <span>STRANDS AGENTS (BEDROCK)</span>
            </span>
          </div>
          {selectedFarm ? (
            <p className="text-xs text-slate-600 mt-1">
              Consulting for: <strong className="text-slate-800">{selectedFarm.farm_name}</strong> • {selectedFarm.village}, {selectedFarm.district} • ({selectedFarm.latitude.toFixed(2)}°, {selectedFarm.longitude.toFixed(2)}°)
            </p>
          ) : (
            <p className="text-xs text-slate-500 mt-1">No farm selected</p>
          )}
        </div>

        {/* Farm Switcher & New Chat Button */}
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
                    {f.farm_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={handleStartNewChat}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200 shadow-xs flex items-center space-x-1.5 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>New Thread</span>
          </button>
        </div>
      </div>

      {/* Bedrock Service Unavailable Notice */}
      {isServiceUnavailable && (
        <div className="bg-amber-50 border border-amber-300 rounded-2xl p-4 text-xs text-amber-900 space-y-2">
          <div className="flex items-center space-x-2 font-bold text-amber-950">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>Amazon Bedrock Model Access Required</span>
          </div>
          <p className="leading-relaxed">
            The Strands AI Advisor is implemented and connected to backend tools, but Amazon Bedrock is not configured or AWS credentials are not found in the environment.
          </p>
          <div className="bg-amber-100/70 p-2.5 rounded-xl font-mono text-[11px] text-amber-900">
            Set environment variables: STRANDS_MODEL_ID and AWS_REGION (e.g. us-east-1) with valid AWS credentials.
          </div>
          <div className="pt-1">
            <button
              onClick={handleRetry}
              className="px-3 py-1 rounded-lg bg-amber-600 text-white font-semibold hover:bg-amber-700 transition-colors"
            >
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && !isServiceUnavailable && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs text-rose-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={handleRetry}
            className="text-xs font-bold text-rose-700 underline hover:text-rose-900"
          >
            Retry
          </button>
        </div>
      )}

      {/* No Farm Warning */}
      {!isLoadingFarms && farms.length === 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-center space-y-2">
          <Building className="w-10 h-10 text-amber-600 mx-auto" />
          <h3 className="font-bold text-slate-800 text-sm">No Registered Farms Found</h3>
          <p className="text-xs text-slate-600 max-w-md mx-auto">
            The AI Advisor requires an authorized farm context to look up weather and risk metrics. Please register a farm in the Profile / My Farm page.
          </p>
        </div>
      )}

      {/* Chat Container */}
      {selectedFarm && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col h-[560px]">
          {/* Messages Scroll Area */}
          <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4">
            {messages.map((m) => {
              const isUser = m.sender === 'user';
              const weatherRef = m.metadata_json?.weather_timestamp;
              const risksRef = m.metadata_json?.risk_assessments || [];

              return (
                <div
                  key={m.id}
                  className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}
                >
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                      isUser
                        ? 'bg-emerald-600 text-white shadow-xs'
                        : 'bg-purple-600 text-white shadow-xs'
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div
                    className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                      isUser
                        ? 'bg-emerald-600 text-white rounded-tr-none'
                        : 'bg-slate-50 text-slate-800 rounded-tl-none border border-slate-200/80 shadow-xs'
                    }`}
                  >
                    <div className="flex items-center justify-between space-x-2 mb-1.5">
                      <span className="font-bold text-[10px] opacity-80">
                        {isUser ? user?.full_name || 'Farmer' : 'FarmShield AI Advisor'}
                      </span>
                      <span className="text-[9px] opacity-60">
                        {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    <div className="whitespace-pre-wrap">{m.content}</div>

                    {/* Grounding Reference Badges */}
                    {!isUser && (weatherRef || risksRef.length > 0) && (
                      <div className="mt-3 pt-2 border-t border-slate-200/60 flex flex-wrap gap-1.5">
                        {weatherRef && (
                          <span className="inline-flex items-center space-x-1 text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-md">
                            <CloudSun className="w-3 h-3 text-blue-500" />
                            <span>Weather verified</span>
                          </span>
                        )}
                        {risksRef.map((r, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center space-x-1 text-[10px] font-medium bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded-md"
                          >
                            <ShieldAlert className="w-3 h-3 text-amber-600" />
                            <span>
                              {r.category}: {r.level}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {isTyping && (
              <div className="flex items-center space-x-2 text-xs text-purple-900 bg-purple-50 border border-purple-200 p-3 rounded-2xl w-fit shadow-xs animate-pulse">
                <Loader2 className="w-4 h-4 text-purple-600 animate-spin" />
                <span>Consulting FarmShield Strands Agronomy Advisor...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompt Chips */}
          <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/60 flex items-center space-x-2 overflow-x-auto text-xs">
            <Sparkles className="w-3.5 h-3.5 text-purple-600 shrink-0" />
            <span className="text-[11px] text-slate-500 shrink-0 font-medium">Quick Questions:</span>
            {quickPrompts.map((p, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(p)}
                disabled={isTyping}
                className="shrink-0 text-[11px] bg-white border border-slate-200 text-slate-700 hover:border-purple-300 hover:text-purple-700 px-2.5 py-1 rounded-full transition-colors disabled:opacity-50"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Message Input Form */}
          <div className="p-3 border-t border-slate-200 bg-white rounded-b-2xl">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center space-x-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about weather forecasts, blight risks, lodging precautions, or Urdu/English advice..."
                disabled={isTyping || !selectedFarmId}
                className="flex-1 border border-slate-300 rounded-xl px-4 py-2.5 text-xs text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500 disabled:bg-slate-50"
              />
              <button
                type="submit"
                disabled={!input.trim() || isTyping || !selectedFarmId}
                className="p-2.5 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors shadow-xs"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
