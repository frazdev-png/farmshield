export type NavigationTab =
  | 'landing'
  | 'login'
  | 'register'
  | 'farmer-overview'
  | 'farmer-weather'
  | 'farmer-crops'
  | 'farmer-risks'
  | 'farmer-notifications'
  | 'farmer-ai'
  | 'farmer-profile'
  | 'admin-overview'
  | 'admin-farmers'
  | 'admin-risks'
  | 'admin-notifications'
  | 'admin-agent';

export interface User {
  id: string;
  full_name: string;
  email: string;
  phone_number: string;
  role: 'farmer' | 'admin';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  phone_number: string;
  password: string;
  farm_name?: string;
  district?: string;
  village?: string;
  region?: string;
  latitude?: number;
  longitude?: number;
  acreage?: string;
  total_area?: number;
  area_unit?: string;
  primary_crops?: string;
  soil_type?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

// Farm & Crop Types (Step 3 Real Models)
export interface FarmCrop {
  id: string;
  farm_id: string;
  crop_name: string;
  variety?: string | null;
  cultivated_area: number;
  area_unit: 'acres' | 'hectares';
  sowing_date?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Farm {
  id: string;
  farmer_id: string;
  farm_name: string;
  district: string;
  village: string;
  address?: string | null;
  latitude: number;
  longitude: number;
  total_area: number;
  area_unit: 'acres' | 'hectares';
  soil_type?: string | null;
  crops_count: number;
  total_cultivated_area: number;
  crops?: FarmCrop[];
  created_at: string;
  updated_at: string;
}

export interface FarmCreatePayload {
  farm_name: string;
  district: string;
  village: string;
  address?: string;
  latitude: number;
  longitude: number;
  total_area: number;
  area_unit: 'acres' | 'hectares';
  soil_type?: string;
}

export interface FarmUpdatePayload {
  farm_name?: string;
  district?: string;
  village?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  total_area?: number;
  area_unit?: 'acres' | 'hectares';
  soil_type?: string;
}

export interface FarmCropCreatePayload {
  crop_name: string;
  variety?: string;
  cultivated_area: number;
  area_unit: 'acres' | 'hectares';
  sowing_date?: string;
}

export interface FarmCropUpdatePayload {
  crop_name?: string;
  variety?: string;
  cultivated_area?: number;
  area_unit?: 'acres' | 'hectares';
  sowing_date?: string;
}

export interface BackendHealthResponse {
  status: 'healthy' | 'degraded' | 'unreachable';
  service: string;
  version: string;
  environment: string;
  database?: string;
  timestamp: string;
}

export interface BackendHealthState {
  data: BackendHealthResponse | null;
  loading: boolean;
  error: string | null;
  lastChecked: Date | null;
  latencyMs: number | null;
}

export interface RiskAlert {
  id: string;
  title: string;
  category: 'Pest' | 'Weather' | 'Disease' | 'Irrigation';
  severity: 'Critical' | 'Warning' | 'Advisory' | 'Info';
  farmArea: string;
  timestamp: string;
  recommendation: string;
  isDemo: boolean;
}

export interface WeatherDay {
  day: string;
  date: string;
  condition: string;
  tempMax: number;
  tempMin: number;
  precipitation: number;
  humidity: number;
  windSpeed: number;
  icon: string;
}

// Weather & Risk Types (Step 4 Real Models)
export interface DailyForecastItem {
  date: string;
  weather_code?: number | null;
  weather_condition: string;
  temperature_max?: number | null;
  temperature_min?: number | null;
  precipitation_sum?: number | null;
  wind_speed_max?: number | null;
}

export interface WeatherObservation {
  id: string;
  farm_id: string;
  provider: string;
  observed_at: string;
  fetched_at: string;
  temperature?: number | null;
  relative_humidity?: number | null;
  precipitation?: number | null;
  wind_speed?: number | null;
  weather_condition?: string | null;
  forecast_data?: DailyForecastItem[] | null;
  created_at: string;
}

export interface WeatherForecastResponse {
  farm_id: string;
  provider: string;
  observed_at: string;
  fetched_at: string;
  forecast: DailyForecastItem[];
}

export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';

export interface RiskAssessment {
  id: string;
  farm_id: string;
  weather_observation_id?: string | null;
  risk_category: string;
  risk_level: RiskLevel;
  risk_score: number;
  evidence: Record<string, any>;
  explanation: string;
  recommended_precaution: string;
  assessed_at: string;
  created_at: string;
}

export interface RiskSummary {
  farm_id: string;
  overall_risk_level: RiskLevel;
  highest_risk_score: number;
  assessed_at: string;
  assessments: RiskAssessment[];
}

// Strands AI Assistant Types (Step 5 Real Models)
export interface AssistantChatRequest {
  farm_id: string;
  message: string;
  conversation_id?: string;
}

export interface AssistantChatResponse {
  conversation_id: string;
  assistant_message: string;
  referenced_weather_timestamp?: string | null;
  referenced_risk_assessments?: Array<{ category: string; level: string; score: number }> | null;
  response_timestamp: string;
}

export interface ConversationMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  metadata_json?: {
    weather_timestamp?: string | null;
    risk_assessments?: Array<{ category: string; level: string; score: number }>;
  } | null;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  farmer_id: string;
  farm_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
}

export interface ConversationSummary {
  id: string;
  farmer_id: string;
  farm_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages_count: number;
}

// Notification & AWS SNS Types (Step 6 Real Models)
export interface FarmerPreference {
  user_id: string;
  sms_consent: boolean;
  sms_consent_at?: string | null;
  language_preference: string;
  updated_at: string;
}

export interface NotificationItem {
  id: string;
  farmer_id: string;
  farm_id?: string | null;
  risk_assessment_id?: string | null;
  notification_type: string;
  title: string;
  message: string;
  severity: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  channel: 'in_app' | 'sms' | 'both';
  is_read: boolean;
  status: 'pending' | 'sending' | 'accepted' | 'delivered' | 'failed';
  sns_message_id?: string | null;
  masked_phone_number?: string | null;
  delivery_attempts: number;
  last_attempt_at?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
  unread_count: number;
}

export interface AdminBroadcastRequest {
  title: string;
  message: string;
  severity: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  district?: string;
  confirmed?: boolean;
}

export interface AdminBroadcastPreviewResponse {
  target_farmers_count: number;
  sms_consented_count: number;
  in_app_only_count: number;
  district?: string | null;
  severity: string;
  title: string;
  message: string;
}

export interface AdminBroadcastResponse {
  target_farmers_count: number;
  notifications_queued: number;
  sms_accepted_count: number;
  sms_skipped_or_failed_count: number;
  message: string;
}

// Real Admin Operations Types (Step 6.2)
export interface AdminOverviewStats {
  total_farmers: number;
  total_farms: number;
  total_monitored_acres: number;
  active_threats_count: number;
  total_ai_queries_count: number;
  total_notifications_count: number;
  system_status: string;
}

export interface AdminFarmerItem {
  id: string;
  full_name: string;
  email: string;
  masked_phone: string;
  created_at: string;
  is_active: boolean;
  farms_count: number;
  total_acreage: number;
  crops_summary: string;
  highest_risk_level?: string | null;
}

export interface FarmerActionResponse {
  message: string;
  farmer_id: string;
  is_active?: boolean;
}


export interface AdminRiskMonitoringItem {
  farm_id: string;
  farm_name: string;
  district: string;
  highest_risk_level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  risk_score: number;
  risk_category: string;
  assessed_at: string;
}

export interface AdminAgentActivityItem {
  session_id: string;
  farmer_name: string;
  farm_name: string;
  title: string;
  messages_count: number;
  last_activity_at: string;
  last_query_snippet?: string | null;
}
