const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type User = {
  id: number;
  name: string;
  email: string;
  platform_role?: string;
  organization_id?: number;
  role?: string;
  assigned_connection_id?: number | null;
};

export type RootUser = {
  id: number;
  name: string;
  email: string;
  platform_role: string;
  created_at: string | null;
};

export type Organization = {
  id: number;
  name: string;
  role: string;
  business_timezone: string;
  business_days: number[];
  business_start_time: string;
  business_end_time: string;
  business_day_hours: Record<string, BusinessDayHours>;
  holiday_country: string;
  created_at: string;
};

export type BusinessDayHours = {
  enabled: boolean;
  uses_default: boolean;
  start_time: string | null;
  end_time: string | null;
};

export type GoogleConnection = {
  id: number;
  assigned_user_id: number | null;
  assigned_user_email: string | null;
  assigned_user_name: string | null;
  display_name: string | null;
  purpose: string | null;
  email: string;
  google_user_id: string | null;
  scopes: string[];
  status: string;
  watch_expiration_at: string | null;
  watch_desired_until: string | null;
  whatsapp_number: string | null;
  whatsapp_status: string;
  whatsapp_contact_name: string | null;
  whatsapp_last_message_id: string | null;
  whatsapp_last_message_at: string | null;
  whatsapp_notifications_enabled: boolean;
  whatsapp_notify_new_email: boolean;
  whatsapp_notify_followup_overdue: boolean;
  whatsapp_notify_followup_warning: boolean;
  whatsapp_notify_followup_late: boolean;
  whatsapp_notify_followup_responded: boolean;
  followup_enabled: boolean;
  followup_response_time_minutes: number;
  followup_notify_whatsapp_on_overdue: boolean;
  followup_warn_before_minutes: number | null;
  followup_escalation_minutes: number | null;
  created_at: string;
  updated_at: string;
};

export type EmailMessage = {
  id: number;
  google_connection_id: number;
  connection_email: string | null;
  gmail_message_id: string;
  gmail_thread_id: string | null;
  subject: string | null;
  sender: string | null;
  recipients: string | null;
  received_at: string | null;
  snippet: string | null;
  has_attachments: boolean;
  matched_rule_id: number | null;
  matched_rule_name: string | null;
  status: string;
  created_at: string;
};

export type GmailSyncResponse = {
  google_connection_id: number;
  fetched: number;
  stored: number;
  attachments_stored: number;
  latest_history_id: string | null;
};

export type GmailWatchResponse = {
  google_connection_id: number;
  history_id: string | null;
  expiration: string | null;
  desired_until: string | null;
  active: boolean;
};

export type WhatsAppSetupResponse = {
  google_connection_id: number;
  assistant_number: string;
  phone_number: string;
  verification_token: string;
  message: string;
  whatsapp_url: string;
  status: string;
};

export type Attachment = {
  id: number;
  email_message_id: number | null;
  google_connection_id: number;
  gmail_attachment_id: string | null;
  filename: string;
  mime_type: string;
  size_bytes: number;
  storage_provider: string;
  storage_path: string;
  processing_status: string;
  created_at: string;
};

export type AutomationRule = {
  id: number;
  organization_id: number;
  google_connection_id: number | null;
  connection_ids: number[];
  whatsapp_enabled_connection_ids: number[];
  name: string;
  is_active: boolean;
  sender_contains: string | null;
  subject_contains: string | null;
  has_attachment: boolean | null;
  action_type: string;
  configuration: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type EmailFollowup = {
  id: number;
  organization_id: number;
  google_connection_id: number;
  connection_email: string | null;
  automation_rule_id: number | null;
  automation_rule_name: string | null;
  email_message_id: number | null;
  gmail_thread_id: string;
  initial_message_id: string;
  subject: string | null;
  sender: string | null;
  received_at: string | null;
  status: string;
  response_due_at: string | null;
  first_response_at: string | null;
  response_time_minutes: number | null;
  message_count: number;
  last_message_at: string | null;
  last_message_from: string | null;
  notified_overdue_at: string | null;
  escalated_at: string | null;
  tracking_source: string;
  tracking_started_at: string | null;
  warn_before_minutes: number | null;
  notify_whatsapp_on_overdue: boolean;
  escalation_minutes: number | null;
  warned_at: string | null;
  escalation_notified_at: string | null;
  closed_at: string | null;
  closure_reason: string | null;
  business_minutes_elapsed: number | null;
  business_due_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SystemEvent = {
  id: number;
  organization_id: number | null;
  google_connection_id: number | null;
  level: string;
  event_type: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

type LoginResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export const AUTH_EXPIRED_EVENT = "email-assistance:auth-expired";

function expireSession() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
  localStorage.removeItem("selected_organization_id");
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

async function apiFetch(path: string, options: RequestInit = {}) {
  const organizationId = localStorage.getItem("selected_organization_id");
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(organizationId ? { "X-Organization-Id": organizationId } : {}),
      ...options.headers,
    },
  });

  if (response.status === 401) {
    expireSession();
  }

  return response;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, options);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Error inesperado" }));
    throw new Error(error.detail ?? "Error inesperado");
  }

  return response.json() as Promise<T>;
}

