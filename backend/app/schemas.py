from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class OrganizationCreate(BaseModel):
    name: str


class OrganizationUpdate(BaseModel):
    name: str


class OrganizationResponse(BaseModel):
    id: int
    name: str
    role: str
    created_at: str


class LinkGoogleAccountRequest(BaseModel):
    email: EmailStr
    display_name: str | None = None
    purpose: str | None = None
    google_user_id: str | None = None
    scopes: list[str] = ["gmail.readonly"]
    refresh_token: str | None = None


class UpdateGoogleConnectionRequest(BaseModel):
    display_name: str | None = None
    purpose: str | None = None


class WhatsAppSetupRequest(BaseModel):
    phone_number: str


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
