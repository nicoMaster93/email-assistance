from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserProfileUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None


class RootUserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    platform_role: str
    is_active: bool = True
    created_at: str | None = None


class RootUserStatusUpdate(BaseModel):
    is_active: bool


class OrganizationCreate(BaseModel):
    name: str


class OrganizationUpdate(BaseModel):
    name: str


class OrganizationBusinessHoursUpdate(BaseModel):
    business_timezone: str = "America/Bogota"
    business_days: list[int] = [1, 2, 3, 4, 5]
    business_start_time: str = "08:00"
    business_end_time: str = "18:00"
    business_day_hours: dict = {}
    holiday_country: str = "CO"


class OrganizationResponse(BaseModel):
    id: int
    name: str
    role: str
    business_timezone: str = "America/Bogota"
    business_days: list[int] = [1, 2, 3, 4, 5]
    business_start_time: str = "08:00"
    business_end_time: str = "18:00"
    business_day_hours: dict = {}
    holiday_country: str = "CO"
    created_at: str


class LinkGoogleAccountRequest(BaseModel):
    email: EmailStr
    display_name: str | None = None
    purpose: str | None = None
    google_user_id: str | None = None
    scopes: list[str] = ["gmail.readonly"]
    refresh_token: str | None = None


class CreateAccountAccessRequest(BaseModel):
    display_name: str
    purpose: str | None = None
    user_email: EmailStr
    password: str


class UpdateGoogleConnectionRequest(BaseModel):
    display_name: str | None = None
    purpose: str | None = None
    user_email: EmailStr | None = None
    password: str | None = None


class AccountFollowupConfigUpdate(BaseModel):
    enabled: bool = False
    response_time_minutes: int = 120
    notify_whatsapp_on_overdue: bool = False
    warn_before_minutes: int | None = None
    escalation_minutes: int | None = None


class WhatsAppSetupRequest(BaseModel):
    phone_number: str


class WhatsAppNotificationPreferencesUpdate(BaseModel):
    notifications_enabled: bool = True
    notify_new_email: bool = True
    notify_followup_overdue: bool = True
    notify_followup_warning: bool = True
    notify_followup_late: bool = True
    notify_followup_responded: bool = True


class WhatsAppSetupResponse(BaseModel):
    google_connection_id: int
    assistant_number: str
    phone_number: str
    verification_token: str
    message: str
    whatsapp_url: str
    status: str


class WhatsAppWebhookRequest(BaseModel):
    from_number: str | None = None
    message: str | None = None
    payload: dict = {}


class GoogleConnectionResponse(BaseModel):
    id: int
    assigned_user_id: int | None = None
    assigned_user_email: EmailStr | None = None
    assigned_user_name: str | None = None
    display_name: str | None = None
    purpose: str | None = None
    email: EmailStr
    google_user_id: str | None
    scopes: list[str]
    status: str
    watch_expiration_at: str | None = None
    watch_desired_until: str | None = None
    whatsapp_number: str | None = None
    whatsapp_status: str = "not_configured"
    whatsapp_contact_name: str | None = None
    whatsapp_last_message_id: str | None = None
    whatsapp_last_message_at: str | None = None
    whatsapp_notifications_enabled: bool = True
    whatsapp_notify_new_email: bool = True
    whatsapp_notify_followup_overdue: bool = True
    whatsapp_notify_followup_warning: bool = True
    whatsapp_notify_followup_late: bool = True
    whatsapp_notify_followup_responded: bool = True
    followup_enabled: bool = False
    followup_response_time_minutes: int = 120
    followup_notify_whatsapp_on_overdue: bool = False
    followup_warn_before_minutes: int | None = None
    followup_escalation_minutes: int | None = None
    created_at: str
    updated_at: str


class AttachmentResponse(BaseModel):
    id: int
    email_message_id: int | None = None
    google_connection_id: int
    gmail_attachment_id: str | None = None
    filename: str
    mime_type: str
    size_bytes: int
    storage_provider: str
    storage_path: str
    processing_status: str
    created_at: str


class GoogleOAuthStartResponse(BaseModel):
    authorization_url: str


class EmailMessageResponse(BaseModel):
    id: int
    google_connection_id: int
    connection_email: str | None = None
    gmail_message_id: str
    gmail_thread_id: str | None
    subject: str | None
    sender: str | None
    recipients: str | None
    received_at: str | None
    snippet: str | None
    has_attachments: bool
    matched_rule_id: int | None = None
    matched_rule_name: str | None = None
    status: str
    created_at: str


class GmailSyncResponse(BaseModel):
    google_connection_id: int
    fetched: int
    stored: int
    attachments_stored: int
    latest_history_id: str | None


