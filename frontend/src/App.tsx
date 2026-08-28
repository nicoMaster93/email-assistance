import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Bell,
  Building2,
  CheckCircle2,
  Clock,
  Filter,
  Inbox,
  Info,
  Link2,
  ListChecks,
  LogOut,
  Mail,
  MessageCircle,
  Eye,
  EyeOff,
  Palette,
  Paperclip,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Pencil,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import {
  ApiMapping,
  Attachment,
  AutomationRule,
  AUTH_EXPIRED_EVENT,
  createAccountAccess,
  createOrganization,
  createManualFollowup,
  createRootUser,
  createRuleApiConnection,
  createRule,
  deleteConnection,
  deleteOrganization,
  deleteRuleApiConnection,
  deleteRule,
  EmailFollowup,
  EmailMessage,
  evaluateFollowups,
  getFollowupSummary,
  GoogleConnection,
  listAttachments,
  listEvents,
  listFollowups,
  listMessages,
  listConnections,
  listOrganizations,
  listRuleApiConnections,
  listRootUsers,
  listRules,
  login,
  Organization,
  RuleApiConnection,
  RootUser,
  startGoogleOAuth,
  startWhatsAppSetup,
  stopWatchConnection,
  syncConnection,
  SystemEvent,
  testRuleApiConnection,
  updateConnection,
  updateConnectionFollowup,
  updateOrganization,
  updateOrganizationBusinessHours,
  updateProfile,
  updateRule,
  updateRuleApiConnection,
  updateRuleFollowup,
  updateRuleWhatsAppNotifications,
  updateWhatsAppPreferences,
  User,
  watchConnection,
} from "./services/api";

type AttachmentFilter = "all" | "with" | "without";
type MainTab = "accounts" | "rules";
type WorkTab = "emails" | "rules" | "attachments" | "events" | "followups";
type RuleMode = "ai" | "manual";
type WatchDuration = "1w" | "1m" | "3m" | "1y" | "custom";
type PublicPage = "home" | "privacy" | "terms" | "data-deletion";
type MappingGroup = "headers" | "query_params" | "body_fields";
type ThemePalette = "automated-mail" | "emerald" | "slate";

const WORK_TABS: WorkTab[] = ["emails", "rules", "attachments", "events", "followups"];
const THEME_PALETTES: Array<{ value: ThemePalette; label: string }> = [
  { value: "automated-mail", label: "Oscuro" },
  { value: "emerald", label: "Claro" },
  { value: "slate", label: "Corporativo" },
];

function ThemeSwitcher({
  isOpen,
  onChange,
  onToggle,
  value,
}: {
  isOpen: boolean;
  onChange: (value: ThemePalette) => void;
  onToggle: () => void;
  value: ThemePalette;
}) {
  return (
    <div className="theme-menu">
      <button
        aria-expanded={isOpen}
        aria-haspopup="menu"
        className="icon-button"
        onClick={onToggle}
        title="Cambiar paleta"
        type="button"
      >
        <Palette size={18} />
      </button>
      {isOpen && (
        <div className="theme-popover" role="menu" aria-label="Paletas de color">
          <div>
            <strong>Paleta</strong>
            <span>{THEME_PALETTES.find((palette) => palette.value === value)?.label}</span>
          </div>
          {THEME_PALETTES.map((palette) => (
            <button
              className={value === palette.value ? "active" : ""}
              key={palette.value}
              onClick={() => onChange(palette.value)}
              role="menuitem"
              type="button"
            >
              <i aria-hidden="true" className={`theme-swatch ${palette.value}`} />
              <span>{palette.label}</span>
              {value === palette.value && <CheckCircle2 size={16} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const API_SOURCE_OPTIONS = [
  ["subject", "Asunto"],
  ["body_text", "Cuerpo del correo"],
  ["snippet", "Resumen de Gmail"],
  ["sender", "Remitente"],
  ["recipients", "Destinatarios"],
  ["received_at", "Fecha de recepcion"],
  ["account_email", "Cuenta conectada"],
  ["rule_name", "Regla aplicada"],
  ["gmail_message_id", "Gmail Message ID"],
  ["gmail_thread_id", "Gmail Thread ID"],
  ["gmail_history_id", "Gmail History ID"],
  ["has_attachments", "Tiene adjuntos"],
  ["attachment_count", "Cantidad de adjuntos"],
  ["attachments", "Lista de adjuntos"],
] as const;

const BUSINESS_DAY_OPTIONS = [
  [1, "Lun"],
  [2, "Mar"],
  [3, "Mie"],
  [4, "Jue"],
  [5, "Vie"],
  [6, "Sab"],
  [7, "Dom"],
] as const;

type BusinessDayHoursState = Record<
  string,
  {
    enabled: boolean;
    uses_default: boolean;
    start_time: string | null;
    end_time: string | null;
  }
>;

function defaultBusinessDayHours(days: number[] = [1, 2, 3, 4, 5]) {
  return BUSINESS_DAY_OPTIONS.reduce<BusinessDayHoursState>((accumulator, [day]) => {
    accumulator[String(day)] = {
      enabled: days.includes(day),
      uses_default: true,
      start_time: null,
      end_time: null,
    };
    return accumulator;
  }, {});
}

function ToggleRow({
  checked,
  description,
  disabled,
  label,
  onChange,
}: {
  checked: boolean;
  description?: string;
  disabled?: boolean;
  label: string;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className={`toggle-row ${disabled ? "disabled" : ""} ${!checked ? "off" : ""}`}>
      <span>
        <strong>{label}</strong>
        {description && <small>{description}</small>}
      </span>
      <input checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} type="checkbox" />
      <i aria-hidden="true" />
    </label>
  );
}

function BrandTitle({ subtitle, title }: { subtitle: string; title: string }) {
  return (
    <div className="brand-title">
      <img className="portal-icon" src="/email-assistance-icon-192-blue.png" alt="" aria-hidden="true" />
      <div>
        <p className="eyebrow">Email Assistance</p>
        <h1>{title}</h1>
        <p className="muted">{subtitle}</p>
      </div>
    </div>
  );
}

function currentPublicPage(pathname: string): PublicPage | null {
  if (pathname === "/" || pathname === "") return "home";
  if (pathname === "/privacy-policy") return "privacy";
  if (pathname === "/terms-of-service") return "terms";
  if (pathname === "/data-deletion") return "data-deletion";
  return null;
}

function parseAppRoute(pathname = window.location.pathname) {
  const segments = pathname.split("/").filter(Boolean);
  const result: {
    organizationId: string;
    connectionId: string;
    mainTab: MainTab;
    panel: WorkTab;
  } = {
    organizationId: "",
    connectionId: "all",
    mainTab: "accounts",
    panel: "emails",
  };

  if (segments[0] !== "app") return result;
  if (segments[1] === "organizaciones" && segments[2]) {
    result.organizationId = segments[2];
  }
  if (segments[3] === "reglas") {
    result.mainTab = "rules";
    return result;
  }
  if (segments[3] === "cuentas") {
    result.mainTab = "accounts";
    if (segments[4]) {
      result.connectionId = segments[4];
    }
    if (segments[5] && WORK_TABS.includes(segments[5] as WorkTab)) {
      result.panel = segments[5] as WorkTab;
    }
  }
  return result;
}

function buildAppPath(organizationId: string, mainTab: MainTab, connectionId: string, panel: WorkTab) {
  if (!organizationId) return "/app/organizaciones";
  if (mainTab === "rules") return `/app/organizaciones/${organizationId}/reglas`;
  if (connectionId && connectionId !== "all") return `/app/organizaciones/${organizationId}/cuentas/${connectionId}/${panel}`;
  return `/app/organizaciones/${organizationId}/cuentas`;
}

function PublicHeader({ themeSwitcher }: { themeSwitcher: ReactNode }) {
  return (
    <header className="public-header">
      <a className="public-logo-link" href="/" aria-label="Email Assistance">
        <img src="/logo-email-assitance-blue.png" alt="Email Assistance" />
      </a>
      <nav className="public-nav" aria-label="Legal">
        <a href="/privacy-policy">Privacidad</a>
        <a href="/terms-of-service">Terminos</a>
        <a href="/data-deletion">Eliminar datos</a>
        {themeSwitcher}
        <a className="public-login-link" href="/login">Iniciar sesion</a>
      </nav>
    </header>
  );
}

function PublicLayout({ children, themeSwitcher }: { children: ReactNode; themeSwitcher: ReactNode }) {
  return (
    <main className="public-shell">
      <PublicHeader themeSwitcher={themeSwitcher} />
      {children}
      <footer className="public-footer">
        <span>Email Assistance</span>
        <span>Uso responsable de datos de Gmail para monitoreo operativo.</span>
      </footer>
    </main>
  );
}

function PublicHome({ themeSwitcher }: { themeSwitcher: ReactNode }) {
  return (
    <PublicLayout themeSwitcher={themeSwitcher}>
      <section className="public-hero">
        <div>
          <p className="eyebrow">Automatizacion de correo</p>
          <h1>Email Assistance</h1>
          <p>
            Plataforma para conectar cuentas Gmail, sincronizar solo correos relevantes mediante reglas de negocio,
            gestionar adjuntos, enviar avisos por WhatsApp y dar seguimiento a respuestas importantes.
          </p>
          <div className="public-actions">
            <a className="primary-link" href="/login">Acceder al portal</a>
            <a className="secondary-link" href="/privacy-policy">Ver politica de privacidad</a>
          </div>
        </div>
        <div className="public-hero-card">
          <strong>Funciones principales</strong>
          <ul>
            <li>Conexion segura con Google OAuth.</li>
            <li>Reglas configurables por cuenta y organizacion.</li>
            <li>Sincronizacion filtrada de correos y adjuntos.</li>
            <li>Alertas y seguimiento operativo por WhatsApp.</li>
          </ul>
        </div>
      </section>
      <section className="public-grid">
        <article>
          <h2>Datos minimos y visibles</h2>
          <p>La aplicacion usa datos de Gmail solo para funciones visibles al usuario: bandeja filtrada, reglas, adjuntos, eventos y seguimientos.</p>
        </article>
        <article>
          <h2>Control del usuario</h2>
          <p>El usuario puede desconectar una cuenta Gmail y solicitar la eliminacion completa de datos almacenados en la plataforma.</p>
        </article>
        <article>
          <h2>Seguridad</h2>
          <p>Los tokens se almacenan cifrados y las conexiones productivas deben operar sobre HTTPS con dominios verificados.</p>
        </article>
      </section>
    </PublicLayout>
  );
}

function PrivacyPolicyPage({ themeSwitcher }: { themeSwitcher: ReactNode }) {
  return (
    <PublicLayout themeSwitcher={themeSwitcher}>
      <article className="legal-page">
        <p className="eyebrow">Politica de privacidad</p>
        <h1>Politica de Privacidad de Email Assistance</h1>
        <p>
          Email Assistance accede a informacion de Gmail solo cuando un usuario autoriza la conexion mediante Google OAuth.
          La finalidad es sincronizar correos que cumplan reglas configuradas por el usuario u organizacion, mostrar contexto operativo,
          gestionar adjuntos, generar eventos, enviar notificaciones configuradas y dar seguimiento a respuestas.
        </p>
        <h2>Datos de Google que podemos almacenar</h2>
        <p>
          Podemos almacenar correo conectado, identificadores de mensajes e hilos, remitente, destinatarios, asunto, fecha de recepcion,
          fragmento, cuerpo del mensaje, metadatos necesarios para auditoria, nombre de la regla coincidente y adjuntos descargados.
          Los tokens de Google se almacenan cifrados y se usan solo para mantener la sincronizacion autorizada.
        </p>
        <h2>Uso limitado</h2>
        <p>
          El uso de la informacion recibida de las APIs de Google se adherira a la Politica de Datos del Usuario de los Servicios de API
          de Google, incluidos los requisitos de Uso Limitado. No vendemos datos de Gmail, no los usamos para publicidad, no los transferimos
          a data brokers y no los usamos para entrenar modelos generales o fundacionales.
        </p>
        <h2>Retencion</h2>
        <p>
          Los datos se conservan mientras la cuenta permanezca conectada y sean necesarios para bandeja, reglas, adjuntos, eventos,
          notificaciones o seguimientos. Al desconectar una cuenta o solicitar eliminacion, se eliminan tokens, correos sincronizados,
          adjuntos locales y datos operativos asociados.
        </p>
        <h2>Eliminacion</h2>
        <p>
          Los usuarios pueden eliminar datos desde el portal al desconectar la cuenta Gmail. Tambien pueden solicitar eliminacion completa
          siguiendo el proceso descrito en la pagina de eliminacion de datos.
        </p>
      </article>
    </PublicLayout>
  );
}

function TermsPage({ themeSwitcher }: { themeSwitcher: ReactNode }) {
  return (
    <PublicLayout themeSwitcher={themeSwitcher}>
      <article className="legal-page">
        <p className="eyebrow">Terminos de servicio</p>
        <h1>Terminos de Servicio de Email Assistance</h1>
        <p>
          Email Assistance es una herramienta para administracion operativa de correos conectados por usuarios autorizados. El usuario
          es responsable de contar con permisos para conectar cuentas Gmail, crear reglas, habilitar notificaciones y gestionar datos
          dentro de su organizacion.
        </p>
        <h2>Uso permitido</h2>
        <p>
          La aplicacion debe usarse para productividad, monitoreo operativo, gestion de adjuntos, seguimiento de respuestas y notificaciones
          relacionadas con correos autorizados. No debe usarse para vigilancia no autorizada, publicidad, venta de datos o acceso a cuentas
          sin consentimiento.
        </p>
        <h2>Responsabilidades</h2>
        <p>
          El proveedor mantiene controles tecnicos razonables para proteger la plataforma. El cliente debe administrar usuarios, reglas,
          horarios, cuentas conectadas y permisos internos de forma responsable.
        </p>
        <h2>Disponibilidad y cambios</h2>
        <p>
          El servicio puede actualizarse para mejorar seguridad, compatibilidad con Google APIs, cumplimiento normativo y estabilidad.
          El uso continuo implica aceptacion de las condiciones vigentes.
        </p>
      </article>
    </PublicLayout>
  );
}

function DataDeletionPage({ themeSwitcher }: { themeSwitcher: ReactNode }) {
  return (
    <PublicLayout themeSwitcher={themeSwitcher}>
      <article className="legal-page">
        <p className="eyebrow">Eliminacion de datos</p>
        <h1>Solicitud de eliminacion de datos</h1>
        <p>
          Los usuarios pueden eliminar datos de Gmail almacenados en Email Assistance desde el portal, desconectando la cuenta Gmail.
          Este proceso borra tokens de Google, correos sincronizados, adjuntos almacenados, seguimientos, eventos y configuraciones asociadas
          a esa cuenta.
        </p>
        <h2>Proceso desde el portal</h2>
        <ol>
          <li>Inicia sesion en Email Assistance.</li>
          <li>Selecciona la organizacion y la cuenta Gmail conectada.</li>
          <li>Usa la accion de eliminar o desconectar cuenta.</li>
          <li>Confirma la eliminacion completa de datos asociados a esa cuenta.</li>
        </ol>
        <h2>Solicitud asistida</h2>
        <p>
          Si no puedes acceder al portal, contacta al administrador de tu organizacion o al equipo responsable del despliegue indicando
          el correo Gmail conectado y la organizacion a la que pertenece. La eliminacion debe ejecutarse sin demoras indebidas una vez
          validada la identidad y autorizacion del solicitante.
        </p>
      </article>
    </PublicLayout>
  );
}

function PublicPageView({ page, themeSwitcher }: { page: PublicPage; themeSwitcher: ReactNode }) {
  if (page === "privacy") return <PrivacyPolicyPage themeSwitcher={themeSwitcher} />;
  if (page === "terms") return <TermsPage themeSwitcher={themeSwitcher} />;
  if (page === "data-deletion") return <DataDeletionPage themeSwitcher={themeSwitcher} />;
  return <PublicHome themeSwitcher={themeSwitcher} />;
}

function formatDate(value: string | null) {
  if (!value) return "Sin fecha";
  return new Date(value).toLocaleString();
}

function fileSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatMinutes(value: number | null) {
  if (value === null || value === undefined) return "Sin dato";
  if (value < 60) return `${value} min`;
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return minutes ? `${hours}h ${minutes}m` : `${hours}h`;
}

function followupConfig(rule: AutomationRule) {
  const config = rule.configuration?.followup;
  if (!config || typeof config !== "object") {
    return {
      enabled: false,
      response_time_minutes: 120,
      notify_whatsapp_on_overdue: false,
      warn_before_minutes: null as number | null,
      escalation_minutes: null as number | null,
    };
  }
  const typed = config as Record<string, unknown>;
  return {
    enabled: Boolean(typed.enabled),
    response_time_minutes: Number(typed.response_time_minutes || 120),
    notify_whatsapp_on_overdue: Boolean(typed.notify_whatsapp_on_overdue),
    warn_before_minutes:
      typed.warn_before_minutes === null || typed.warn_before_minutes === undefined ? null : Number(typed.warn_before_minutes),
    escalation_minutes:
      typed.escalation_minutes === null || typed.escalation_minutes === undefined
        ? null
        : Number(typed.escalation_minutes),
  };
}

function followupStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: "Pendiente",
    overdue: "Vencido",
    responded: "Respondido",
    responded_late: "Respondido tarde",
    escalated: "Escalado",
  };
  return labels[status] || status;
}

function ignoreReasonLabel(value: string) {
  const labels: Record<string, string> = {
    no_active_rules_for_connection: "La cuenta no tenia reglas activas asociadas",
    no_ai_rule_matched: "Ninguna regla con IA considero que el correo cumple",
    no_rule_matched: "Ninguna regla asociada coincide con el correo",
  };
  return labels[value] || value;
}

function textFromMetadata(value: unknown) {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "boolean") return value ? "Si" : "No";
  if (typeof value === "string") return decodeEmailText(value);
  if (typeof value === "number") return String(value);
  return null;
}

function decodeEmailText(value: string | null | undefined) {
  if (!value) return "";
  return value
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCharCode(Number.parseInt(code, 16)))
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number.parseInt(code, 10)))
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&nbsp;/g, " ");
}

function eventTone(event: SystemEvent) {
  if (event.event_type.includes("ignored") || event.level === "warning") return "warning";
  if (event.level === "error") return "danger";
  if (
    event.event_type.includes("matched") ||
    event.event_type.includes("sent") ||
    event.event_type.includes("synced") ||
    event.event_type.includes("registered")
  ) {
    return "success";
  }
  return "neutral";
}