export function login(email: string, password: string) {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function updateProfile(token: string, payload: { name?: string; email?: string; password?: string }) {
  return request<User>("/auth/me", {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function listRootUsers(token: string) {
  return request<RootUser[]>("/auth/root-users", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createRootUser(token: string, payload: { name: string; email: string; password: string }) {
  return request<RootUser>("/auth/root-users", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function listOrganizations(token: string) {
  return request<Organization[]>("/organizations", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createOrganization(token: string, name: string) {
  return request<Organization>("/organizations", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ name }),
  });
}

export function updateOrganization(token: string, id: number, name: string) {
  return request<Organization>(`/organizations/${id}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ name }),
  });
}

export function updateOrganizationBusinessHours(
  token: string,
  id: number,
  payload: {
    business_timezone: string;
    business_days: number[];
    business_start_time: string;
    business_end_time: string;
    business_day_hours: Record<string, BusinessDayHours>;
    holiday_country: string;
  },
) {
  return request<Organization>(`/organizations/${id}/business-hours`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function deleteOrganization(token: string, id: number) {
  return apiFetch(`/organizations/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  }).then((response) => {
    if (!response.ok) {
      throw new Error("No se pudo eliminar la organizacion");
    }
  });
}

export function listConnections(token: string) {
  return request<GoogleConnection[]>("/google-connections", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createConnection(token: string, email: string, displayName?: string, purpose?: string) {
  return request<GoogleConnection>("/google-connections", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      email,
      display_name: displayName || email,
      purpose,
      scopes: ["gmail.readonly"],
      refresh_token: "dev-refresh-token",
    }),
  });
}

export function createAccountAccess(
  token: string,
  payload: { display_name: string; purpose?: string; user_email: string; password: string },
) {
  return request<GoogleConnection>("/google-connections/access", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function updateConnection(
  token: string,
  id: number,
  payload: { display_name?: string; purpose?: string; user_email?: string; password?: string },
) {
  return request<GoogleConnection>(`/google-connections/${id}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function updateConnectionFollowup(
  token: string,
  id: number,
  payload: {
    enabled: boolean;
    response_time_minutes: number;
    notify_whatsapp_on_overdue: boolean;
    warn_before_minutes?: number | null;
    escalation_minutes?: number | null;
  },
) {
  return request<GoogleConnection>(`/google-connections/${id}/followup`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function startGoogleOAuth(token: string, payload: { display_name?: string; purpose?: string; connection_id?: number } = {}) {
  const params = new URLSearchParams();
  if (payload.display_name) params.set("display_name", payload.display_name);
  if (payload.purpose) params.set("purpose", payload.purpose);
  if (payload.connection_id) params.set("connection_id", String(payload.connection_id));
  const query = params.toString() ? `?${params.toString()}` : "";

  return request<{ authorization_url: string }>(`/google/oauth/start${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function syncConnection(token: string, id: number) {
  return request<GmailSyncResponse>(`/gmail/connections/${id}/sync`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function watchConnection(token: string, id: number, activeUntil: string) {
  return request<GmailWatchResponse>(`/gmail/connections/${id}/watch`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ active_until: activeUntil }),
  });
}

export function stopWatchConnection(token: string, id: number) {
  return request<GmailWatchResponse>(`/gmail/connections/${id}/watch`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function startWhatsAppSetup(token: string, id: number, phoneNumber: string) {
  return request<WhatsAppSetupResponse>(`/whatsapp/connections/${id}/setup`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ phone_number: phoneNumber }),
  });
}

export function updateWhatsAppPreferences(
  token: string,
  id: number,
  payload: {
    notifications_enabled: boolean;
    notify_new_email: boolean;
    notify_followup_overdue: boolean;
    notify_followup_warning: boolean;
    notify_followup_late: boolean;
    notify_followup_responded: boolean;
  },
) {
  return request<{ status: string; google_connection_id: number }>(`/whatsapp/connections/${id}/preferences`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function listMessages(token: string, connectionId?: number | null) {
  const query = connectionId ? `?connection_id=${connectionId}` : "";
  return request<EmailMessage[]>(`/gmail/messages${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function listAttachments(token: string) {
  return request<Attachment[]>("/attachments", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function listRules(token: string) {
  return request<AutomationRule[]>("/automation/rules", {
    headers: { Authorization: `Bearer ${token}` },
  }).then((rules) =>
    rules.map((rule) => ({
      ...rule,
      connection_ids: Array.isArray(rule.connection_ids) ? rule.connection_ids : [],
      whatsapp_enabled_connection_ids: Array.isArray(rule.whatsapp_enabled_connection_ids)
        ? rule.whatsapp_enabled_connection_ids
        : [],
      configuration: rule.configuration || {},
    })),
  );
}

export function createRule(token: string, payload: { name: string; connection_ids: number[]; sender_contains?: string | null; subject_contains?: string | null; has_attachment?: boolean | null; action_type?: string; configuration?: Record<string, unknown> }) {
  return request<AutomationRule>("/automation/rules", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function updateRule(token: string, id: number, payload: { name: string; connection_ids: number[]; sender_contains?: string | null; subject_contains?: string | null; has_attachment?: boolean | null; action_type?: string; configuration?: Record<string, unknown>; is_active?: boolean }) {
  return request<AutomationRule>(`/automation/rules/${id}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function updateRuleWhatsAppNotifications(token: string, id: number, connectionIds: number[]) {
  return request<AutomationRule>(`/automation/rules/${id}/whatsapp-notifications`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ connection_ids: connectionIds }),
  });
}

export function updateRuleFollowup(
  token: string,
  id: number,
  payload: {
    enabled: boolean;
    response_time_minutes: number;
    notify_whatsapp_on_overdue: boolean;
    warn_before_minutes?: number | null;
    escalation_minutes?: number | null;
  },
) {
  return request<AutomationRule>(`/automation/rules/${id}/followup`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function listFollowups(token: string, connectionId?: number | null, status?: string) {
  const params = new URLSearchParams();
  if (connectionId) params.set("connection_id", String(connectionId));
  if (status && status !== "all") params.set("status", status);
  const query = params.toString() ? `?${params.toString()}` : "";
  return request<EmailFollowup[]>(`/followups${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createManualFollowup(
  token: string,
  payload: {
    email_message_id: number;
    response_time_minutes: number;
    notify_whatsapp_on_overdue: boolean;
    warn_before_minutes?: number | null;
    escalation_minutes?: number | null;
  },
) {
  return request<EmailFollowup>("/followups", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function getFollowupSummary(token: string) {
  return request<{ totals: Record<string, number>; avg_response_minutes: number | null }>("/followups/summary", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function evaluateFollowups(token: string, connectionId?: number | null) {
  const query = connectionId ? `?connection_id=${connectionId}` : "";
  return request<{ status: string; evaluated: number; responded: number; overdue: number; errors: number }>(
    `/followups/evaluate${query}`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    },
  );
}

export function draftRuleFromText(token: string, payload: { text: string; connection_ids: number[] }) {
  return request<{
    name: string;
    connection_ids: number[];
    sender_contains: string | null;
    subject_contains: string | null;
    has_attachment: boolean | null;
    action_type: string;
    configuration: Record<string, unknown>;
  }>("/automation/rules/draft-from-text", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function deleteRule(token: string, id: number) {
  return apiFetch(`/automation/rules/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  }).then((response) => {
    if (!response.ok) {
      throw new Error("No se pudo eliminar la regla");
    }
  });
}

export type EventFilters = {
  connection_id?: number;
  event_type?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
};

export function listEvents(token: string, filters: EventFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return request<SystemEvent[]>(`/automation/events${query ? `?${query}` : ""}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function deleteConnection(token: string, id: number) {
  return apiFetch(`/google-connections/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  }).then((response) => {
    if (!response.ok) {
      throw new Error("No se pudo desconectar la cuenta");
    }
  });
}