class GmailWatchResponse(BaseModel):
    google_connection_id: int
    history_id: str | None
    expiration: str | None
    desired_until: str | None = None
    active: bool = False


class GmailWatchRequest(BaseModel):
    active_until: str


class PubSubPushRequest(BaseModel):
    message: dict
    subscription: str | None = None


class AutomationRuleCreate(BaseModel):
    name: str
    connection_ids: list[int] = []
    sender_contains: str | None = None
    subject_contains: str | None = None
    has_attachment: bool | None = None
    action_type: str = "mark_detected"
    configuration: dict = {}


class AutomationRuleUpdate(BaseModel):
    name: str
    connection_ids: list[int] = []
    sender_contains: str | None = None
    subject_contains: str | None = None
    has_attachment: bool | None = None
    action_type: str = "mark_detected"
    configuration: dict = {}
    is_active: bool = True


class AutomationRuleResponse(BaseModel):
    id: int
    organization_id: int
    google_connection_id: int | None
    connection_ids: list[int] = []
    whatsapp_enabled_connection_ids: list[int] = []
    api_connection_count: int = 0
    name: str
    is_active: bool
    sender_contains: str | None
    subject_contains: str | None
    has_attachment: bool | None
    action_type: str
    configuration: dict
    created_at: str
    updated_at: str


class RuleWhatsAppNotificationsUpdate(BaseModel):
    connection_ids: list[int] = []


class RuleApiConnectionCreate(BaseModel):
    name: str
    method: str = "POST"
    url: str
    headers: list[dict] = []
    query_params: list[dict] = []
    body_fields: list[dict] = []
    timeout_seconds: int = 15
    is_active: bool = True


class RuleApiConnectionUpdate(BaseModel):
    name: str
    method: str = "POST"
    url: str
    headers: list[dict] = []
    query_params: list[dict] = []
    body_fields: list[dict] = []
    timeout_seconds: int = 15
    is_active: bool = True


class RuleApiConnectionTestRequest(RuleApiConnectionCreate):
    pass


class RuleApiConnectionTestResponse(BaseModel):
    ok: bool
    method: str
    url: str
    status_code: int | None = None
    elapsed_ms: int
    message: str
    response_preview: str | None = None


class RuleApiConnectionResponse(BaseModel):
    id: int
    organization_id: int
    rule_id: int
    name: str
    method: str
    url: str
    headers: list[dict] = []
    query_params: list[dict] = []
    body_fields: list[dict] = []
    timeout_seconds: int
    is_active: bool
    created_at: str
    updated_at: str


class RuleFollowupConfigUpdate(BaseModel):
    enabled: bool = False
    response_time_minutes: int = 120
    notify_whatsapp_on_overdue: bool = False
    warn_before_minutes: int | None = None
    escalation_minutes: int | None = None


class ManualFollowupCreate(BaseModel):
    email_message_id: int
    response_time_minutes: int = 120
    notify_whatsapp_on_overdue: bool = False
    warn_before_minutes: int | None = None
    escalation_minutes: int | None = None


class EmailFollowupResponse(BaseModel):
    id: int
    organization_id: int
    google_connection_id: int
    connection_email: str | None = None
    automation_rule_id: int | None = None
    automation_rule_name: str | None = None
    email_message_id: int | None = None
    gmail_thread_id: str
    initial_message_id: str
    subject: str | None = None
    sender: str | None = None
    received_at: str | None = None
    status: str
    response_due_at: str | None = None
    first_response_at: str | None = None
    response_time_minutes: int | None = None
    message_count: int
    last_message_at: str | None = None
    last_message_from: str | None = None
    notified_overdue_at: str | None = None
    escalated_at: str | None = None
    tracking_source: str = "rule"
    tracking_started_at: str | None = None
    warn_before_minutes: int | None = None
    notify_whatsapp_on_overdue: bool = False
    escalation_minutes: int | None = None
    warned_at: str | None = None
    escalation_notified_at: str | None = None
    closed_at: str | None = None
    closure_reason: str | None = None
    business_minutes_elapsed: int | None = None
    business_due_at: str | None = None
    created_at: str
    updated_at: str


class SystemEventResponse(BaseModel):
    id: int
    organization_id: int | None
    google_connection_id: int | None
    level: str
    event_type: str
    message: str
    metadata: dict
    created_at: str


class RuleDraftFromTextRequest(BaseModel):
    text: str
    connection_ids: list[int] = []


class RuleDraftResponse(BaseModel):
    name: str
    connection_ids: list[int] = []
    sender_contains: str | None = None
    subject_contains: str | None = None
    has_attachment: bool | None = None
    action_type: str = "mark_detected"
    configuration: dict = {}