function eventTitle(event: SystemEvent) {
  const subject = textFromMetadata(event.metadata?.subject);
  if (
    (event.event_type === "gmail_message_ignored" ||
      event.event_type === "gmail_message_matched" ||
      event.event_type === "gmail_message_deleted") &&
    subject
  ) {
    return subject;
  }
  return event.message;
}

function eventSubtitle(event: SystemEvent) {
  const sender = textFromMetadata(event.metadata?.sender);
  const reason = textFromMetadata(event.metadata?.ignore_reason);
  const matchedRule = textFromMetadata(event.metadata?.matched_rule_name);
  if (event.event_type === "gmail_message_deleted" && sender) return `${sender} - El correo original fue eliminado en Gmail`;
  if (sender && matchedRule) return `${sender} - Coincidio con ${matchedRule}`;
  if (sender && reason) return `${sender} - ${ignoreReasonLabel(reason)}`;
  if (sender) return sender;
  return event.event_type;
}

function eventTypeLabel(type: string) {
  const labels: Record<string, string> = {
    gmail_message_ignored: "Correo descartado",
    gmail_message_matched: "Correo sincronizado",
    gmail_message_deleted: "Correo eliminado en Gmail",
    gmail_history_synced: "Historial sincronizado",
    gmail_pubsub_received: "Aviso de Gmail recibido",
    gmail_watch_registered: "Monitor activado",
    gmail_watch_stopped: "Monitor inactivado",
    whatsapp_email_notification_sent: "WhatsApp enviado",
    followup_whatsapp_warning_sent: "WhatsApp seguimiento por vencer",
    followup_whatsapp_overdue_sent: "WhatsApp seguimiento vencido",
    followup_whatsapp_escalation_sent: "WhatsApp seguimiento escalado",
    followup_whatsapp_late_response_sent: "WhatsApp contestado tarde",
    followup_whatsapp_response_sent: "WhatsApp respondido",
  };
  return labels[type] || type;
}

function ruleFieldLabel(field: string) {
  const labels: Record<string, string> = {
    sender_contains: "Remitente",
    subject_contains: "Asunto",
    has_attachment: "Adjuntos",
    ai_description: "IA",
  };
  return labels[field] || field;
}

function matchTypeLabel(value: string | null) {
  const labels: Record<string, string> = {
    literal_email: "coincidencia exacta",
    literal_normalized: "coincidencia normalizada",
    token_fuzzy: "coincidencia flexible",
    boolean: "validacion exacta",
    no_match: "sin coincidencia",
  };
  return value ? labels[value] || value : "";
}

function eventDetailItems(event: SystemEvent) {
  const metadata = event.metadata || {};
  const pairs: Array<[string, string]> = [];
  const sender = textFromMetadata(metadata.sender);
  const recipients = textFromMetadata(metadata.recipients);
  const receivedAt = textFromMetadata(metadata.received_at);
  const deletedAt = textFromMetadata(metadata.deleted_at);
  const gmailMessageId = textFromMetadata(metadata.gmail_message_id);
  const hasAttachments = textFromMetadata(metadata.has_attachments);
  const messageIdsFound = textFromMetadata(metadata.message_ids_found);
  const stored = textFromMetadata(metadata.stored);
  const ignored = textFromMetadata(metadata.ignored);
  const attachmentsStored = textFromMetadata(metadata.attachments_stored);

  if (sender) pairs.push(["De", sender]);
  if (recipients) pairs.push(["Para", recipients]);
  if (receivedAt) pairs.push(["Recibido", formatDate(receivedAt)]);
  if (deletedAt) pairs.push(["Eliminado", formatDate(deletedAt)]);
  if (hasAttachments) pairs.push(["Adjuntos", hasAttachments]);
  if (gmailMessageId) pairs.push(["Gmail ID", gmailMessageId]);
  if (messageIdsFound) pairs.push(["Encontrados", messageIdsFound]);
  if (stored) pairs.push(["Sincronizados", stored]);
  if (ignored) pairs.push(["Descartados", ignored]);
  if (attachmentsStored) pairs.push(["Adjuntos guardados", attachmentsStored]);

  return pairs;
}

function eventRuleDiagnostics(event: SystemEvent) {
  const evaluatedRules = event.metadata?.evaluated_rules;
  if (!Array.isArray(evaluatedRules)) return [];
  return evaluatedRules
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const rule = item as Record<string, unknown>;
      const ruleName = textFromMetadata(rule.rule_name) || `Regla ${textFromMetadata(rule.rule_id) || ""}`.trim();
      const matched = Boolean(rule.matched);
      const checks = Array.isArray(rule.checks)
        ? rule.checks
            .map((check) => {
              if (!check || typeof check !== "object") return null;
              const typed = check as Record<string, unknown>;
              const field = textFromMetadata(typed.field);
              const expected = textFromMetadata(typed.expected);
              const passed = Boolean(typed.passed);
              const matchType = textFromMetadata(typed.match_type);
              if (!field || !expected) return null;
              return {
                label: ruleFieldLabel(field),
                expected,
                passed,
                matchType: matchTypeLabel(matchType),
              };
            })
            .filter(Boolean)
        : [];

      return {
        ruleName,
        matched,
        checks,
      };
    })
    .filter(Boolean) as Array<{
      ruleName: string;
      matched: boolean;
      checks: Array<{ label: string; expected: string; passed: boolean; matchType: string }>;
    }>;
}

function isWatchActive(connection: GoogleConnection) {
  if (!connection.watch_expiration_at) return false;
  return new Date(connection.watch_expiration_at).getTime() > Date.now();
}

function isWhatsAppConnected(connection?: GoogleConnection) {
  return (connection?.whatsapp_status || "").trim().toLowerCase() === "connected";
}

function defaultWatchUntil() {
  const value = new Date();
  value.setDate(value.getDate() + 30);
  value.setMinutes(value.getMinutes() - value.getTimezoneOffset());
  return value.toISOString().slice(0, 16);
}

function toIsoFromLocalInput(value: string) {
  return new Date(value).toISOString();
}

function watchDateForDuration(duration: WatchDuration, customValue: string) {
  if (duration === "custom") return customValue;

  const value = new Date();
  if (duration === "1w") value.setDate(value.getDate() + 7);
  if (duration === "1m") value.setMonth(value.getMonth() + 1);
  if (duration === "3m") value.setMonth(value.getMonth() + 3);
  if (duration === "1y") value.setFullYear(value.getFullYear() + 1);
  value.setMinutes(value.getMinutes() - value.getTimezoneOffset());
  return value.toISOString().slice(0, 16);
}

export function App() {
  const initialRoute = useMemo(() => parseAppRoute(), []);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [token, setToken] = useState(() => localStorage.getItem("access_token") ?? "");
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem("user");
    return stored ? JSON.parse(stored) : null;
  });
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [rootUsers, setRootUsers] = useState<RootUser[]>([]);
  const [organizationsLoaded, setOrganizationsLoaded] = useState(false);
  const [selectedOrganizationId, setSelectedOrganizationId] = useState(
    () => initialRoute.organizationId || localStorage.getItem("selected_organization_id") || "",
  );
  const [isOrganizationModalOpen, setIsOrganizationModalOpen] = useState(false);
  const [editingOrganization, setEditingOrganization] = useState<Organization | null>(null);
  const [organizationName, setOrganizationName] = useState("");
  const [isBusinessHoursModalOpen, setIsBusinessHoursModalOpen] = useState(false);
  const [businessTimezone, setBusinessTimezone] = useState("America/Bogota");
  const [businessDays, setBusinessDays] = useState<number[]>([1, 2, 3, 4, 5]);
  const [businessStartTime, setBusinessStartTime] = useState("08:00");
  const [businessEndTime, setBusinessEndTime] = useState("18:00");
  const [businessDayHours, setBusinessDayHours] = useState<BusinessDayHoursState>(() => defaultBusinessDayHours());
  const [holidayCountry, setHolidayCountry] = useState("CO");
  const [businessHoursMessage, setBusinessHoursMessage] = useState("");
  const [watchConnectionTarget, setWatchConnectionTarget] = useState<GoogleConnection | null>(null);
  const [watchDuration, setWatchDuration] = useState<WatchDuration>("1m");
  const [customWatchUntil, setCustomWatchUntil] = useState(defaultWatchUntil);
  const [watchModalMessage, setWatchModalMessage] = useState("");
  const [whatsAppConnectionTarget, setWhatsAppConnectionTarget] = useState<GoogleConnection | null>(null);
  const [whatsAppNumber, setWhatsAppNumber] = useState("");
  const [whatsAppModalMessage, setWhatsAppModalMessage] = useState("");
  const [whatsAppNotificationsEnabled, setWhatsAppNotificationsEnabled] = useState(true);
  const [whatsAppNotifyNewEmail, setWhatsAppNotifyNewEmail] = useState(true);
  const [whatsAppNotifyFollowupOverdue, setWhatsAppNotifyFollowupOverdue] = useState(true);
  const [whatsAppNotifyFollowupWarning, setWhatsAppNotifyFollowupWarning] = useState(true);
  const [whatsAppNotifyFollowupLate, setWhatsAppNotifyFollowupLate] = useState(true);
  const [whatsAppNotifyFollowupResponded, setWhatsAppNotifyFollowupResponded] = useState(true);
  const [ruleWhatsAppTarget, setRuleWhatsAppTarget] = useState<AutomationRule | null>(null);
  const [ruleWhatsAppConnectionIds, setRuleWhatsAppConnectionIds] = useState<number[]>([]);
  const [ruleWhatsAppMessage, setRuleWhatsAppMessage] = useState("");
  const [ruleApiTarget, setRuleApiTarget] = useState<AutomationRule | null>(null);
  const [ruleApiConnections, setRuleApiConnections] = useState<RuleApiConnection[]>([]);
  const [editingRuleApi, setEditingRuleApi] = useState<RuleApiConnection | null>(null);
  const [ruleApiName, setRuleApiName] = useState("");
  const [ruleApiMethod, setRuleApiMethod] = useState("POST");
  const [ruleApiUrl, setRuleApiUrl] = useState("");
  const [ruleApiActive, setRuleApiActive] = useState(true);
  const [ruleApiTimeout, setRuleApiTimeout] = useState("15");
  const [ruleApiHeaders, setRuleApiHeaders] = useState<ApiMapping[]>([]);
  const [ruleApiQueryParams, setRuleApiQueryParams] = useState<ApiMapping[]>([]);
  const [ruleApiBodyFields, setRuleApiBodyFields] = useState<ApiMapping[]>([]);
  const [ruleApiMessage, setRuleApiMessage] = useState("");
  const [ruleApiMessageTone, setRuleApiMessageTone] = useState<"info" | "success" | "error">("info");
  const [ruleApiTesting, setRuleApiTesting] = useState(false);
  const [ruleFollowupTarget, setRuleFollowupTarget] = useState<AutomationRule | null>(null);
  const [ruleFollowupEnabled, setRuleFollowupEnabled] = useState(false);
  const [ruleFollowupHours, setRuleFollowupHours] = useState("2");
  const [ruleFollowupNotifyWhatsApp, setRuleFollowupNotifyWhatsApp] = useState(false);
  const [ruleFollowupWarnMinutes, setRuleFollowupWarnMinutes] = useState("");
  const [ruleFollowupEscalationMinutes, setRuleFollowupEscalationMinutes] = useState("");
  const [ruleFollowupMessage, setRuleFollowupMessage] = useState("");
  const [accountFollowupTarget, setAccountFollowupTarget] = useState<GoogleConnection | null>(null);
  const [accountFollowupEnabled, setAccountFollowupEnabled] = useState(false);
  const [accountFollowupHours, setAccountFollowupHours] = useState("2");
  const [accountFollowupNotifyWhatsApp, setAccountFollowupNotifyWhatsApp] = useState(false);
  const [accountFollowupWarnMinutes, setAccountFollowupWarnMinutes] = useState("");
  const [accountFollowupEscalationMinutes, setAccountFollowupEscalationMinutes] = useState("");
  const [accountFollowupMessage, setAccountFollowupMessage] = useState("");
  const [manualFollowupTarget, setManualFollowupTarget] = useState<EmailMessage | null>(null);
  const [manualFollowupHours, setManualFollowupHours] = useState("2");
  const [manualFollowupNotifyWhatsApp, setManualFollowupNotifyWhatsApp] = useState(false);
  const [manualFollowupWarnMinutes, setManualFollowupWarnMinutes] = useState("");
  const [manualFollowupEscalationMinutes, setManualFollowupEscalationMinutes] = useState("");
  const [manualFollowupMessage, setManualFollowupMessage] = useState("");
  const [followupSummary, setFollowupSummary] = useState<{ totals: Record<string, number>; avg_response_minutes: number | null } | null>(null);
  const [editingRule, setEditingRule] = useState<AutomationRule | null>(null);
  const [connections, setConnections] = useState<GoogleConnection[]>([]);
  const [messages, setMessages] = useState<EmailMessage[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [followups, setFollowups] = useState<EmailFollowup[]>([]);
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [activeMainTab, setActiveMainTab] = useState<MainTab>(initialRoute.mainTab);
  const [activePanel, setActivePanel] = useState<WorkTab>(initialRoute.panel);
  const [ruleMode, setRuleMode] = useState<RuleMode>("ai");
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<GoogleConnection | null>(null);
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);
  const [newAccountName, setNewAccountName] = useState("");
  const [newAccountPurpose, setNewAccountPurpose] = useState("");
  const [newAccountUserEmail, setNewAccountUserEmail] = useState("");
  const [newAccountPassword, setNewAccountPassword] = useState("");
  const [accountModalMessage, setAccountModalMessage] = useState("");
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [profileEmail, setProfileEmail] = useState("");
  const [profilePassword, setProfilePassword] = useState("");
  const [profileMessage, setProfileMessage] = useState("");
  const [rootUserName, setRootUserName] = useState("");
  const [rootUserEmail, setRootUserEmail] = useState("");
  const [rootUserPassword, setRootUserPassword] = useState("");
  const [rootUserMessage, setRootUserMessage] = useState("");
  const [isEditingConnection, setIsEditingConnection] = useState(false);
  const [editName, setEditName] = useState("");
  const [editPurpose, setEditPurpose] = useState("");
  const [ruleName, setRuleName] = useState("Facturas con adjuntos");
  const [ruleSender, setRuleSender] = useState("");
  const [ruleSubject, setRuleSubject] = useState("factura");
  const [ruleHasAttachment, setRuleHasAttachment] = useState(true);
  const [ruleText, setRuleText] = useState("Detecta facturas o invoices que tengan PDF adjunto");
  const [ruleConnectionIds, setRuleConnectionIds] = useState<number[]>([]);
  const [ruleModalMessage, setRuleModalMessage] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedMessageId, setSelectedMessageId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [selectedConnectionId, setSelectedConnectionId] = useState(initialRoute.connectionId);
  const [statusFilter, setStatusFilter] = useState("all");
  const [followupStatusFilter, setFollowupStatusFilter] = useState("all");
  const [eventTypeFilter, setEventTypeFilter] = useState("business");
  const [eventDateFrom, setEventDateFrom] = useState("");
  const [eventDateTo, setEventDateTo] = useState("");
  const [eventLimit, setEventLimit] = useState("100");
  const [attachmentFilter, setAttachmentFilter] = useState<AttachmentFilter>("all");
  const [showFilters, setShowFilters] = useState(false);
  const [themePalette, setThemePalette] = useState<ThemePalette>(
    () => (localStorage.getItem("theme_palette") as ThemePalette | null) || "automated-mail",
  );
  const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false);
  const publicPage = currentPublicPage(window.location.pathname);

  const isLoggedIn = useMemo(() => Boolean(token && user), [token, user]);
  const selectedOrganization =
    organizations.find((organization) => String(organization.id) === selectedOrganizationId) ?? null;
  const isSuperRoot = user?.role === "super_root" || user?.platform_role === "super_root";
  const isOwner = user?.role === "owner" || selectedOrganization?.role === "owner";
  const isAccountUser = user?.role === "account_user" || selectedOrganization?.role === "account_user";
  const selectedConnection = connections.find((connection) => String(connection.id) === selectedConnectionId) ?? null;
  const visibleAttachments = selectedConnection
    ? attachments.filter((item) => item.google_connection_id === selectedConnection.id)
    : attachments;
  const visibleRules = selectedConnection
    ? rules.filter((rule) => (rule.connection_ids || []).includes(selectedConnection.id))
    : rules;
  const visibleEvents = selectedConnection
    ? events.filter((event) => event.google_connection_id === selectedConnection.id)
    : events;
  const visibleFollowups = (selectedConnection
    ? followups.filter((followup) => followup.google_connection_id === selectedConnection.id)
    : followups
  ).filter((followup) => followupStatusFilter === "all" || followup.status === followupStatusFilter);

  useEffect(() => {
    if (!token) return;
    refreshOrganizations(token);
  }, [token]);

  useEffect(() => {
    document.documentElement.dataset.theme = themePalette;
    localStorage.setItem("theme_palette", themePalette);
  }, [themePalette]);

  useEffect(() => {
    function handlePopState() {
      const route = parseAppRoute();
      setSelectedOrganizationId(route.organizationId);
      setSelectedConnectionId(route.connectionId);
      setActiveMainTab(route.mainTab);
      setActivePanel(route.panel);
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (!token || !selectedOrganizationId) return;
    const params = new URLSearchParams(window.location.search);
    const googleConnected = params.get("google_connected");
    const googleError = params.get("google_error");
    if (googleConnected) {
      setMessage(`Cuenta conectada: ${googleConnected}`);
      window.history.replaceState({}, "", window.location.pathname);
    }
    if (googleError) {
      setMessage(googleError);
      window.history.replaceState({}, "", window.location.pathname);
    }
    refreshConnections(token);
  }, [token, selectedOrganizationId]);

  useEffect(() => {
    if (!isLoggedIn || isSuperRoot) return;
    const nextPath = buildAppPath(selectedOrganizationId, activeMainTab, selectedConnectionId, activePanel);
    if (window.location.pathname !== nextPath) {
      window.history.replaceState({}, "", nextPath);
    }
  }, [activeMainTab, activePanel, isLoggedIn, isSuperRoot, selectedConnectionId, selectedOrganizationId]);

  useEffect(() => {
    if (!selectedOrganizationId) return;
    localStorage.setItem("selected_organization_id", selectedOrganizationId);
  }, [selectedOrganizationId]);

  useEffect(() => {
    setEditName(selectedConnection?.display_name || selectedConnection?.email || "");
    setEditPurpose(selectedConnection?.purpose || "");
    setIsEditingConnection(false);
  }, [selectedConnectionId, selectedConnection?.display_name, selectedConnection?.purpose, selectedConnection?.email]);

  useEffect(() => {
    if (!isOwner && !["emails", "rules", "attachments"].includes(activePanel)) {
      setActivePanel("emails");
    }
  }, [activePanel, isOwner]);

  useEffect(() => {
    if (!connections.length || selectedConnectionId === "all") return;
    if (!connections.some((connection) => String(connection.id) === selectedConnectionId)) {
      setSelectedConnectionId("all");
      setActivePanel("emails");
    }
  }, [connections, selectedConnectionId]);

  async function refreshConnections(activeToken = token) {
    try {
      const loadedConnections = await listConnections(activeToken);
      setConnections(loadedConnections);
      if ((user?.role === "account_user" || selectedOrganization?.role === "account_user") && loadedConnections.length > 0) {
        setSelectedConnectionId(String(loadedConnections[0].id));
      }
      setMessages(await listMessages(activeToken));
      setAttachments(await listAttachments(activeToken));
      setRules(await listRules(activeToken));
      if (user?.role === "owner" || selectedOrganization?.role === "owner") {
        setFollowups(await listFollowups(activeToken));
        setFollowupSummary(await getFollowupSummary(activeToken));
        setEvents(await listEvents(activeToken, { event_type: "business", limit: 100 }));
      } else {
        setFollowups([]);
        setFollowupSummary(null);
        setEvents([]);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudieron cargar las cuentas");
    }
  }

  async function refreshEventsWithFilters(activeToken = token) {
    try {
      setLoading(true);
      setEvents(
        await listEvents(activeToken, {
          connection_id: selectedConnection?.id,
          event_type: eventTypeFilter === "all" ? undefined : eventTypeFilter,
          date_from: eventDateFrom,
          date_to: eventDateTo,
          limit: Number(eventLimit || 100),
        }),
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudieron cargar los eventos");
    } finally {
      setLoading(false);
    }
  }

  async function clearEventFilters() {
    setEventTypeFilter("business");
    setEventDateFrom("");
    setEventDateTo("");
    setEventLimit("100");
    try {
      setEvents(await listEvents(token, { connection_id: selectedConnection?.id, event_type: "business", limit: 100 }));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudieron cargar los eventos");
    }
  }

  async function refreshOrganizations(activeToken = token) {
    try {
      if (user?.role === "super_root" || user?.platform_role === "super_root") {
        setRootUsers(await listRootUsers(activeToken));
        setOrganizations([]);
        setSelectedOrganizationId("");
        localStorage.removeItem("selected_organization_id");
        return;
      }
      const items = await listOrganizations(activeToken);
      setOrganizations(items);
      const routeOrganizationId = parseAppRoute().organizationId;
      const storedOrganizationId = routeOrganizationId || localStorage.getItem("selected_organization_id");
      const storedStillExists = items.some((organization) => String(organization.id) === storedOrganizationId);
      if (items.length === 1 && items[0].role === "account_user") {
        setSelectedOrganizationId(String(items[0].id));
        localStorage.setItem("selected_organization_id", String(items[0].id));
        setUser((current) => (current ? { ...current, organization_id: items[0].id, role: items[0].role } : current));
        return;
      }
      if (storedOrganizationId && storedStillExists) {
        setSelectedOrganizationId(storedOrganizationId);
      } else {
        setSelectedOrganizationId("");
        localStorage.removeItem("selected_organization_id");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudieron cargar las organizaciones");
    } finally {
      setOrganizationsLoaded(true);
    }
  }

  async function refreshRootUsers(activeToken = token) {
    try {
      setRootUsers(await listRootUsers(activeToken));
    } catch (error) {
      setRootUserMessage(error instanceof Error ? error.message : "No se pudieron cargar los usuarios root");
    }
  }

  const filteredMessages = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return messages.filter((emailMessage) => {
      const matchesConnection =
        selectedConnectionId === "all" || String(emailMessage.google_connection_id) === selectedConnectionId;
      const matchesStatus = statusFilter === "all" || emailMessage.status === statusFilter;
      const matchesAttachments =
        attachmentFilter === "all" ||
        (attachmentFilter === "with" && emailMessage.has_attachments) ||
        (attachmentFilter === "without" && !emailMessage.has_attachments);
      const searchableText = [
        decodeEmailText(emailMessage.subject),
        decodeEmailText(emailMessage.sender),
        emailMessage.connection_email,
        decodeEmailText(emailMessage.snippet),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return matchesConnection && matchesStatus && matchesAttachments && searchableText.includes(normalizedQuery);
    });
  }, [attachmentFilter, messages, query, selectedConnectionId, statusFilter]);

  const selectedMessage = useMemo(() => {
    if (!filteredMessages.length) return null;
    return filteredMessages.find((emailMessage) => emailMessage.id === selectedMessageId) ?? filteredMessages[0];
  }, [filteredMessages, selectedMessageId]);

  const selectedAttachments = useMemo(() => {
    if (!selectedMessage) return [];
    return attachments.filter((attachment) => attachment.email_message_id === selectedMessage.id);
  }, [attachments, selectedMessage]);

  useEffect(() => {
    if (!filteredMessages.length) {
      setSelectedMessageId(null);
      return;
    }

    if (!selectedMessageId || !filteredMessages.some((emailMessage) => emailMessage.id === selectedMessageId)) {
      setSelectedMessageId(filteredMessages[0].id);
    }
  }, [filteredMessages, selectedMessageId]);

  const activeRules = rules.filter((rule) => rule.is_active).length;
  const statusOptions = Array.from(new Set(messages.map((emailMessage) => emailMessage.status))).filter(Boolean);
  const followupStatusOptions = Array.from(new Set(followups.map((followup) => followup.status))).filter(Boolean);
  const eventTypeOptions = [
    ["business", "Actividad util"],
    ["all", "Todos los eventos"],
    ["gmail_message_matched", "Correos sincronizados"],
    ["gmail_message_ignored", "Correos descartados"],
    ["gmail_message_deleted", "Eliminados en Gmail"],
    ["gmail_pubsub_received", "Avisos Pub/Sub"],
    ["gmail_history_synced", "Historial sincronizado"],
    ["whatsapp_email_notification_sent", "WhatsApp enviados"],
    ["followup_whatsapp_warning_sent", "WhatsApp por vencer"],
    ["followup_whatsapp_overdue_sent", "WhatsApp vencidos"],
    ["followup_whatsapp_late_response_sent", "WhatsApp contestados tarde"],
    ["followup_whatsapp_response_sent", "WhatsApp respondidos"],
  ];

  function clearSession(expiredMessage?: string) {
    setToken("");
    setUser(null);
    setOrganizations([]);
    setOrganizationsLoaded(false);
    setSelectedOrganizationId("");
    setConnections([]);
    setMessages([]);
    setAttachments([]);
    setRules([]);
    setFollowups([]);
    setFollowupSummary(null);
    setEvents([]);
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    localStorage.removeItem("selected_organization_id");
    if (expiredMessage) {
      setMessage(expiredMessage);
    }
  }

  useEffect(() => {
    function handleAuthExpired() {
      clearSession("Tu sesion expiro. Inicia sesion nuevamente.");
    }

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
  }, []);

  function connectionRuleCount(connectionId: number) {
    return rules.filter((rule) => rule.is_active && (rule.connection_ids || []).includes(connectionId)).length;
  }

  function connectionRuleNames(connectionId: number) {
    return rules
      .filter((rule) => (rule.connection_ids || []).includes(connectionId))
      .map((rule) => rule.name);
  }

  function connectionLabel(connectionId: number) {
    const connection = connections.find((item) => item.id === connectionId);
    return connection?.display_name || connection?.email || `Cuenta ${connectionId}`;
  }

  function ruleSummary(rule: AutomationRule) {
    if (rule.action_type === "ai_match") {
      const description = typeof rule.configuration.ai_description === "string" ? rule.configuration.ai_description : rule.name;
      return `IA: ${description}`;
    }

    return (
      [
        rule.sender_contains ? `Remitente: ${rule.sender_contains}` : null,
        rule.subject_contains ? `Asunto: ${rule.subject_contains}` : null,
        rule.has_attachment ? "Con adjuntos" : null,
      ]
        .filter(Boolean)
        .join(" | ") || "Sin condiciones especificas"
    );
  }

  function openOrganizationModal(organization?: Organization) {
    setEditingOrganization(organization ?? null);
    setOrganizationName(organization?.name ?? "");
    setIsOrganizationModalOpen(true);
  }

  function closeOrganizationModal() {
    setEditingOrganization(null);
    setOrganizationName("");
    setIsOrganizationModalOpen(false);
  }

  async function handleSaveOrganization(event: FormEvent) {
    event.preventDefault();
    if (!organizationName.trim()) {
      setMessage("El nombre de la organizacion es obligatorio.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const saved = editingOrganization
        ? await updateOrganization(token, editingOrganization.id, organizationName.trim())
        : await createOrganization(token, organizationName.trim());
      await refreshOrganizations();
      setSelectedOrganizationId(String(saved.id));
      localStorage.setItem("selected_organization_id", String(saved.id));
      closeOrganizationModal();
      await refreshConnections();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo guardar la organizacion");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectOrganization(organization: Organization) {
    setSelectedOrganizationId(String(organization.id));
    localStorage.setItem("selected_organization_id", String(organization.id));
    setSelectedConnectionId("all");
    setConnections([]);
    setMessages([]);
    setAttachments([]);
    setRules([]);
    setFollowups([]);
    setFollowupSummary(null);
    setEvents([]);
    await refreshConnections();
  }

  function returnToOrganizationSelector() {
    setSelectedOrganizationId("");
    localStorage.removeItem("selected_organization_id");
    setSelectedConnectionId("all");
    setConnections([]);
    setMessages([]);
    setAttachments([]);
    setRules([]);
    setFollowups([]);
    setFollowupSummary(null);
    setEvents([]);
  }

  async function handleDeleteOrganization(organization: Organization) {
    const confirmed = window.confirm(
      `Vas a eliminar "${organization.name}". Esta accion tambien elimina sus cuentas de correo, reglas, correos, adjuntos y eventos. ¿Quieres continuar?`,
    );
    if (!confirmed) return;

    setLoading(true);
    setMessage("");

    try {
      await deleteOrganization(token, organization.id);
      if (selectedOrganizationId === String(organization.id)) {
        setSelectedOrganizationId("");
        localStorage.removeItem("selected_organization_id");
        setConnections([]);
        setMessages([]);
        setAttachments([]);
        setRules([]);
        setFollowups([]);
        setFollowupSummary(null);
        setEvents([]);
      }
      await refreshOrganizations();
      setMessage("Organizacion eliminada.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo eliminar la organizacion");
    } finally {
      setLoading(false);
    }
  }

  function openBusinessHoursModal() {
    if (!selectedOrganization) return;
    setBusinessTimezone(selectedOrganization.business_timezone || "America/Bogota");
    const selectedDays = selectedOrganization.business_days?.length ? selectedOrganization.business_days : [1, 2, 3, 4, 5];
    setBusinessDays(selectedDays);
    setBusinessStartTime(selectedOrganization.business_start_time || "08:00");
    setBusinessEndTime(selectedOrganization.business_end_time || "18:00");
    setBusinessDayHours({
      ...defaultBusinessDayHours(selectedDays),
      ...(selectedOrganization.business_day_hours || {}),
    });
    setHolidayCountry(selectedOrganization.holiday_country || "CO");
    setBusinessHoursMessage("");
    setIsBusinessHoursModalOpen(true);
  }

  function closeBusinessHoursModal() {
    setIsBusinessHoursModalOpen(false);
    setBusinessHoursMessage("");
  }

  function toggleBusinessDay(day: number) {
    setBusinessDays((current) =>
      current.includes(day) ? current.filter((value) => value !== day) : [...current, day].sort((left, right) => left - right),
    );
    setBusinessDayHours((current) => ({
      ...current,
      [String(day)]: {
        ...(current[String(day)] || { uses_default: true, start_time: null, end_time: null }),
        enabled: !(current[String(day)]?.enabled ?? businessDays.includes(day)),
      },
    }));
  }

  function updateBusinessDayHour(day: number, patch: Partial<BusinessDayHoursState[string]>) {
    setBusinessDayHours((current) => {
      const existing = current[String(day)] || {
        enabled: businessDays.includes(day),
        uses_default: true,
        start_time: null,
        end_time: null,
      };
      return {
        ...current,
        [String(day)]: {
          ...existing,
          ...patch,
        },
      };
    });
  }

  async function handleSaveBusinessHours(event: FormEvent) {
    event.preventDefault();
    if (!selectedOrganization) return;
    const enabledDays = BUSINESS_DAY_OPTIONS.filter(([day]) => businessDayHours[String(day)]?.enabled).map(([day]) => day);
    if (!enabledDays.length) {
      setBusinessHoursMessage("Selecciona al menos un dia habil.");
      return;
    }
    if (businessStartTime >= businessEndTime) {
      setBusinessHoursMessage("La hora de inicio debe ser menor que la hora de fin.");
      return;
    }

    setLoading(true);
    setBusinessHoursMessage("");
    try {
      const saved = await updateOrganizationBusinessHours(token, selectedOrganization.id, {
        business_timezone: businessTimezone,
        business_days: enabledDays,
        business_start_time: businessStartTime,
        business_end_time: businessEndTime,
        business_day_hours: businessDayHours,
        holiday_country: holidayCountry.trim().toUpperCase() || "CO",
      });
      setOrganizations((current) => current.map((organization) => (organization.id === saved.id ? saved : organization)));
      setMessage("Horario de seguimiento actualizado.");
      closeBusinessHoursModal();
      await refreshOrganizations();
    } catch (error) {
      setBusinessHoursMessage(error instanceof Error ? error.message : "No se pudo actualizar el horario de seguimiento");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const response = await login(email, password);
      setToken(response.access_token);
      setUser(response.user);
      localStorage.setItem("access_token", response.access_token);
      localStorage.setItem("user", JSON.stringify(response.user));
      if (response.user.role === "super_root" || response.user.platform_role === "super_root") {
        window.history.replaceState(null, "", "/master");
        setRootUsers(await listRootUsers(response.access_token));
        setOrganizations([]);
        setOrganizationsLoaded(true);
      } else {
        window.history.replaceState(null, "", "/app/organizaciones");
        await refreshOrganizations(response.access_token);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo iniciar sesion");
    } finally {
      setLoading(false);
    }
  }

  async function handleStartGoogleOAuth(event?: FormEvent) {
    event?.preventDefault();
    if (!newAccountName.trim()) {
      setAccountModalMessage("Escribe un nombre para identificar la cuenta.");
      return;
    }
    if (!newAccountUserEmail.trim()) {
      setAccountModalMessage("Escribe el usuario que entrara a vincular esta cuenta.");
      return;
    }
    if (newAccountPassword.length < 6) {
      setAccountModalMessage("La contrasena debe tener al menos 6 caracteres.");
      return;
    }

    setLoading(true);
    setAccountModalMessage("");

    try {
      const account = await createAccountAccess(token, {
        display_name: newAccountName.trim(),
        purpose: newAccountPurpose.trim(),
        user_email: newAccountUserEmail.trim(),
        password: newAccountPassword,
      });
      const response = await startGoogleOAuth(token, {
        connection_id: account.id,
      });
      window.location.href = response.authorization_url;
    } catch (error) {
      setAccountModalMessage(error instanceof Error ? error.message : "No se pudo iniciar OAuth con Google");
      setLoading(false);
    }
  }

  function openAccountModal(connection?: GoogleConnection) {
    setEditingAccount(connection || null);
    setNewAccountName(connection?.display_name || "");
    setNewAccountPurpose(connection?.purpose || "");
    setNewAccountUserEmail(connection?.assigned_user_email || "");
    setNewAccountPassword("");
    setAccountModalMessage("");
    setIsAccountModalOpen(true);
  }

  async function handleSaveEditedAccount(event?: FormEvent, linkAfterSave = false) {
    event?.preventDefault();
    if (!editingAccount) return;
    if (!newAccountName.trim()) {
      setAccountModalMessage("Escribe un nombre para identificar la cuenta.");
      return;
    }
    if (!newAccountUserEmail.trim()) {
      setAccountModalMessage("Escribe el usuario de acceso.");
      return;
    }
    if (newAccountPassword && newAccountPassword.length < 6) {
      setAccountModalMessage("La contrasena debe tener al menos 6 caracteres.");
      return;
    }

    setLoading(true);
    setAccountModalMessage("");
    try {
      const saved = await updateConnection(token, editingAccount.id, {
        display_name: newAccountName.trim(),
        purpose: newAccountPurpose.trim(),
        user_email: newAccountUserEmail.trim(),
        password: newAccountPassword || undefined,
      });
      if (linkAfterSave) {
        const response = await startGoogleOAuth(token, { connection_id: saved.id });
        window.location.href = response.authorization_url;
        return;
      }
      resetAccountModal();
      setMessage("Cuenta actualizada.");
      await refreshConnections();
    } catch (error) {
      setAccountModalMessage(error instanceof Error ? error.message : "No se pudo actualizar la cuenta");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateAccountAccess() {
    if (!newAccountName.trim()) {
      setAccountModalMessage("Escribe un nombre para identificar la cuenta.");
      return;
    }
    if (!newAccountUserEmail.trim()) {
      setAccountModalMessage("Escribe el usuario de acceso.");
      return;
    }
    if (newAccountPassword.length < 6) {
      setAccountModalMessage("La contrasena debe tener al menos 6 caracteres.");
      return;
    }

    setLoading(true);
    setAccountModalMessage("");
    try {
      await createAccountAccess(token, {
        display_name: newAccountName.trim(),
        purpose: newAccountPurpose.trim(),
        user_email: newAccountUserEmail.trim(),
        password: newAccountPassword,
      });
      resetAccountModal();
      setMessage("Acceso creado. El usuario ya puede ingresar y vincular su cuenta Google.");
      await refreshConnections();
    } catch (error) {
      setAccountModalMessage(error instanceof Error ? error.message : "No se pudo crear el acceso");
    } finally {
      setLoading(false);
    }
  }

  async function handleLinkSelectedAccount(connectionId?: number) {
    const targetId = connectionId || selectedConnection?.id;
    if (!targetId) return;
    setLoading(true);
    setMessage("");
    try {
      const response = await startGoogleOAuth(token, { connection_id: targetId });
      window.location.href = response.authorization_url;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo iniciar la vinculacion con Google");
      setLoading(false);
    }
  }

  function openProfileModal() {
    setProfileName(activeUser.name || "");
    setProfileEmail(activeUser.email || "");
    setProfilePassword("");
    setProfileMessage("");
    setIsProfileModalOpen(true);
  }

  async function handleSaveProfile(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setProfileMessage("");
    try {
      const updated = await updateProfile(token, {
        name: profileName.trim(),
        email: profileEmail.trim(),
        password: profilePassword || undefined,
      });
      const nextUser = { ...activeUser, ...updated };
      setUser(nextUser);
      localStorage.setItem("user", JSON.stringify(nextUser));
      setIsProfileModalOpen(false);
      setMessage("Perfil actualizado.");
    } catch (error) {
      setProfileMessage(error instanceof Error ? error.message : "No se pudo actualizar el perfil");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateRootUser(event: FormEvent) {
    event.preventDefault();
    if (!rootUserName.trim() || !rootUserEmail.trim() || !rootUserPassword) {
      setRootUserMessage("Completa nombre, correo y contrasena.");
      return;
    }

    setLoading(true);
    setRootUserMessage("");
    try {
      await createRootUser(token, {
        name: rootUserName.trim(),
        email: rootUserEmail.trim(),
        password: rootUserPassword,
      });
      setRootUserName("");
      setRootUserEmail("");
      setRootUserPassword("");
      setRootUserMessage("Usuario root creado.");
      await refreshRootUsers();
    } catch (error) {
      setRootUserMessage(error instanceof Error ? error.message : "No se pudo crear el usuario root");
    } finally {
      setLoading(false);
    }
  }

  function resetAccountModal() {
    setEditingAccount(null);
    setNewAccountName("");
    setNewAccountPurpose("");
    setNewAccountUserEmail("");
    setNewAccountPassword("");
    setAccountModalMessage("");
    setIsAccountModalOpen(false);
  }

  async function handleDeleteConnection(id: number) {
    const connection = connections.find((item) => item.id === id);
    const confirmed = window.confirm(
      `Vas a desconectar ${connection?.email ?? "esta cuenta"} y eliminar sus datos sincronizados: tokens de Google, correos, adjuntos, eventos y seguimientos asociados. Esta accion no se puede deshacer.`
    );
    if (!confirmed) return;

    setLoading(true);
    setMessage("");

    try {
      await deleteConnection(token, id);
      setMessage("Cuenta desconectada y datos de Gmail eliminados.");
      if (selectedConnectionId === String(id)) {
        setSelectedConnectionId("all");
      }
      await refreshConnections();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo desconectar la cuenta");
    } finally {
      setLoading(false);
    }
  }

  async function handleSyncConnection(id: number) {
    if (isOwner && connectionRuleCount(id) === 0) {
      setMessage("Antes de sincronizar, la cuenta debe tener al menos una regla activa asociada.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const result = await syncConnection(token, id);
      setMessage(
        `Sincronizacion lista: ${result.fetched} leidos, ${result.stored} nuevos, ${result.attachments_stored} adjuntos guardados.`,
      );
      await refreshConnections();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo sincronizar Gmail");
    } finally {
      setLoading(false);
    }
  }

  function openWatchModal(connection: GoogleConnection) {
    if (isWatchActive(connection)) {
      setMessage(`Monitor ya activo. Expira: ${formatDate(connection.watch_expiration_at)}.`);
      return;
    }

    setWatchConnectionTarget(connection);
    setWatchDuration("1m");
    setCustomWatchUntil(defaultWatchUntil());
    setWatchModalMessage("");
  }

  function closeWatchModal() {
    setWatchConnectionTarget(null);
    setWatchModalMessage("");
  }

  async function handleWatchConnection(id: number, activeUntil: string) {
    const connection = connections.find((item) => item.id === id);
    if (connection && isWatchActive(connection)) {
      setMessage(`Monitor ya activo. Expira: ${formatDate(connection.watch_expiration_at)}.`);
      return;
    }
    if (!activeUntil || new Date(activeUntil).getTime() <= Date.now()) {
      setWatchModalMessage("Selecciona una fecha futura para la vigencia del monitor.");
      return;
    }

    setLoading(true);
    setWatchModalMessage("");

    try {
      const result = await watchConnection(token, id, toIsoFromLocalInput(activeUntil));
      setMessage(`Monitor activo hasta ${formatDate(result.desired_until)}.`);
      closeWatchModal();
      await refreshConnections();
    } catch (error) {
      setWatchModalMessage(error instanceof Error ? error.message : "No se pudo registrar el monitor Gmail");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitWatch(event: FormEvent) {
    event.preventDefault();
    if (!watchConnectionTarget) return;
    await handleWatchConnection(
      watchConnectionTarget.id,
      watchDateForDuration(watchDuration, customWatchUntil),
    );
  }

  async function handleStopWatchConnection(id: number) {
    setLoading(true);
    setMessage("");

    try {
      await stopWatchConnection(token, id);
      setMessage("Monitor inactivado.");
      await refreshConnections();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo inactivar el monitor Gmail");
    } finally {
      setLoading(false);
    }
  }

  function openWhatsAppModal(connection: GoogleConnection) {
    setWhatsAppConnectionTarget(connection);
    setWhatsAppNumber(connection.whatsapp_number || "");
    setWhatsAppNotificationsEnabled(connection.whatsapp_notifications_enabled);
    setWhatsAppNotifyNewEmail(connection.whatsapp_notify_new_email);
    setWhatsAppNotifyFollowupOverdue(connection.whatsapp_notify_followup_overdue);
    setWhatsAppNotifyFollowupWarning(connection.whatsapp_notify_followup_warning);
    setWhatsAppNotifyFollowupLate(connection.whatsapp_notify_followup_late);
    setWhatsAppNotifyFollowupResponded(connection.whatsapp_notify_followup_responded);
    setWhatsAppModalMessage("");
  }

  function closeWhatsAppModal() {
    setWhatsAppConnectionTarget(null);
    setWhatsAppModalMessage("");
  }

  function setAllWhatsAppNotifications(value: boolean) {
    setWhatsAppNotificationsEnabled(value);
    setWhatsAppNotifyNewEmail(value);
    setWhatsAppNotifyFollowupOverdue(value);
    setWhatsAppNotifyFollowupWarning(value);
    setWhatsAppNotifyFollowupLate(value);
    setWhatsAppNotifyFollowupResponded(value);
  }

  async function handleSaveWhatsAppPreferences() {
    if (!whatsAppConnectionTarget) return;
    setLoading(true);
    setWhatsAppModalMessage("");
    try {
      await updateWhatsAppPreferences(token, whatsAppConnectionTarget.id, {
        notifications_enabled: whatsAppNotificationsEnabled,
        notify_new_email: whatsAppNotifyNewEmail,
        notify_followup_overdue: whatsAppNotifyFollowupOverdue,
        notify_followup_warning: whatsAppNotifyFollowupWarning,
        notify_followup_late: whatsAppNotifyFollowupLate,
        notify_followup_responded: whatsAppNotifyFollowupResponded,
      });
      setMessage("Preferencias de WhatsApp actualizadas.");
      closeWhatsAppModal();
      await refreshConnections();
    } catch (error) {
      setWhatsAppModalMessage(error instanceof Error ? error.message : "No se pudieron guardar las preferencias");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitWhatsApp(event: FormEvent) {
    event.preventDefault();
    if (!whatsAppConnectionTarget) return;
    if (!whatsAppNumber.trim()) {
      setWhatsAppModalMessage("Escribe el numero de WhatsApp que quieres asociar.");
      return;
    }

    setLoading(true);
    setWhatsAppModalMessage("");

    try {
      const result = await startWhatsAppSetup(token, whatsAppConnectionTarget.id, whatsAppNumber.trim());
      window.open(result.whatsapp_url, "_blank", "noopener,noreferrer");
      setMessage("Se abrio WhatsApp Web. Envia el mensaje prellenado para confirmar la vinculacion.");
      closeWhatsAppModal();
      await refreshConnections();
    } catch (error) {
      setWhatsAppModalMessage(error instanceof Error ? error.message : "No se pudo iniciar la configuracion de WhatsApp");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveConnection() {
    if (!selectedConnection) return;
    setLoading(true);
    setMessage("");

    try {
      await updateConnection(token, selectedConnection.id, {
        display_name: editName,
        purpose: editPurpose,
      });
      setMessage("Cuenta actualizada.");
      setIsEditingConnection(false);
      await refreshConnections();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo actualizar la cuenta");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveRule(event: FormEvent) {
    event.preventDefault();
    if (ruleConnectionIds.length === 0) {
      setRuleModalMessage("Selecciona al menos una cuenta para asociar la regla.");
      return;
    }
    setLoading(true);
    setRuleModalMessage("");

    try {
      const payload = {
        name: ruleName,
        connection_ids: ruleConnectionIds,
        sender_contains: ruleSender || undefined,
        subject_contains: ruleSubject || undefined,
        has_attachment: ruleHasAttachment,
        action_type: "mark_detected",
        configuration: {},
        is_active: editingRule?.is_active ?? true,
      };
      if (editingRule) {
        await updateRule(token, editingRule.id, payload);
        setMessage("Regla actualizada.");
      } else {
        await createRule(token, payload);
        setMessage("Regla creada.");
      }
      closeRuleModal();
      await refreshConnections();
    } catch (error) {
      setRuleModalMessage(error instanceof Error ? error.message : "No se pudo guardar la regla");
    } finally {
      setLoading(false);
    }
  }

  async function handleDraftRule() {
    if (!ruleText.trim()) {
      setRuleModalMessage("Describe que correos quieres detectar.");
      return;
    }
    if (ruleConnectionIds.length === 0) {
      setRuleModalMessage("Selecciona al menos una cuenta antes de crear la regla con IA.");
      return;
    }
    setLoading(true);
    setRuleModalMessage("");

    try {
      const normalizedText = ruleText.trim();
      const payload = {
        name: normalizedText.length > 70 ? `${normalizedText.slice(0, 67)}...` : normalizedText,
        action_type: "ai_match",
        configuration: {
          ai_description: normalizedText,
          matching_mode: "semantic_email_evaluation",
        },
        connection_ids: ruleConnectionIds,
        sender_contains: null,
        subject_contains: null,
        has_attachment: null,
        is_active: editingRule?.is_active ?? true,
      };
      if (editingRule) {
        await updateRule(token, editingRule.id, payload);
        setMessage("Regla con IA actualizada.");
      } else {
        await createRule(token, payload);
        setMessage("Regla con IA creada.");
      }
      closeRuleModal();
      await refreshConnections();
    } catch (error) {
      setRuleModalMessage(error instanceof Error ? error.message : "No se pudo guardar la regla con IA");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteRule(id: number) {
    setLoading(true);
    setMessage("");

    try {
      await deleteRule(token, id);
      await refreshConnections();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo eliminar la regla");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    clearSession();
    window.history.replaceState(null, "", "/login");
  }

  function selectConnection(id: string) {
    setSelectedConnectionId(id);
    setActiveMainTab("accounts");
    setActivePanel("emails");
  }

  function showAccountsList() {
    setActiveMainTab("accounts");
    setSelectedConnectionId("all");
    setActivePanel("emails");
  }

  function openRuleModal() {
    setEditingRule(null);
    setRuleConnectionIds(selectedConnection ? [selectedConnection.id] : []);
    setRuleModalMessage("");
    setRuleName("Facturas con adjuntos");
    setRuleSender("");
    setRuleSubject("factura");
    setRuleHasAttachment(true);
    setRuleText("Detecta facturas o invoices que tengan PDF adjunto");
    setRuleMode("ai");
    setIsRuleModalOpen(true);
  }

  function openEditRuleModal(rule: AutomationRule) {
    const description = typeof rule.configuration.ai_description === "string" ? rule.configuration.ai_description : rule.name;
    setEditingRule(rule);
    setRuleConnectionIds(rule.connection_ids || []);
    setRuleModalMessage("");
    setRuleMode(rule.action_type === "ai_match" ? "ai" : "manual");
    setRuleName(rule.name);
    setRuleSender(rule.sender_contains || "");
    setRuleSubject(rule.subject_contains || "");
    setRuleHasAttachment(Boolean(rule.has_attachment));
    setRuleText(description);
    setIsRuleModalOpen(true);
  }

  function closeRuleModal() {
    setEditingRule(null);
    setRuleModalMessage("");
    setIsRuleModalOpen(false);
  }

  function toggleRuleConnection(connectionId: number) {
    setRuleConnectionIds((current) =>
      current.includes(connectionId) ? current.filter((id) => id !== connectionId) : [...current, connectionId],
    );
  }

  function openRuleWhatsAppModal(rule: AutomationRule) {
    setRuleWhatsAppTarget(rule);
    setRuleWhatsAppConnectionIds(rule.whatsapp_enabled_connection_ids || []);
    setRuleWhatsAppMessage("");
  }

  function closeRuleWhatsAppModal() {
    setRuleWhatsAppTarget(null);
    setRuleWhatsAppMessage("");
  }

  function toggleRuleWhatsAppConnection(connectionId: number) {
    setRuleWhatsAppConnectionIds((current) =>
      current.includes(connectionId) ? current.filter((id) => id !== connectionId) : [...current, connectionId],
    );
  }

  async function handleSaveRuleWhatsAppNotifications(event: FormEvent) {
    event.preventDefault();
    if (!ruleWhatsAppTarget) return;

    setLoading(true);
    setRuleWhatsAppMessage("");

    try {
      await updateRuleWhatsAppNotifications(token, ruleWhatsAppTarget.id, ruleWhatsAppConnectionIds);
      setMessage("Notificaciones WhatsApp actualizadas.");
      closeRuleWhatsAppModal();
      await refreshConnections();
    } catch (error) {
      setRuleWhatsAppMessage(error instanceof Error ? error.message : "No se pudieron actualizar las notificaciones");
    } finally {
      setLoading(false);
    }
  }

  function emptyMapping(target = ""): ApiMapping {
    return { target, source_type: "field", source_key: "subject", literal: "" };
  }

  function resetRuleApiForm() {
    setEditingRuleApi(null);
    setRuleApiName("Nueva integracion");
    setRuleApiMethod("POST");
    setRuleApiUrl("");
    setRuleApiActive(true);
    setRuleApiTimeout("15");
    setRuleApiHeaders([]);
    setRuleApiQueryParams([]);
    setRuleApiBodyFields([emptyMapping("subject")]);
    setRuleApiMessage("");
    setRuleApiMessageTone("info");
  }

  async function openRuleApiModal(rule: AutomationRule) {
    setRuleApiTarget(rule);
    setRuleApiMessage("");
    resetRuleApiForm();
    try {
      const apiConnections = await listRuleApiConnections(token, rule.id);
      setRuleApiConnections(apiConnections);
      if (apiConnections[0]) {
        selectRuleApi(apiConnections[0]);
      }
    } catch (error) {
      setRuleApiMessage(error instanceof Error ? error.message : "No se pudieron cargar las APIs");
      setRuleApiMessageTone("error");
    }
  }

  function closeRuleApiModal() {
    setRuleApiTarget(null);
    setRuleApiConnections([]);
    resetRuleApiForm();
  }

  function selectRuleApi(apiConnection: RuleApiConnection) {
    setEditingRuleApi(apiConnection);
    setRuleApiName(apiConnection.name);
    setRuleApiMethod(apiConnection.method);
    setRuleApiUrl(apiConnection.url);
    setRuleApiActive(apiConnection.is_active);
    setRuleApiTimeout(String(apiConnection.timeout_seconds || 15));
    setRuleApiHeaders(apiConnection.headers || []);
    setRuleApiQueryParams(apiConnection.query_params || []);
    setRuleApiBodyFields(apiConnection.body_fields || []);
    setRuleApiMessage("");
    setRuleApiMessageTone("info");
  }

  function apiMappingState(group: MappingGroup) {
    if (group === "headers") return [ruleApiHeaders, setRuleApiHeaders] as const;
    if (group === "query_params") return [ruleApiQueryParams, setRuleApiQueryParams] as const;
    return [ruleApiBodyFields, setRuleApiBodyFields] as const;
  }

  function addApiMapping(group: MappingGroup) {
    const [items, setItems] = apiMappingState(group);
    setItems([...items, emptyMapping()]);
  }

  function updateApiMapping(group: MappingGroup, index: number, patch: Partial<ApiMapping>) {
    const [items, setItems] = apiMappingState(group);
    setItems(items.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)));
  }

  function removeApiMapping(group: MappingGroup, index: number) {
    const [items, setItems] = apiMappingState(group);
    setItems(items.filter((_, itemIndex) => itemIndex !== index));
  }

  function validateRuleApiForm() {
    const timeout = Number(ruleApiTimeout);
    if (!ruleApiName.trim()) {
      setRuleApiMessage("Escribe un nombre para identificar la API.");
      setRuleApiMessageTone("error");
      return null;
    }
    if (!ruleApiUrl.trim()) {
      setRuleApiMessage("Configura la URL de la API.");
      setRuleApiMessageTone("error");
      return null;
    }
    if (!Number.isFinite(timeout) || timeout < 1 || timeout > 60) {
      setRuleApiMessage("El timeout debe estar entre 1 y 60 segundos.");
      setRuleApiMessageTone("error");
      return null;
    }

    return {
      name: ruleApiName,
      method: ruleApiMethod,
      url: ruleApiUrl,
      headers: ruleApiHeaders,
      query_params: ruleApiQueryParams,
      body_fields: ruleApiBodyFields,
      timeout_seconds: timeout,
      is_active: ruleApiActive,
    };
  }

  async function runRuleApiTest(payload: ReturnType<typeof validateRuleApiForm>, options: { beforeSave?: boolean } = {}) {
    if (!ruleApiTarget || !payload) return false;
    setRuleApiTesting(true);
    setRuleApiMessage(options.beforeSave ? "Probando API antes de guardar..." : "Probando API...");
    setRuleApiMessageTone("info");
    try {
      const result = await testRuleApiConnection(token, ruleApiTarget.id, payload);
      const statusText = result.status_code ? ` Estado ${result.status_code}.` : "";
      const previewText = result.response_preview ? ` Respuesta: ${result.response_preview}` : "";
      setRuleApiMessage(`${result.message}${statusText} Tiempo: ${result.elapsed_ms} ms.${previewText}`);
      setRuleApiMessageTone(result.ok ? "success" : "error");
      return result.ok;
    } catch (error) {
      setRuleApiMessage(error instanceof Error ? error.message : "No se pudo probar la API");
      setRuleApiMessageTone("error");
      return false;
    } finally {
      setRuleApiTesting(false);
    }
  }

  async function handleTestRuleApi() {
    const payload = validateRuleApiForm();
    await runRuleApiTest(payload);
  }

  async function handleSaveRuleApi(event: FormEvent) {
    event.preventDefault();
    if (!ruleApiTarget) return;
    const payload = validateRuleApiForm();
    if (!payload) return;

    setLoading(true);
    try {
      const testPassed = await runRuleApiTest(payload, { beforeSave: true });
      if (!testPassed) return;
      if (editingRuleApi) {
        await updateRuleApiConnection(token, editingRuleApi.id, payload);
      } else {
        await createRuleApiConnection(token, ruleApiTarget.id, payload);
      }
      const apiConnections = await listRuleApiConnections(token, ruleApiTarget.id);
      setRuleApiConnections(apiConnections);
      await refreshConnections();
      setRuleApiMessage("API probada y guardada.");
      setRuleApiMessageTone("success");
    } catch (error) {
      setRuleApiMessage(error instanceof Error ? error.message : "No se pudo guardar la API");
      setRuleApiMessageTone("error");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteRuleApi() {
    if (!ruleApiTarget || !editingRuleApi) return;
    const confirmed = window.confirm(`Eliminar la API "${editingRuleApi.name}" de esta regla?`);
    if (!confirmed) return;
    setLoading(true);
    setRuleApiMessage("");
    try {
      await deleteRuleApiConnection(token, editingRuleApi.id);
      const apiConnections = await listRuleApiConnections(token, ruleApiTarget.id);
      setRuleApiConnections(apiConnections);
      resetRuleApiForm();
      await refreshConnections();
      setRuleApiMessage("API eliminada.");
      setRuleApiMessageTone("success");
    } catch (error) {
      setRuleApiMessage(error instanceof Error ? error.message : "No se pudo eliminar la API");
      setRuleApiMessageTone("error");
    } finally {
      setLoading(false);
    }
  }

  function renderApiMappings(title: string, group: MappingGroup, description: string) {
    const [items] = apiMappingState(group);
    return (
      <div className="api-mapping-section">
        <div className="mapping-section-header">
          <div>
            <strong>{title}</strong>
            <span>{description}</span>
          </div>
          <button className="secondary-button" onClick={() => addApiMapping(group)} type="button">
            <Plus size={16} />
            Campo
          </button>
        </div>
        <div className="mapping-list">
          {items.map((item, index) => (
            <div className="mapping-row" key={`${group}-${index}`}>
              <label>
                Campo API
                <input
                  value={item.target}
                  onChange={(event) => updateApiMapping(group, index, { target: event.target.value })}
                  placeholder="customer.email"
                />
              </label>
              <label>
                Fuente
                <select
                  value={item.source_type}
                  onChange={(event) =>
                    updateApiMapping(group, index, {
                      source_type: event.target.value as ApiMapping["source_type"],
                    })
                  }
                >
                  <option value="field">Dato del correo</option>
                  <option value="literal">Valor escrito</option>
                </select>
              </label>
              {item.source_type === "literal" ? (
                <label>
                  Valor
                  <input
                    value={item.literal || ""}
                    onChange={(event) => updateApiMapping(group, index, { literal: event.target.value })}
                    placeholder="Valor fijo"
                  />
                </label>
              ) : (
                <label>
                  Dato disponible
                  <select
                    value={item.source_key || "subject"}
                    onChange={(event) => updateApiMapping(group, index, { source_key: event.target.value })}
                  >
                    {API_SOURCE_OPTIONS.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <button className="icon-button danger" onClick={() => removeApiMapping(group, index)} title="Quitar campo" type="button">
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          {items.length === 0 && <div className="empty compact-empty">Sin campos configurados.</div>}
        </div>
      </div>
    );
  }

  function openRuleFollowupModal(rule: AutomationRule) {
    const config = followupConfig(rule);
    setRuleFollowupTarget(rule);
    setRuleFollowupEnabled(config.enabled);
    setRuleFollowupHours(String(Math.max(1, Math.round(config.response_time_minutes / 60))));
    setRuleFollowupNotifyWhatsApp(config.notify_whatsapp_on_overdue);
    setRuleFollowupWarnMinutes(config.warn_before_minutes ? String(config.warn_before_minutes) : "");
    setRuleFollowupEscalationMinutes(config.escalation_minutes ? String(config.escalation_minutes) : "");
    setRuleFollowupMessage("");
  }

  function closeRuleFollowupModal() {
    setRuleFollowupTarget(null);
    setRuleFollowupMessage("");
  }

  async function handleSaveRuleFollowup(event: FormEvent) {
    event.preventDefault();
    if (!ruleFollowupTarget) return;
    const hours = Number(ruleFollowupHours);
    if (!Number.isFinite(hours) || hours <= 0) {
      setRuleFollowupMessage("Define un tiempo maximo de respuesta valido.");
      return;
    }

    setLoading(true);
    setRuleFollowupMessage("");
    try {
      await updateRuleFollowup(token, ruleFollowupTarget.id, {
        enabled: ruleFollowupEnabled,
        response_time_minutes: Math.round(hours * 60),
        notify_whatsapp_on_overdue: ruleFollowupNotifyWhatsApp,
        warn_before_minutes: ruleFollowupWarnMinutes ? Number(ruleFollowupWarnMinutes) : null,
        escalation_minutes: ruleFollowupEscalationMinutes ? Number(ruleFollowupEscalationMinutes) : null,
      });
      setMessage("Seguimiento de regla actualizado.");
      closeRuleFollowupModal();
      await refreshConnections();
    } catch (error) {
      setRuleFollowupMessage(error instanceof Error ? error.message : "No se pudo actualizar el seguimiento");
    } finally {
      setLoading(false);
    }
  }

  function openAccountFollowupModal(connection: GoogleConnection) {
    setAccountFollowupTarget(connection);
    setAccountFollowupEnabled(connection.followup_enabled);
    setAccountFollowupHours(String(Math.max(1, Math.round(connection.followup_response_time_minutes / 60))));
    setAccountFollowupNotifyWhatsApp(connection.followup_notify_whatsapp_on_overdue);
    setAccountFollowupWarnMinutes(connection.followup_warn_before_minutes ? String(connection.followup_warn_before_minutes) : "");
    setAccountFollowupEscalationMinutes(connection.followup_escalation_minutes ? String(connection.followup_escalation_minutes) : "");
    setAccountFollowupMessage("");
  }

  function closeAccountFollowupModal() {
    setAccountFollowupTarget(null);
    setAccountFollowupWarnMinutes("");
    setAccountFollowupEscalationMinutes("");
    setAccountFollowupMessage("");
  }

  async function handleSaveAccountFollowup(event: FormEvent) {
    event.preventDefault();
    if (!accountFollowupTarget) return;
    const hours = Number(accountFollowupHours);
    if (!Number.isFinite(hours) || hours <= 0) {
      setAccountFollowupMessage("Define un tiempo maximo de respuesta valido.");
      return;
    }

    setLoading(true);
    setAccountFollowupMessage("");
    try {
      await updateConnectionFollowup(token, accountFollowupTarget.id, {
        enabled: accountFollowupEnabled,
        response_time_minutes: Math.round(hours * 60),
        notify_whatsapp_on_overdue: accountFollowupNotifyWhatsApp,
        warn_before_minutes: accountFollowupWarnMinutes ? Number(accountFollowupWarnMinutes) : null,
        escalation_minutes: accountFollowupEscalationMinutes ? Number(accountFollowupEscalationMinutes) : null,
      });
      setMessage("Seguimiento por cuenta actualizado.");
      closeAccountFollowupModal();
      await refreshConnections();
    } catch (error) {
      setAccountFollowupMessage(error instanceof Error ? error.message : "No se pudo actualizar el seguimiento de cuenta");
    } finally {
      setLoading(false);
    }
  }

  function openManualFollowupModal(emailMessage: EmailMessage) {
    setManualFollowupTarget(emailMessage);
    setManualFollowupHours("2");
    setManualFollowupNotifyWhatsApp(false);
    setManualFollowupWarnMinutes("");
    setManualFollowupEscalationMinutes("");
    setManualFollowupMessage("");
  }

  function closeManualFollowupModal() {
    setManualFollowupTarget(null);
    setManualFollowupWarnMinutes("");
    setManualFollowupEscalationMinutes("");
    setManualFollowupMessage("");
  }

  async function handleCreateManualFollowup(event: FormEvent) {
    event.preventDefault();
    if (!manualFollowupTarget) return;
    const hours = Number(manualFollowupHours);
    if (!Number.isFinite(hours) || hours <= 0) {
      setManualFollowupMessage("Define un tiempo maximo de respuesta valido.");
      return;
    }

    setLoading(true);
    setManualFollowupMessage("");
    try {
      await createManualFollowup(token, {
        email_message_id: manualFollowupTarget.id,
        response_time_minutes: Math.round(hours * 60),
        notify_whatsapp_on_overdue: manualFollowupNotifyWhatsApp,
        warn_before_minutes: manualFollowupWarnMinutes ? Number(manualFollowupWarnMinutes) : null,
        escalation_minutes: manualFollowupEscalationMinutes ? Number(manualFollowupEscalationMinutes) : null,
      });
      setMessage("Seguimiento creado para el correo.");
      closeManualFollowupModal();
      await refreshConnections();
      setActivePanel("followups");
    } catch (error) {
      setManualFollowupMessage(error instanceof Error ? error.message : "No se pudo crear el seguimiento");
    } finally {
      setLoading(false);
    }
  }

  async function handleEvaluateFollowups() {
    setLoading(true);
    setMessage("");
    try {
      const result = await evaluateFollowups(token, selectedConnection?.id);
      setMessage(`Seguimientos evaluados: ${result.evaluated}. Respondidos: ${result.responded}. Vencidos: ${result.overdue}.`);
      await refreshConnections();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudieron evaluar los seguimientos");
    } finally {
      setLoading(false);
    }
  }

  const themeSwitcher = (
    <ThemeSwitcher
      isOpen={isThemeMenuOpen}
      onChange={(nextTheme) => {
        setThemePalette(nextTheme);
        setIsThemeMenuOpen(false);
      }}
      onToggle={() => setIsThemeMenuOpen((current) => !current)}
      value={themePalette}
    />
  );

  if (!isLoggedIn && publicPage) {
    return <PublicPageView page={publicPage} themeSwitcher={themeSwitcher} />;
  }

  if (!isLoggedIn) {
    return (
      <main className="auth-shell">
        <div className="auth-toolbar">{themeSwitcher}</div>
        <section className="auth-panel">
          <div className="auth-brand">
            <img className="auth-logo" src="/logo-email-assitance-blue.png" alt="Email Assistance" />
            <div>
              <h1>Iniciar sesion</h1>
              <p className="muted">Accede a tu centro de procesamiento de correos.</p>
            </div>
          </div>

          <form onSubmit={handleLogin} className="form">
            <label>
              Correo
              <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" />
            </label>
            <label>
              Contrasena
              <span className="password-field">
                <input value={password} onChange={(event) => setPassword(event.target.value)} type={showPassword ? "text" : "password"} />
                <button
                  aria-label={showPassword ? "Ocultar contrasena" : "Mostrar contrasena"}
                  className="password-toggle"
                  onClick={() => setShowPassword((current) => !current)}
                  title={showPassword ? "Ocultar contrasena" : "Mostrar contrasena"}
                  type="button"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </label>
            {message && <p className="message">{message}</p>}
            <button disabled={loading} type="submit">
              <Link2 size={18} />
              Iniciar sesion
            </button>
          </form>
        </section>
      </main>
    );
  }

  const activeUser = user!;
  const profileModal = isProfileModalOpen ? (
    <div className="modal-backdrop" role="presentation">
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="profile-modal-title">
        <div className="modal-header">
          <div>
            <p className="eyebrow">Mi perfil</p>
            <h2 id="profile-modal-title">Datos personales y acceso</h2>
          </div>
          <button className="icon-button" onClick={() => setIsProfileModalOpen(false)} title="Cerrar" type="button">
            <X size={18} />
          </button>
        </div>
        <form className="modal-form" onSubmit={handleSaveProfile}>
          {profileMessage && <p className="message modal-message">{profileMessage}</p>}
          <label>
            Nombre
            <input value={profileName} onChange={(event) => setProfileName(event.target.value)} placeholder="Tu nombre" />
          </label>
          <label>
            Correo de acceso
            <input value={profileEmail} onChange={(event) => setProfileEmail(event.target.value)} placeholder="correo@empresa.com" type="email" />
          </label>
          <label>
            Nueva contrasena
            <input
              value={profilePassword}
              onChange={(event) => setProfilePassword(event.target.value)}
              placeholder="Dejalo vacio para conservarla"
              type="password"
            />
          </label>
          <button disabled={loading} type="submit">
            <UserRound size={18} />
            Guardar perfil
          </button>
        </form>
      </section>
    </div>
  ) : null;

  if (isSuperRoot) {
    return (
      <main className="app-shell organization-shell">
        <header className="topbar">
          <BrandTitle
            title="Panel master"
            subtitle="Crea usuarios root. Cada root administra un espacio aislado con sus propias organizaciones."
          />
          <div className="session">
            <span>{activeUser.email}</span>
            <button className="icon-button" onClick={openProfileModal} title="Mi perfil" type="button">
              <UserRound size={18} />
            </button>
            {themeSwitcher}
            <button className="icon-button" onClick={handleLogout} title="Cerrar sesion">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        <section className="master-layout">
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Usuarios root</p>
                <h2>Crear nuevo root</h2>
                <p className="muted">Este usuario podra crear sus organizaciones, cuentas, reglas y configuraciones.</p>
              </div>
            </div>
            <form className="modal-form" onSubmit={handleCreateRootUser}>
              {rootUserMessage && <p className="message modal-message">{rootUserMessage}</p>}
              <label>
                Nombre
                <input value={rootUserName} onChange={(event) => setRootUserName(event.target.value)} placeholder="Administrador cliente" />
              </label>
              <label>
                Correo
                <input value={rootUserEmail} onChange={(event) => setRootUserEmail(event.target.value)} placeholder="admin@cliente.com" type="email" />
              </label>
              <label>
                Contrasena
                <input value={rootUserPassword} onChange={(event) => setRootUserPassword(event.target.value)} placeholder="Clave inicial" type="password" />
              </label>
              <button disabled={loading} type="submit">
                <UserRound size={18} />
                Crear root
              </button>
            </form>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Roots activos</p>
                <h2>Usuarios administradores</h2>
              </div>
            </div>
            <div className="rules-table-list">
              {rootUsers.map((rootUser) => (
                <article className="rule-row" key={rootUser.id}>
                  <div>
                    <strong>{rootUser.name}</strong>
                    <span>{rootUser.email}</span>
                  </div>
                  <span className="status">{rootUser.platform_role}</span>
                </article>
              ))}
              {rootUsers.length === 0 && <div className="empty compact-empty">Aun no hay usuarios root creados.</div>}
            </div>
          </section>
        </section>
        {profileModal}
      </main>
    );
  }

  if (!selectedOrganization) {
    return (
      <main className="app-shell organization-shell">
        <header className="topbar">
          <BrandTitle
            title="Selecciona una organizacion"
            subtitle="Las cuentas de correo, reglas y sincronizaciones se administran dentro de una organizacion."
          />
          <div className="session">
            <span>{activeUser.email}</span>
            <button className="icon-button" onClick={openProfileModal} title="Mi perfil" type="button">
              <UserRound size={18} />
            </button>
            {themeSwitcher}
            <button className="icon-button" onClick={handleLogout} title="Cerrar sesion">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        {message && (
          <p className="message app-message" role="status">
            {message}
          </p>
        )}

        {!organizationsLoaded ? (
          <section className="empty-organization-state">
            <Building2 size={42} />
            <h2>Cargando organizaciones</h2>
            <p className="muted">Estamos preparando tu espacio de trabajo.</p>
          </section>
        ) : organizations.length === 0 ? (
          <section className="empty-organization-state">
            <Building2 size={42} />
            <h2>Aun no tienes organizaciones</h2>
            <p className="muted">Crea una organizacion para empezar a vincular cuentas de Google y definir reglas.</p>
            <button onClick={() => openOrganizationModal()} type="button">
              <Plus size={18} />
              Agregar organizacion
            </button>
          </section>
        ) : (
          <section className="organization-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Organizaciones</p>
                <h2>Elige donde trabajar</h2>
              </div>
              {isOwner && (
                <button onClick={() => openOrganizationModal()} type="button">
                  <Plus size={18} />
                  Agregar organizacion
                </button>
              )}
            </div>
            <div className="organization-grid">
              {organizations.map((organization) => (
                <article className="organization-card" key={organization.id}>
                  <button className="organization-card-main" onClick={() => handleSelectOrganization(organization)} type="button">
                    <span className="organization-icon">
                      <Building2 size={24} />
                    </span>
                    <strong>{organization.name}</strong>
                    <span>{organization.role}</span>
                  </button>
                  {organization.role === "owner" && (
                    <div className="row-actions">
                      <button className="icon-button" onClick={() => openOrganizationModal(organization)} title="Editar organizacion">
                        <Pencil size={16} />
                      </button>
                      <button
                        className="icon-button danger"
                        disabled={loading}
                        onClick={() => handleDeleteOrganization(organization)}
                        title="Eliminar organizacion"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  )}
                </article>
              ))}
            </div>
          </section>
        )}

        {isOrganizationModalOpen && (
          <div className="modal-backdrop" role="presentation">
            <section className="modal" role="dialog" aria-modal="true" aria-labelledby="organization-modal-title">
              <div className="modal-header">
                <div>
                  <p className="eyebrow">{editingOrganization ? "Editar" : "Nueva"} organizacion</p>
                  <h2 id="organization-modal-title">
                    {editingOrganization ? "Actualizar organizacion" : "Agregar organizacion"}
                  </h2>
                </div>
                <button className="icon-button" onClick={closeOrganizationModal} title="Cerrar" type="button">
                  <X size={18} />
                </button>
              </div>
              <form className="modal-form" onSubmit={handleSaveOrganization}>
                <label>
                  Nombre de la organizacion
                  <input
                    autoFocus
                    value={organizationName}
                    onChange={(event) => setOrganizationName(event.target.value)}
                    placeholder="Mi empresa"
                  />
                </label>
                <button disabled={loading} type="submit">
                  <Building2 size={18} />
                  {editingOrganization ? "Guardar cambios" : "Crear organizacion"}
                </button>
              </form>
            </section>
          </div>
        )}
        {profileModal}
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <BrandTitle title="Centro de procesamiento" subtitle={`Organizacion activa: ${selectedOrganization.name}`} />
        <div className="session">
          {isOwner && (
            <>
              <button className="secondary-button" onClick={openBusinessHoursModal} type="button">
                <Clock size={17} />
                Horario de seguimiento
              </button>
              <button className="secondary-button" onClick={returnToOrganizationSelector} type="button">
                <Building2 size={17} />
                Cambiar organizacion
              </button>
            </>
          )}
          <span>{activeUser.email}</span>
          <button className="icon-button" onClick={openProfileModal} title="Mi perfil" type="button">
            <UserRound size={18} />
          </button>
          {themeSwitcher}
          <button className="icon-button" onClick={handleLogout} title="Cerrar sesion">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <section className="summary-grid" aria-label="Resumen operativo">
        <div className="metric-card">
          <span className="summary-number">{messages.length}</span>
          <span className="muted">correos</span>
        </div>
        <div className="metric-card">
          <span className="summary-number">{attachments.length}</span>
          <span className="muted">adjuntos</span>
        </div>
        {isOwner && (
          <>
            <div className="metric-card">
              <span className="summary-number">{connections.length}</span>
              <span className="muted">cuentas</span>
            </div>
            <div className="metric-card">
              <span className="summary-number">{activeRules}</span>
              <span className="muted">reglas activas</span>
            </div>
            <div className="metric-card">
              <span className="summary-number">{events.length}</span>
              <span className="muted">eventos</span>
            </div>
          </>
        )}
      </section>

      {message && (
        <p className="message app-message" role="status">
          {message}
        </p>
      )}

      <section className="workspace">
        {isOwner && <div className="workspace-toolbar">
          <nav className="account-tabs" aria-label="Navegacion principal">
            <button
              className={activeMainTab === "accounts" ? "active" : ""}
              onClick={showAccountsList}
              type="button"
            >
              Cuentas
            </button>
            <button
              className={activeMainTab === "rules" ? "active" : ""}
              onClick={() => setActiveMainTab("rules")}
              type="button"
            >
              Reglas
            </button>
          </nav>
          <div className="toolbar-actions">
            <button className="secondary-button" onClick={openRuleModal} type="button">
              <ListChecks size={18} />
              Nueva regla
            </button>
            <button onClick={() => openAccountModal()} type="button">
              <Plus size={18} />
              Agregar
            </button>
          </div>
        </div>}

        {isOwner && activeMainTab === "rules" ? (
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Reglas</p>
                <h2>Todas las reglas</h2>
                <p className="muted">Administra las reglas generales y revisa rapidamente a que cuentas estan asociadas.</p>
              </div>
              <button onClick={openRuleModal} type="button">
                <Plus size={18} />
                Nueva regla
              </button>
            </div>
            <div className="rules-table-list">
              {rules.map((rule) => (
                <article className="rule-row" key={rule.id}>
                  <div>
                    <strong>{rule.name}</strong>
                    <span>{ruleSummary(rule)}</span>
                    <div className="account-badges">
                      {(rule.connection_ids || []).map((connectionId) => (
                        <button key={connectionId} onClick={() => selectConnection(String(connectionId))} type="button">
                          {connectionLabel(connectionId)}
                        </button>
                      ))}
                      {(rule.connection_ids || []).length === 0 && <span>Sin cuentas asociadas</span>}
                    </div>
                  </div>
                  <div className="row-actions">
                    <button className="icon-button" onClick={() => openEditRuleModal(rule)} title="Editar regla" type="button">
                      <Pencil size={16} />
                    </button>
                    <button
                      className={`icon-button ${(rule.whatsapp_enabled_connection_ids || []).length > 0 ? "solid" : ""}`}
                      onClick={() => openRuleWhatsAppModal(rule)}
                      title="Notificaciones WhatsApp"
                      type="button"
                    >
                      <MessageCircle size={16} />
                    </button>
                    <button
                      className={`icon-button ${rule.api_connection_count > 0 ? "solid" : ""}`}
                      onClick={() => openRuleApiModal(rule)}
                      title="Conectar APIs"
                      type="button"
                    >
                      <Link2 size={16} />
                    </button>
                    <button
                      className={`icon-button ${followupConfig(rule).enabled ? "solid" : ""}`}
                      onClick={() => openRuleFollowupModal(rule)}
                      title="Seguimiento de respuestas"
                      type="button"
                    >
                      <Clock size={16} />
                    </button>
                    <button className="icon-button danger" onClick={() => handleDeleteRule(rule.id)} title="Eliminar regla" type="button">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </article>
              ))}
              {rules.length === 0 && <div className="empty compact-empty">Sin reglas configuradas.</div>}
            </div>
          </section>
        ) : selectedConnectionId === "all" ? (
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Cuentas</p>
                <h2>Cuentas conectadas</h2>
                <p className="muted">Selecciona una cuenta para ver sus correos, reglas y eventos asociados.</p>
              </div>
            </div>
            <div className="table-wrap">
              <table className="accounts-table">
                <thead>
                  <tr>
                    <th>Cuenta</th>
                    <th>Proposito</th>
                    <th>Reglas</th>
                    <th>Correos</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {connections.map((connection) => (
                    <tr key={connection.id} onClick={() => selectConnection(String(connection.id))}>
                      <td>
                        <strong>{connection.display_name || connection.email}</strong>
                        <span>{connection.email}</span>
                      </td>
                      <td>{connection.purpose || "Sin proposito definido"}</td>
                      <td>
                        <strong>{connectionRuleCount(connection.id)}</strong>
                        <span>{connectionRuleNames(connection.id).slice(0, 2).join(", ") || "Sin reglas"}</span>
                      </td>
                      <td>{messages.filter((emailMessage) => emailMessage.google_connection_id === connection.id).length}</td>
                      <td>
                        <span className="status">{connection.status}</span>
                      </td>
                      <td>
                        <div className="row-actions" onClick={(event) => event.stopPropagation()}>
                          {isOwner ? (
                            <>
                              <button className="icon-button" disabled={loading} onClick={() => openAccountModal(connection)} title="Editar cuenta" type="button">
                                <Pencil size={17} />
                              </button>
                              <button
                                className="icon-button"
                                disabled={loading || connectionRuleCount(connection.id) === 0}
                                onClick={() => handleSyncConnection(connection.id)}
                                title={connectionRuleCount(connection.id) === 0 ? "Crea una regla antes de sincronizar" : "Sincronizar Gmail"}
                              >
                                <RefreshCw size={17} />
                              </button>
                              <button
                                className={`icon-button ${isWatchActive(connection) ? "danger" : ""}`}
                                disabled={loading}
                                onClick={() =>
                                  isWatchActive(connection)
                                    ? handleStopWatchConnection(connection.id)
                                    : openWatchModal(connection)
                                }
                                title={isWatchActive(connection) ? "Inactivar monitor Gmail" : "Registrar monitor Gmail"}
                              >
                                <Bell size={17} />
                              </button>
                              <button className="icon-button" disabled={loading} onClick={() => openWhatsAppModal(connection)} title="Configurar WhatsApp">
                                <MessageCircle size={17} />
                              </button>
                              <button
                                className={`icon-button ${connection.followup_enabled ? "solid" : ""}`}
                                disabled={loading}
                                onClick={() => openAccountFollowupModal(connection)}
                                title="Seguimiento por cuenta"
                              >
                                <Clock size={17} />
                              </button>
                              <button className="icon-button danger" disabled={loading} onClick={() => handleDeleteConnection(connection.id)} title="Desconectar cuenta">
                                <Trash2 size={17} />
                              </button>
                            </>
                          ) : connection.status !== "connected" ? (
                            <button className="icon-button solid" disabled={loading} onClick={() => handleLinkSelectedAccount(connection.id)} title="Vincular con Google">
                              <ShieldCheck size={17} />
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {connections.length === 0 && (
                    <tr>
                      <td colSpan={6}>
                        <div className="empty compact-empty">Aun no hay cuentas vinculadas.</div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        ) : (
          <>
            {selectedConnection && (
              <section className="panel account-focus">
                <div className="account-identity">
                  <p className="eyebrow">Cuenta activa</p>
                  <div className="account-title-row">
                    <h2>{selectedConnection.display_name || selectedConnection.email}</h2>
                    {isOwner && (
                      <button className="icon-button subtle-icon" onClick={() => openAccountModal(selectedConnection)} title="Editar cuenta" type="button">
                        <Pencil size={16} />
                      </button>
                    )}
                  </div>
                  <p className="muted">{selectedConnection.email}</p>
                  {selectedConnection.assigned_user_email && isOwner && (
                    <p className="muted">Usuario: {selectedConnection.assigned_user_email}</p>
                  )}
                </div>
                {isOwner && <div className="account-status-strip">
                  <span className={connectionRuleCount(selectedConnection.id) > 0 ? "status" : "status warning"}>
                    {connectionRuleCount(selectedConnection.id)} reglas asociadas
                  </span>
                  <span className={isWatchActive(selectedConnection) ? "status" : "status neutral"}>
                    {isWatchActive(selectedConnection)
                      ? `Monitor activo hasta ${formatDate(selectedConnection.watch_desired_until)}`
                      : "Monitor no registrado"}
                  </span>
                  <span className={isWhatsAppConnected(selectedConnection) ? "status" : "status neutral"}>
                    {isWhatsAppConnected(selectedConnection)
                      ? `WhatsApp ${selectedConnection.whatsapp_contact_name || selectedConnection.whatsapp_number}`
                      : selectedConnection.whatsapp_status === "pending"
                        ? "WhatsApp pendiente"
                        : "WhatsApp no configurado"}
                  </span>
                  <span className={selectedConnection.followup_enabled ? "status" : "status neutral"}>
                    {selectedConnection.followup_enabled
                      ? `Seguimiento cuenta ${formatMinutes(selectedConnection.followup_response_time_minutes)}`
                      : "Seguimiento por cuenta inactivo"}
                  </span>
                </div>}
                {isOwner ? (
                  <div className="account-actions">
                    <button
                      className="account-command"
                      disabled={loading || connectionRuleCount(selectedConnection.id) === 0}
                      onClick={() => handleSyncConnection(selectedConnection.id)}
                      title={connectionRuleCount(selectedConnection.id) === 0 ? "Crea una regla antes de sincronizar" : "Sincronizar Gmail"}
                      type="button"
                    >
                      <RefreshCw size={17} />
                      Sincronizar
                    </button>
                    {isWatchActive(selectedConnection) ? (
                      <button className="account-command danger-command" disabled={loading} onClick={() => handleStopWatchConnection(selectedConnection.id)} type="button">
                        <Bell size={17} />
                        Inactivar monitor
                      </button>
                    ) : (
                      <button className="account-command" disabled={loading} onClick={() => openWatchModal(selectedConnection)} type="button">
                        <Bell size={17} />
                        Activar monitor
                      </button>
                    )}
                    <button className="account-command" disabled={loading} onClick={() => openWhatsAppModal(selectedConnection)} type="button">
                      <MessageCircle size={17} />
                      WhatsApp
                    </button>
                    <button className="account-command" disabled={loading} onClick={() => openAccountFollowupModal(selectedConnection)} type="button">
                      <Clock size={17} />
                      Seguimiento
                    </button>
                  </div>
                ) : (
                  <div className="account-actions">
                    <button className="account-command" disabled={loading || selectedConnection.status !== "connected"} onClick={() => handleSyncConnection(selectedConnection.id)} type="button">
                      <RefreshCw size={17} />
                      Sincronizar
                    </button>
                    <button className="account-command primary-command" disabled={loading} onClick={() => handleLinkSelectedAccount()} type="button">
                      <ShieldCheck size={17} />
                      {selectedConnection.status === "connected" ? "Re-vincular Gmail" : "Vincular Gmail"}
                    </button>
                  </div>
                )}
                {isOwner && isEditingConnection && (
                  <div className="account-edit-panel">
                    <label>
                      Nombre visible
                      <input value={editName} onChange={(event) => setEditName(event.target.value)} placeholder="Nombre visible" />
                    </label>
                    <label>
                      Proposito
                      <input
                        value={editPurpose}
                        onChange={(event) => setEditPurpose(event.target.value)}
                        placeholder="Proposito de la cuenta"
                      />
                    </label>
                    <div className="account-edit-actions">
                      <button disabled={loading} onClick={handleSaveConnection} type="button">
                        Guardar
                      </button>
                      <button className="secondary-button" disabled={loading} onClick={() => setIsEditingConnection(false)} type="button">
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}
              </section>
            )}

            <nav className="content-tabs" aria-label="Secciones de la cuenta">
              <button className={activePanel === "emails" ? "active" : ""} onClick={() => setActivePanel("emails")} type="button">
                <Inbox size={18} />
                Correos
              </button>
              <button className={activePanel === "rules" ? "active" : ""} onClick={() => setActivePanel("rules")} type="button">
                <ListChecks size={18} />
                Reglas
              </button>
              <button
                className={activePanel === "attachments" ? "active" : ""}
                onClick={() => setActivePanel("attachments")}
                type="button"
              >
                <Paperclip size={18} />
                Adjuntos
              </button>
              {isOwner && (
                <>
                  <button className={activePanel === "followups" ? "active" : ""} onClick={() => setActivePanel("followups")} type="button">
                    <Clock size={18} />
                    Seguimientos
                  </button>
                  <button className={activePanel === "events" ? "active" : ""} onClick={() => setActivePanel("events")} type="button">
                    <Bell size={18} />
                    Eventos
                  </button>
                </>
              )}
            </nav>

            {activePanel === "emails" && (
              <section className="mail-layout">
                <section className="panel inbox-panel">
                  <div className="panel-header">
                    <div className="section-title">
                      <Inbox size={20} />
                      <h2>Correos recientes</h2>
                    </div>
                    <span className="results-count">
                      {filteredMessages.length} de {messages.length}
                    </span>
                  </div>

                  <div className="filters-bar">
                    <label className="search-field">
                      <Search size={18} />
                      <input
                        aria-label="Buscar correos"
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder="Buscar asunto, remitente o contenido"
                      />
                    </label>
                    <button
                      aria-expanded={showFilters}
                      aria-controls="email-filters"
                      className="icon-button"
                      type="button"
                      onClick={() => setShowFilters((isOpen) => !isOpen)}
                      title="Mostrar filtros"
                    >
                      <Filter size={18} />
                    </button>
                  </div>

                  {showFilters && (
                    <form className="filter-panel" id="email-filters">
                      <label>
                        Estado
                        <select
                          aria-label="Filtrar por estado"
                          value={statusFilter}
                          onChange={(event) => setStatusFilter(event.target.value)}
                        >
                          <option value="all">Todos los estados</option>
                          {statusOptions.map((status) => (
                            <option key={status} value={status}>
                              {status}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Adjuntos
                        <select
                          aria-label="Filtrar por adjuntos"
                          value={attachmentFilter}
                          onChange={(event) => setAttachmentFilter(event.target.value as AttachmentFilter)}
                        >
                          <option value="all">Todos</option>
                          <option value="with">Con adjuntos</option>
                          <option value="without">Sin adjuntos</option>
                        </select>
                      </label>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => {
                          setStatusFilter("all");
                          setAttachmentFilter("all");
                        }}
                      >
                        Limpiar filtros
                      </button>
                    </form>
                  )}

                  <div className="message-list">
                    {filteredMessages.map((emailMessage) => (
                      <button
                        className={`message-item ${selectedMessage?.id === emailMessage.id ? "selected" : ""} ${
                          emailMessage.status === "deleted_in_gmail" ? "deleted-message" : ""
                        }`}
                        key={emailMessage.id}
                        onClick={() => setSelectedMessageId(emailMessage.id)}
                        type="button"
                      >
                        <div className="account-cell">{emailMessage.connection_email || "Cuenta no disponible"}</div>
                        <div className="message-main">
                          <h3>{decodeEmailText(emailMessage.subject) || "Sin asunto"}</h3>
                          <p>{decodeEmailText(emailMessage.sender) || "Remitente no disponible"}</p>
                          {emailMessage.snippet && <p className="snippet">{decodeEmailText(emailMessage.snippet)}</p>}
                        </div>
                        <div className="message-meta">
                          {emailMessage.status === "deleted_in_gmail" && <span className="status warning">Eliminado en Gmail</span>}
                          {emailMessage.matched_rule_name && <span className="status rule-status">{emailMessage.matched_rule_name}</span>}
                          {emailMessage.has_attachments && <span className="status">adjuntos</span>}
                          <span>{formatDate(emailMessage.received_at)}</span>
                        </div>
                      </button>
                    ))}
                    {messages.length === 0 && <div className="empty">Sin correos sincronizados todavia.</div>}
                    {messages.length > 0 && filteredMessages.length === 0 && (
                      <div className="empty">Sin resultados para los filtros activos.</div>
                    )}
                  </div>
                </section>

                <aside className="panel detail-panel">
                  <div className="panel-header">
                    <div>
                      <p className="eyebrow">Detalle</p>
                      <h2>Contexto del correo</h2>
                    </div>
                  </div>

                  {selectedMessage ? (
                    <div className="detail-content">
                      <div className="detail-card">
                        <h3>{decodeEmailText(selectedMessage.subject) || "Sin asunto"}</h3>
                        <dl>
                          <div>
                            <dt>Remitente</dt>
                            <dd>{decodeEmailText(selectedMessage.sender) || "No disponible"}</dd>
                          </div>
                          <div>
                            <dt>Cuenta</dt>
                            <dd>{selectedMessage.connection_email || "No disponible"}</dd>
                          </div>
                          <div>
                            <dt>Fecha</dt>
                            <dd>{formatDate(selectedMessage.received_at)}</dd>
                          </div>
                          <div>
                            <dt>Regla</dt>
                            <dd>{selectedMessage.matched_rule_name || "No disponible"}</dd>
                          </div>
                          <div>
                            <dt>Estado</dt>
                            <dd>
                              <span className="status">{selectedMessage.status}</span>
                            </dd>
                          </div>
                        </dl>
                        {selectedMessage.snippet && <p className="detail-snippet">{decodeEmailText(selectedMessage.snippet)}</p>}
                        {isOwner && (
                          <button className="secondary-button" disabled={loading} onClick={() => openManualFollowupModal(selectedMessage)} type="button">
                            <Clock size={17} />
                            Dar seguimiento
                          </button>
                        )}
                      </div>

                      <section className="panel-subsection">
                        <div className="section-title">
                          <Paperclip size={18} />
                          <h3>Adjuntos del correo</h3>
                        </div>
                        <div className="compact-list">
                          {selectedAttachments.map((attachment) => (
                            <div className="compact-row" key={attachment.id}>
                              <span>{attachment.filename}</span>
                              <span>{fileSize(attachment.size_bytes)}</span>
                            </div>
                          ))}
                          {selectedAttachments.length === 0 && (
                            <div className="empty compact-empty">Este correo no tiene adjuntos guardados.</div>
                          )}
                        </div>
                      </section>
                    </div>
                  ) : (
                    <div className="empty">Selecciona un correo para ver su contexto.</div>
                  )}
                </aside>
              </section>
            )}

            {activePanel === "rules" && (
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Reglas aplicadas</p>
                    <h2>Lineas de negocio de la cuenta</h2>
                    <p className="muted">
                      Estas reglas definen que correos se sincronizan. Un correo que no cumpla ninguna regla asociada no entra a la bandeja.
                    </p>
                  </div>
                  {isOwner && (
                    <button onClick={openRuleModal} type="button">
                      <Plus size={18} />
                      Nueva regla
                    </button>
                  )}
                </div>
                <div className="rules-table-list">
                  {visibleRules.map((rule) => (
                    <article className="rule-row" key={rule.id}>
                      <div>
                        <strong>{rule.name}</strong>
                        <span>{ruleSummary(rule)}</span>
                      </div>
                      {isOwner && (
                        <div className="row-actions">
                          <button className="icon-button" onClick={() => openEditRuleModal(rule)} title="Editar regla" type="button">
                            <Pencil size={16} />
                          </button>
                          <button
                            className={`icon-button ${(rule.whatsapp_enabled_connection_ids || []).length > 0 ? "solid" : ""}`}
                            onClick={() => openRuleWhatsAppModal(rule)}
                            title="Notificaciones WhatsApp"
                            type="button"
                          >
                            <MessageCircle size={16} />
                          </button>
                          <button
                            className={`icon-button ${rule.api_connection_count > 0 ? "solid" : ""}`}
                            onClick={() => openRuleApiModal(rule)}
                            title="Conectar APIs"
                            type="button"
                          >
                            <Link2 size={16} />
                          </button>
                          <button
                            className={`icon-button ${followupConfig(rule).enabled ? "solid" : ""}`}
                            onClick={() => openRuleFollowupModal(rule)}
                            title="Seguimiento de respuestas"
                            type="button"
                          >
                            <Clock size={16} />
                          </button>
                          <button className="icon-button danger" onClick={() => handleDeleteRule(rule.id)} title="Eliminar regla" type="button">
                            <Trash2 size={16} />
                          </button>
                        </div>
                      )}
                    </article>
                  ))}
                  {visibleRules.length === 0 && <div className="empty compact-empty">Sin reglas configuradas para esta cuenta.</div>}
                </div>
              </section>
            )}

            {activePanel === "attachments" && (
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Archivos</p>
                    <h2>Adjuntos guardados</h2>
                  </div>
                </div>
                <div className="compact-list">
                  {visibleAttachments.map((attachment) => (
                    <div className="compact-row" key={attachment.id}>
                      <span>{attachment.filename}</span>
                      <span>{fileSize(attachment.size_bytes)}</span>
                    </div>
                  ))}
                  {visibleAttachments.length === 0 && <div className="empty compact-empty">Sin adjuntos guardados todavia.</div>}
                </div>
              </section>
            )}

            {activePanel === "followups" && (
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Trazabilidad</p>
                    <h2>Seguimientos de respuesta</h2>
                    <p className="muted">Correos importantes que requieren respuesta desde la cuenta conectada.</p>
                  </div>
                  <div className="toolbar-actions">
                    <select
                      aria-label="Filtrar seguimientos"
                      value={followupStatusFilter}
                      onChange={(event) => setFollowupStatusFilter(event.target.value)}
                    >
                      <option value="all">Todos</option>
                      {followupStatusOptions.map((status) => (
                        <option key={status} value={status}>
                          {followupStatusLabel(status)}
                        </option>
                      ))}
                    </select>
                    <button className="secondary-button" disabled={loading} onClick={handleEvaluateFollowups} type="button">
                      <RefreshCw size={17} />
                      Evaluar
                    </button>
                  </div>
                </div>
                <div className="followup-list">
                  {followupSummary && (
                    <div className="followup-summary">
                      <span>Pendientes: {followupSummary.totals.pending || 0}</span>
                      <span>Vencidos: {followupSummary.totals.overdue || 0}</span>
                      <span>Respondidos: {(followupSummary.totals.responded || 0) + (followupSummary.totals.responded_late || 0)}</span>
                      <span>Promedio: {formatMinutes(followupSummary.avg_response_minutes)}</span>
                    </div>
                  )}
                  {visibleFollowups.map((followup) => (
                    <article className="followup-row" key={followup.id}>
                      <span className={`status followup-${followup.status}`}>{followupStatusLabel(followup.status)}</span>
                      <div>
                        <strong>{decodeEmailText(followup.subject) || "Sin asunto"}</strong>
                        <span>{decodeEmailText(followup.sender) || "Remitente no disponible"}</span>
                      </div>
                      <div>
                        <small>Fuente</small>
                        <span>{followup.tracking_source}</span>
                      </div>
                      <div>
                        <small>Regla</small>
                        <span>{followup.automation_rule_name || "Sin regla"}</span>
                      </div>
                      <div>
                        <small>Vence</small>
                        <span>{formatDate(followup.response_due_at)}</span>
                      </div>
                      <div>
                        <small>Respuesta</small>
                        <span>{followup.first_response_at ? formatDate(followup.first_response_at) : "Pendiente"}</span>
                      </div>
                      <div>
                        <small>Tiempo</small>
                        <span>{formatMinutes(followup.response_time_minutes)}</span>
                      </div>
                    </article>
                  ))}
                  {visibleFollowups.length === 0 && (
                    <div className="empty compact-empty">Aun no hay seguimientos para esta seleccion.</div>
                  )}
                </div>
              </section>
            )}

            {activePanel === "events" && (
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Actividad</p>
                    <h2>Eventos recientes</h2>
                    <p className="muted">
                      Revisa decisiones utiles del sistema: correos sincronizados, descartados, avisos WhatsApp y casos que requieren atencion.
                    </p>
                  </div>
                </div>
                <div className="event-filters">
                  <label>
                    Tipo
                    <select value={eventTypeFilter} onChange={(event) => setEventTypeFilter(event.target.value)}>
                      {eventTypeOptions.map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Desde
                    <input value={eventDateFrom} onChange={(event) => setEventDateFrom(event.target.value)} type="date" />
                  </label>
                  <label>
                    Hasta
                    <input value={eventDateTo} onChange={(event) => setEventDateTo(event.target.value)} type="date" />
                  </label>
                  <label>
                    Cantidad
                    <input min="1" max="500" value={eventLimit} onChange={(event) => setEventLimit(event.target.value)} type="number" />
                  </label>
                  <div className="event-filter-actions">
                    <button className="secondary-button" disabled={loading} onClick={() => refreshEventsWithFilters()} type="button">
                      <Filter size={17} />
                      Filtrar
                    </button>
                    <button className="ghost-button" disabled={loading} onClick={clearEventFilters} type="button">
                      Limpiar
                    </button>
                  </div>
                </div>
                <div className="compact-list">
                  {visibleEvents.map((event) => {
                    const detailItems = eventDetailItems(event);
                    const ruleDiagnostics = eventRuleDiagnostics(event);
                    const tone = eventTone(event);

                    return (
                      <article className={`event-card event-${tone}`} key={event.id}>
                        <div className="event-card-icon" aria-hidden="true">
                          {tone === "success" ? <CheckCircle2 size={20} /> : tone === "warning" ? <AlertTriangle size={20} /> : <Mail size={20} />}
                        </div>
                        <div className="event-card-body">
                          <div className="event-title">
                            <div>
                              <span className="event-kicker">{eventTypeLabel(event.event_type)}</span>
                              <strong>{eventTitle(event)}</strong>
                              <span>{eventSubtitle(event)}</span>
                            </div>
                            <time>{formatDate(event.created_at)}</time>
                          </div>
                          {event.event_type !== "gmail_message_ignored" && <span className="event-message">{event.message}</span>}
                        {detailItems.length > 0 && (
                          <dl className="event-details">
                            {detailItems.map(([label, value]) => (
                              <div key={`${event.id}-${label}`}>
                                <dt>{label}</dt>
                                <dd>{value}</dd>
                              </div>
                            ))}
                          </dl>
                        )}
                        {ruleDiagnostics.length > 0 && (
                          <div className="event-rule-checks">
                            {ruleDiagnostics.map((rule) => (
                              <div className="event-rule-check" key={`${event.id}-${rule.ruleName}`}>
                                <div className="event-rule-heading">
                                  <span className={`status ${rule.matched ? "connected" : "neutral"}`}>
                                    {rule.matched ? "Coincide" : "No coincide"}
                                  </span>
                                  <strong>{rule.ruleName}</strong>
                                </div>
                                {rule.checks.length > 0 && (
                                  <div className="event-check-list">
                                    {rule.checks.map((check) => (
                                      <span className={check.passed ? "passed" : "failed"} key={`${rule.ruleName}-${check.label}-${check.expected}`}>
                                        {check.label}: {check.expected}
                                        {check.matchType && <small>{check.matchType}</small>}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                        </div>
                      </article>
                    );
                  })}
                  {visibleEvents.length === 0 && <div className="empty compact-empty">Sin eventos registrados.</div>}
                </div>
              </section>
            )}
          </>
        )}
      </section>

      {isAccountModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="account-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">{editingAccount ? "Editar cuenta" : "Nueva cuenta"}</p>
                <h2 id="account-modal-title">{editingAccount ? "Actualizar cuenta" : "Agregar conexion Gmail"}</h2>
              </div>
              <button className="icon-button" onClick={resetAccountModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">
              {editingAccount
                ? "Actualiza la identificacion interna y el usuario que puede acceder a esta cuenta. El correo Gmail vinculado no cambia aqui."
                : "Crea el acceso del responsable de esta cuenta. Puede vincular Google ahora o entrar despues con este usuario."}
            </p>
            {accountModalMessage && <p className="message modal-message">{accountModalMessage}</p>}
            <form onSubmit={editingAccount ? handleSaveEditedAccount : handleStartGoogleOAuth} className="modal-form">
              <label>
                Nombre de la cuenta
                <input
                  value={newAccountName}
                  onChange={(event) => setNewAccountName(event.target.value)}
                  placeholder="Mesa de ayuda, Compras, Contabilidad"
                />
              </label>
              <label>
                Proposito
                <textarea
                  value={newAccountPurpose}
                  onChange={(event) => setNewAccountPurpose(event.target.value)}
                  placeholder="Describe el proposito de esta cuenta para tu equipo"
                />
              </label>
              <label>
                Usuario
                <input
                  value={newAccountUserEmail}
                  onChange={(event) => setNewAccountUserEmail(event.target.value)}
                  placeholder="responsable@empresa.com"
                  type="email"
                />
              </label>
              <label>
                Contrasena
                <input
                  value={newAccountPassword}
                  onChange={(event) => setNewAccountPassword(event.target.value)}
                  placeholder={editingAccount ? "Dejala vacia para conservarla" : "Minimo 6 caracteres"}
                  type="password"
                />
              </label>
              <button disabled={loading} type="submit">
                {editingAccount ? <Pencil size={18} /> : <ShieldCheck size={18} />}
                {editingAccount ? "Guardar cambios" : "Vincular cuenta de Google"}
              </button>
              {editingAccount ? (
                editingAccount.status !== "connected" && (
                  <button className="secondary-button full-button" disabled={loading} onClick={(event) => handleSaveEditedAccount(event, true)} type="button">
                    <ShieldCheck size={18} />
                    Guardar y vincular
                  </button>
                )
              ) : (
                <button className="secondary-button full-button" disabled={loading} onClick={handleCreateAccountAccess} type="button">
                  <UserRound size={18} />
                  Crear acceso
                </button>
              )}
            </form>
          </section>
        </div>
      )}
      {profileModal}

      {isRuleModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal wide-modal" role="dialog" aria-modal="true" aria-labelledby="rule-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">{editingRule ? "Editar regla" : "Nueva regla"}</p>
                <h2 id="rule-modal-title">
                  {editingRule ? "Actualizar regla de sincronizacion" : "Definir correos que se sincronizan"}
                </h2>
              </div>
              <button className="icon-button" onClick={closeRuleModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">
              Asocia esta regla a una o varias cuentas. Solo los correos que cumplan estas condiciones se guardaran en la bandeja.
            </p>
            {ruleModalMessage && <p className="message modal-message">{ruleModalMessage}</p>}
            <div className="account-picker">
              <p className="eyebrow">Cuentas donde aplica</p>
              {connections.map((connection) => (
                <label className="checkbox-label account-check" key={connection.id}>
                  <input
                    checked={ruleConnectionIds.includes(connection.id)}
                    onChange={() => toggleRuleConnection(connection.id)}
                    type="checkbox"
                  />
                  <span>
                    <strong>{connection.display_name || connection.email}</strong>
                    <small>{connection.email}</small>
                  </span>
                </label>
              ))}
              {connections.length === 0 && <div className="empty compact-empty">Primero agrega una cuenta.</div>}
            </div>
            <div className="segmented-control" role="tablist" aria-label="Modo de creacion de regla">
              <button className={ruleMode === "ai" ? "active" : ""} onClick={() => setRuleMode("ai")} type="button">
                <Sparkles size={17} />
                Crear con IA
              </button>
              <button className={ruleMode === "manual" ? "active" : ""} onClick={() => setRuleMode("manual")} type="button">
                <ListChecks size={17} />
                Formulario
              </button>
            </div>

            {ruleMode === "ai" && (
              <div className="ai-rule-box">
                <label>
                  Describe que correos debe aceptar esta regla
                  <textarea
                    value={ruleText}
                    onChange={(event) => setRuleText(event.target.value)}
                    placeholder="Ej: Comprobantes de pago de proveedores con adjuntos PDF"
                  />
                </label>
                <button disabled={loading} onClick={handleDraftRule} type="button">
                  <Sparkles size={18} />
                  {editingRule ? "Guardar regla con IA" : "Crear regla con IA"}
                </button>
              </div>
            )}

            {ruleMode === "manual" && (
              <form className="modal-form" onSubmit={handleSaveRule}>
                <label>
                  Nombre
                  <input value={ruleName} onChange={(event) => setRuleName(event.target.value)} placeholder="Facturas con adjuntos" />
                </label>
                <label>
                  Remitente contiene
                  <input
                    value={ruleSender}
                    onChange={(event) => setRuleSender(event.target.value)}
                    placeholder="@proveedor.com"
                  />
                </label>
                <label>
                  Asunto contiene
                  <input value={ruleSubject} onChange={(event) => setRuleSubject(event.target.value)} placeholder="factura" />
                </label>
                <label className="checkbox-label">
                  <input
                    checked={ruleHasAttachment}
                    onChange={(event) => setRuleHasAttachment(event.target.checked)}
                    type="checkbox"
                  />
                  Exigir que el correo tenga adjuntos
                </label>
                <button disabled={loading} type="submit">
                  {editingRule ? <Pencil size={18} /> : <Plus size={18} />}
                  {editingRule ? "Guardar cambios" : "Guardar regla"}
                </button>
              </form>
            )}
          </section>
        </div>
      )}

      {watchConnectionTarget && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="watch-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">Monitor Gmail</p>
                <h2 id="watch-modal-title">Activar monitor</h2>
              </div>
              <button className="icon-button" onClick={closeWatchModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">
              Selecciona hasta cuando quieres mantener activo el monitoreo de {watchConnectionTarget.display_name || watchConnectionTarget.email}.
              Google entrega vigencias cortas y el sistema las renovara automaticamente mientras esta fecha siga vigente.
            </p>
            {watchModalMessage && <p className="message modal-message">{watchModalMessage}</p>}
            <form className="modal-form" onSubmit={handleSubmitWatch}>
              <fieldset className="radio-group">
                <legend>Vigencia</legend>
                <label className="radio-option">
                  <input checked={watchDuration === "1w"} onChange={() => setWatchDuration("1w")} type="radio" />
                  1 semana
                </label>
                <label className="radio-option">
                  <input checked={watchDuration === "1m"} onChange={() => setWatchDuration("1m")} type="radio" />
                  1 mes
                </label>
                <label className="radio-option">
                  <input checked={watchDuration === "3m"} onChange={() => setWatchDuration("3m")} type="radio" />
                  3 meses
                </label>
                <label className="radio-option">
                  <input checked={watchDuration === "1y"} onChange={() => setWatchDuration("1y")} type="radio" />
                  1 año
                </label>
                <label className="radio-option">
                  <input checked={watchDuration === "custom"} onChange={() => setWatchDuration("custom")} type="radio" />
                  Personalizado
                </label>
              </fieldset>
              {watchDuration === "custom" && (
                <label>
                  Fecha personalizada
                  <input
                    type="datetime-local"
                    value={customWatchUntil}
                    onChange={(event) => setCustomWatchUntil(event.target.value)}
                  />
                </label>
              )}
              <button disabled={loading} type="submit">
                <Bell size={18} />
                Activar monitor
              </button>
            </form>
          </section>
        </div>
      )}

      {ruleWhatsAppTarget && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="rule-whatsapp-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">WhatsApp</p>
                <h2 id="rule-whatsapp-modal-title">Notificaciones por regla</h2>
              </div>
              <button className="icon-button" onClick={closeRuleWhatsAppModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">
              Activa en que cuentas esta regla debe enviar avisos por WhatsApp. Solo se notifican correos que coincidan con la regla y que pertenezcan a cuentas con WhatsApp conectado.
            </p>
            {ruleWhatsAppMessage && <p className="message modal-message">{ruleWhatsAppMessage}</p>}
            <form className="modal-form" onSubmit={handleSaveRuleWhatsAppNotifications}>
              <div className="account-picker">
                <p className="eyebrow">Cuentas asociadas a {ruleWhatsAppTarget.name}</p>
                {(ruleWhatsAppTarget.connection_ids || []).map((connectionId) => {
                  const connection = connections.find((item) => item.id === connectionId);
                  const whatsappConnected = isWhatsAppConnected(connection);
                  const isEnabled = ruleWhatsAppConnectionIds.includes(connectionId);
                  return (
                    <label
                      className={`checkbox-label account-check ${!whatsappConnected ? "disabled-check" : ""}`}
                      key={connectionId}
                    >
                      <input
                        checked={isEnabled}
                        disabled={!whatsappConnected && !isEnabled}
                        onChange={() => toggleRuleWhatsAppConnection(connectionId)}
                        type="checkbox"
                      />
                      <span>
                        <strong>{connection?.display_name || connection?.email || `Cuenta ${connectionId}`}</strong>
                        <small>{connection?.email || "Cuenta asociada"}</small>
                        <small>
                          {whatsappConnected
                            ? `WhatsApp conectado: ${connection?.whatsapp_number}`
                            : `WhatsApp ${connection?.whatsapp_status || "no configurado"}. Configuralo antes de recibir avisos.`}
                        </small>
                      </span>
                    </label>
                  );
                })}
                {(ruleWhatsAppTarget.connection_ids || []).length === 0 && (
                  <div className="empty compact-empty">Esta regla no tiene cuentas asociadas.</div>
                )}
              </div>
              <button disabled={loading} type="submit">
                <MessageCircle size={18} />
                Guardar notificaciones
              </button>
            </form>
          </section>
        </div>
      )}

      {ruleApiTarget && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal wide-modal api-modal" role="dialog" aria-modal="true" aria-labelledby="rule-api-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">APIs conectadas</p>
                <h2 id="rule-api-modal-title">Conectar APIs a {ruleApiTarget.name}</h2>
              </div>
              <button className="icon-button" onClick={closeRuleApiModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">
              Cuando un correo coincida con esta regla, se ejecutaran las APIs activas con los datos mapeados del correo y valores personalizados.
            </p>
            {ruleApiMessage && <p className={`message modal-message ${ruleApiMessageTone}`}>{ruleApiMessage}</p>}
            <div className="api-config-layout">
              <aside className="api-connection-list">
                <button className={!editingRuleApi ? "active" : ""} onClick={resetRuleApiForm} type="button">
                  <Plus size={16} />
                  Nueva API
                </button>
                {ruleApiConnections.map((apiConnection) => (
                  <button
                    className={editingRuleApi?.id === apiConnection.id ? "active" : ""}
                    key={apiConnection.id}
                    onClick={() => selectRuleApi(apiConnection)}
                    type="button"
                  >
                    <span>
                      <strong>{apiConnection.name}</strong>
                      <small>{apiConnection.method} - {apiConnection.is_active ? "Activa" : "Inactiva"}</small>
                    </span>
                  </button>
                ))}
                {ruleApiConnections.length === 0 && <div className="empty compact-empty">Sin APIs configuradas.</div>}
              </aside>
              <form className="modal-form api-config-form" onSubmit={handleSaveRuleApi}>
                <div className="api-basic-grid">
                  <label>
                    Nombre
                    <input value={ruleApiName} onChange={(event) => setRuleApiName(event.target.value)} placeholder="Crear ticket en CRM" />
                  </label>
                  <label>
                    Metodo
                    <select value={ruleApiMethod} onChange={(event) => setRuleApiMethod(event.target.value)}>
                      <option value="POST">POST</option>
                      <option value="PUT">PUT</option>
                      <option value="PATCH">PATCH</option>
                      <option value="GET">GET</option>
                      <option value="DELETE">DELETE</option>
                    </select>
                  </label>
                  <label className="api-url-field">
                    URL
                    <input value={ruleApiUrl} onChange={(event) => setRuleApiUrl(event.target.value)} placeholder="https://api.empresa.com/webhook" />
                  </label>
                  <label>
                    Timeout
                    <input value={ruleApiTimeout} onChange={(event) => setRuleApiTimeout(event.target.value)} min="1" max="60" type="number" />
                  </label>
                  <label className="checkbox-label api-active-toggle">
                    <input checked={ruleApiActive} onChange={(event) => setRuleApiActive(event.target.checked)} type="checkbox" />
                    API activa
                  </label>
                </div>
                {renderApiMappings("Headers", "headers", "Campos enviados como headers HTTP.")}
                {renderApiMappings("Query params", "query_params", "Campos enviados en la URL como parametros.")}
                {renderApiMappings("Body JSON", "body_fields", "Campos enviados en el cuerpo JSON.")}
                <div className="modal-actions-row">
                  {editingRuleApi && (
                    <button className="secondary-button danger-text" disabled={loading} onClick={handleDeleteRuleApi} type="button">
                      <Trash2 size={17} />
                      Eliminar API
                    </button>
                  )}
                  <button className="secondary-button" disabled={loading || ruleApiTesting} onClick={handleTestRuleApi} type="button">
                    <RefreshCw size={17} />
                    {ruleApiTesting ? "Probando..." : "Probar API"}
                  </button>
                  <button disabled={loading || ruleApiTesting} type="submit">
                    <Link2 size={18} />
                    {editingRuleApi ? "Guardar API" : "Crear API"}
                  </button>
                </div>
              </form>
            </div>
          </section>
        </div>
      )}

      {ruleFollowupTarget && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="rule-followup-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">Seguimiento</p>
                <h2 id="rule-followup-modal-title">Trazabilidad de respuestas</h2>
              </div>
              <button className="icon-button" onClick={closeRuleFollowupModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">
              Cuando esta opcion esta activa, cada correo nuevo que entre por esta regla queda en seguimiento hasta que la cuenta conectada responda en el mismo hilo.
            </p>
            {ruleFollowupMessage && <p className="message modal-message">{ruleFollowupMessage}</p>}
            <form className="modal-form" onSubmit={handleSaveRuleFollowup}>
              <label className="checkbox-label">
                <input
                  checked={ruleFollowupEnabled}
                  onChange={(event) => setRuleFollowupEnabled(event.target.checked)}
                  type="checkbox"
                />
                Activar seguimiento para esta regla
              </label>
              <label>
                Tiempo maximo de respuesta en horas
                <input
                  min="0.25"
                  step="0.25"
                  type="number"
                  value={ruleFollowupHours}
                  onChange={(event) => setRuleFollowupHours(event.target.value)}
                />
              </label>
              <label className="checkbox-label">
                <input
                  checked={ruleFollowupNotifyWhatsApp}
                  onChange={(event) => setRuleFollowupNotifyWhatsApp(event.target.checked)}
                  type="checkbox"
                />
                Notificar por WhatsApp si vence sin respuesta
              </label>
              <label>
                Preaviso antes de vencer en minutos
                <input
                  min="1"
                  type="number"
                  value={ruleFollowupWarnMinutes}
                  onChange={(event) => setRuleFollowupWarnMinutes(event.target.value)}
                  placeholder="30"
                />
              </label>
              <label>
                Escalar despues de vencido en minutos
                <input
                  min="1"
                  type="number"
                  value={ruleFollowupEscalationMinutes}
                  onChange={(event) => setRuleFollowupEscalationMinutes(event.target.value)}
                  placeholder="60"
                />
              </label>
              <button disabled={loading} type="submit">
                <Clock size={18} />
                Guardar seguimiento
              </button>
            </form>
          </section>
        </div>
      )}

      {accountFollowupTarget && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="account-followup-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">Seguimiento</p>
                <h2 id="account-followup-modal-title">Seguimiento por cuenta</h2>
              </div>
              <button className="icon-button" onClick={closeAccountFollowupModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">
              Activa seguimiento para todos los correos sincronizados de {accountFollowupTarget.display_name || accountFollowupTarget.email}, incluso si la regla no tiene seguimiento propio.
            </p>
            {accountFollowupMessage && <p className="message modal-message">{accountFollowupMessage}</p>}
            <form className="modal-form" onSubmit={handleSaveAccountFollowup}>
              <label className="checkbox-label">
                <input
                  checked={accountFollowupEnabled}
                  onChange={(event) => setAccountFollowupEnabled(event.target.checked)}
                  type="checkbox"
                />
                Activar seguimiento por cuenta
              </label>
              <label>
                Tiempo maximo de respuesta en horas
                <input
                  min="0.25"
                  step="0.25"
                  type="number"
                  value={accountFollowupHours}
                  onChange={(event) => setAccountFollowupHours(event.target.value)}
                />
              </label>
              <label className="checkbox-label">
                <input
                  checked={accountFollowupNotifyWhatsApp}
                  onChange={(event) => setAccountFollowupNotifyWhatsApp(event.target.checked)}
                  type="checkbox"
                />
                Notificar por WhatsApp si vence sin respuesta
              </label>
              <label>
                Preaviso antes de vencer en minutos
                <input
                  min="1"
                  type="number"
                  value={accountFollowupWarnMinutes}
                  onChange={(event) => setAccountFollowupWarnMinutes(event.target.value)}
                  placeholder="30"
                />
              </label>
              <label>
                Escalar despues de vencido en minutos
                <input
                  min="1"
                  type="number"
                  value={accountFollowupEscalationMinutes}
                  onChange={(event) => setAccountFollowupEscalationMinutes(event.target.value)}
                  placeholder="60"
                />
              </label>
              <button disabled={loading} type="submit">
                <Clock size={18} />
                Guardar seguimiento
              </button>
            </form>
          </section>
        </div>
      )}

      {manualFollowupTarget && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="manual-followup-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">Seguimiento manual</p>
                <h2 id="manual-followup-modal-title">Dar seguimiento a este correo</h2>
              </div>
              <button className="icon-button" onClick={closeManualFollowupModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">{decodeEmailText(manualFollowupTarget.subject) || "Sin asunto"}</p>
            {manualFollowupMessage && <p className="message modal-message">{manualFollowupMessage}</p>}
            <form className="modal-form" onSubmit={handleCreateManualFollowup}>
              <label>
                Tiempo maximo de respuesta en horas
                <input
                  min="0.25"
                  step="0.25"
                  type="number"
                  value={manualFollowupHours}
                  onChange={(event) => setManualFollowupHours(event.target.value)}
                />
              </label>
              <label className="checkbox-label">
                <input
                  checked={manualFollowupNotifyWhatsApp}
                  onChange={(event) => setManualFollowupNotifyWhatsApp(event.target.checked)}
                  type="checkbox"
                />
                Notificar por WhatsApp si vence sin respuesta
              </label>
              <label>
                Preaviso antes de vencer en minutos
                <input
                  min="1"
                  type="number"
                  value={manualFollowupWarnMinutes}
                  onChange={(event) => setManualFollowupWarnMinutes(event.target.value)}
                  placeholder="30"
                />
              </label>
              <label>
                Escalar despues de vencido en minutos
                <input
                  min="1"
                  type="number"
                  value={manualFollowupEscalationMinutes}
                  onChange={(event) => setManualFollowupEscalationMinutes(event.target.value)}
                  placeholder="60"
                />
              </label>
              <button disabled={loading} type="submit">
                <Clock size={18} />
                Crear seguimiento
              </button>
            </form>
          </section>
        </div>
      )}

      {whatsAppConnectionTarget && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="whatsapp-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">WhatsApp</p>
                <h2 id="whatsapp-modal-title">Configurar WhatsApp</h2>
              </div>
              <button className="icon-button" onClick={closeWhatsAppModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">
              Ingresa el numero del usuario que recibira notificaciones de la cuenta {whatsAppConnectionTarget.display_name || whatsAppConnectionTarget.email}.
              Se abrira WhatsApp con un mensaje de confirmacion hacia el asistente de la plataforma.
            </p>
            {whatsAppModalMessage && <p className="message modal-message">{whatsAppModalMessage}</p>}
            <form className="modal-form whatsapp-settings-form" onSubmit={handleSubmitWhatsApp}>
              <label>
                Numero de WhatsApp
                <input
                  value={whatsAppNumber}
                  onChange={(event) => setWhatsAppNumber(event.target.value)}
                  placeholder="573001234567"
                  inputMode="tel"
                />
              </label>
              <button disabled={loading} type="submit">
                <MessageCircle size={18} />
                Abrir WhatsApp Web
              </button>
            </form>
            <section className="whatsapp-preferences">
              <div>
                <p className="eyebrow">Notificaciones</p>
                <h3>Tipos de avisos</h3>
                <p className="muted">Controla que mensajes enviaremos a este numero cuando la cuenta este conectada.</p>
              </div>
              <ToggleRow
                checked={whatsAppNotificationsEnabled}
                description="Enciende o apaga todos los avisos de esta cuenta."
                label="Todos"
                onChange={setAllWhatsAppNotifications}
              />
              <ToggleRow
                checked={whatsAppNotifyNewEmail}
                description="Se envia solo si la regla tambien tiene WhatsApp habilitado."
                label="Correo nuevo"
                onChange={setWhatsAppNotifyNewEmail}
              />
              <div className="preference-group">
                <span>Seguimiento</span>
                <ToggleRow
                  checked={whatsAppNotifyFollowupOverdue}
                  label="Vencidos"
                  onChange={setWhatsAppNotifyFollowupOverdue}
                />
                <ToggleRow
                  checked={whatsAppNotifyFollowupWarning}
                  label="Por vencer"
                  onChange={setWhatsAppNotifyFollowupWarning}
                />
                <ToggleRow
                  checked={whatsAppNotifyFollowupLate}
                  label="Contestados tarde"
                  onChange={setWhatsAppNotifyFollowupLate}
                />
                <ToggleRow
                  checked={whatsAppNotifyFollowupResponded}
                  label="Respondidos"
                  onChange={setWhatsAppNotifyFollowupResponded}
                />
              </div>
              <button className="secondary-button" disabled={loading} onClick={handleSaveWhatsAppPreferences} type="button">
                <MessageCircle size={18} />
                Guardar preferencias
              </button>
            </section>
          </section>
        </div>
      )}

      {isBusinessHoursModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal wide-modal" role="dialog" aria-modal="true" aria-labelledby="business-hours-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">Seguimiento</p>
                <h2 id="business-hours-modal-title">Horario habil de respuesta</h2>
              </div>
              <button className="icon-button" onClick={closeBusinessHoursModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">
              Este horario es excluyente: los vencimientos de seguimiento solo consumen tiempo dentro de los dias y horas seleccionados.
            </p>
            {businessHoursMessage && <p className="message modal-message">{businessHoursMessage}</p>}
            <form className="modal-form" onSubmit={handleSaveBusinessHours}>
              <label>
                Zona horaria
                <select value={businessTimezone} onChange={(event) => setBusinessTimezone(event.target.value)}>
                  <option value="America/Bogota">America/Bogota</option>
                  <option value="America/Mexico_City">America/Mexico_City</option>
                  <option value="America/Lima">America/Lima</option>
                  <option value="America/Santiago">America/Santiago</option>
                  <option value="America/New_York">America/New_York</option>
                </select>
              </label>
              <div className="two-column-form">
                <label>
                  Hora general de inicio
                  <input value={businessStartTime} onChange={(event) => setBusinessStartTime(event.target.value)} type="time" />
                </label>
                <label>
                  Hora general de fin
                  <input value={businessEndTime} onChange={(event) => setBusinessEndTime(event.target.value)} type="time" />
                </label>
              </div>
              <fieldset className="business-day-schedule">
                <legend>Dias y excepciones</legend>
                {BUSINESS_DAY_OPTIONS.map(([day, label]) => {
                  const config = businessDayHours[String(day)] || {
                    enabled: businessDays.includes(day),
                    uses_default: true,
                    start_time: null,
                    end_time: null,
                  };
                  return (
                    <div className={`business-day-row ${config.enabled ? "enabled" : "disabled"}`} key={day}>
                      <label className="checkbox-label">
                        <input checked={config.enabled} onChange={() => toggleBusinessDay(day)} type="checkbox" />
                        {label}
                      </label>
                      <label className="checkbox-label">
                        <input
                          checked={config.uses_default}
                          disabled={!config.enabled}
                          onChange={(event) =>
                            updateBusinessDayHour(day, {
                              uses_default: event.target.checked,
                              start_time: event.target.checked ? null : config.start_time || businessStartTime,
                              end_time: event.target.checked ? null : config.end_time || businessEndTime,
                            })
                          }
                          type="checkbox"
                        />
                        Usa horario general
                      </label>
                      <div className="day-hour-inputs">
                        <input
                          aria-label={`Inicio ${label}`}
                          disabled={!config.enabled || config.uses_default}
                          onChange={(event) => updateBusinessDayHour(day, { start_time: event.target.value })}
                          type="time"
                          value={config.start_time || businessStartTime}
                        />
                        <input
                          aria-label={`Fin ${label}`}
                          disabled={!config.enabled || config.uses_default}
                          onChange={(event) => updateBusinessDayHour(day, { end_time: event.target.value })}
                          type="time"
                          value={config.end_time || businessEndTime}
                        />
                      </div>
                    </div>
                  );
                })}
              </fieldset>
              <label>
                <span className="label-with-help">
                  Pais de festivos
                  <span className="help-icon" tabIndex={0}>
                    <Info size={15} />
                    <span className="help-tooltip" role="tooltip">
                      Usa el codigo ISO de 2 letras del pais, por ejemplo CO para Colombia, MX para Mexico o US para Estados Unidos.
                      Si no existe cache local para ese pais y ano, el backend consulta Nager.Date y guarda los festivos en BD. Luego el seguimiento excluye esos festivos y los festivos propios de la organizacion.
                    </span>
                  </span>
                </span>
                <input
                  maxLength={2}
                  value={holidayCountry}
                  onChange={(event) => setHolidayCountry(event.target.value)}
                  placeholder="CO"
                />
              </label>
              <p className="muted">
                Ejemplo: si un correo llega el viernes despues del cierre, el contador inicia en el siguiente minuto habil configurado.
              </p>
              <button disabled={loading} type="submit">
                <Clock size={18} />
                Guardar horario
              </button>
            </form>
          </section>
        </div>
      )}

      {isOrganizationModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="organization-modal-title">
            <div className="modal-header">
              <div>
                <p className="eyebrow">{editingOrganization ? "Editar" : "Nueva"} organizacion</p>
                <h2 id="organization-modal-title">
                  {editingOrganization ? "Actualizar organizacion" : "Agregar organizacion"}
                </h2>
              </div>
              <button className="icon-button" onClick={closeOrganizationModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <form className="modal-form" onSubmit={handleSaveOrganization}>
              <label>
                Nombre de la organizacion
                <input
                  autoFocus
                  value={organizationName}
                  onChange={(event) => setOrganizationName(event.target.value)}
                  placeholder="Mi empresa"
                />
              </label>
              <button disabled={loading} type="submit">
                <Building2 size={18} />
                {editingOrganization ? "Guardar cambios" : "Crear organizacion"}
              </button>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}
