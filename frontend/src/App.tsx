import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Bell,
  Building2,
  Filter,
  Inbox,
  Link2,
  ListChecks,
  LogOut,
  MessageCircle,
  Paperclip,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import {
  Attachment,
  AutomationRule,
  AUTH_EXPIRED_EVENT,
  createOrganization,
  createRule,
  deleteConnection,
  deleteOrganization,
  deleteRule,
  EmailMessage,
  GoogleConnection,
  listAttachments,
  listEvents,
  listMessages,
  listConnections,
  listOrganizations,
  listRules,
  login,
  Organization,
  startGoogleOAuth,
  startWhatsAppSetup,
  stopWatchConnection,
  syncConnection,
  SystemEvent,
  updateConnection,
  updateOrganization,
  updateRule,
  updateRuleWhatsAppNotifications,
  User,
  watchConnection,
} from "./services/api";

const DEMO_EMAIL = "demo@example.com";
const DEMO_PASSWORD = "Demo123!";

type AttachmentFilter = "all" | "with" | "without";
type MainTab = "accounts" | "rules";
type WorkTab = "emails" | "rules" | "attachments" | "events";
type RuleMode = "ai" | "manual";
type WatchDuration = "1w" | "1m" | "3m" | "1y" | "custom";

function formatDate(value: string | null) {
  if (!value) return "Sin fecha";
  return new Date(value).toLocaleString();
}

function fileSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [token, setToken] = useState(() => localStorage.getItem("access_token") ?? "");
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem("user");
    return stored ? JSON.parse(stored) : null;
  });
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [organizationsLoaded, setOrganizationsLoaded] = useState(false);
  const [selectedOrganizationId, setSelectedOrganizationId] = useState(
    () => localStorage.getItem("selected_organization_id") ?? "",
  );
  const [isOrganizationModalOpen, setIsOrganizationModalOpen] = useState(false);
  const [editingOrganization, setEditingOrganization] = useState<Organization | null>(null);
  const [organizationName, setOrganizationName] = useState("");
  const [watchConnectionTarget, setWatchConnectionTarget] = useState<GoogleConnection | null>(null);
  const [watchDuration, setWatchDuration] = useState<WatchDuration>("1m");
  const [customWatchUntil, setCustomWatchUntil] = useState(defaultWatchUntil);
  const [watchModalMessage, setWatchModalMessage] = useState("");
  const [whatsAppConnectionTarget, setWhatsAppConnectionTarget] = useState<GoogleConnection | null>(null);
  const [whatsAppNumber, setWhatsAppNumber] = useState("");
  const [whatsAppModalMessage, setWhatsAppModalMessage] = useState("");
  const [ruleWhatsAppTarget, setRuleWhatsAppTarget] = useState<AutomationRule | null>(null);
  const [ruleWhatsAppConnectionIds, setRuleWhatsAppConnectionIds] = useState<number[]>([]);
  const [ruleWhatsAppMessage, setRuleWhatsAppMessage] = useState("");
  const [editingRule, setEditingRule] = useState<AutomationRule | null>(null);
  const [connections, setConnections] = useState<GoogleConnection[]>([]);
  const [messages, setMessages] = useState<EmailMessage[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [activeMainTab, setActiveMainTab] = useState<MainTab>("accounts");
  const [activePanel, setActivePanel] = useState<WorkTab>("emails");
  const [ruleMode, setRuleMode] = useState<RuleMode>("ai");
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);
  const [newAccountName, setNewAccountName] = useState("");
  const [newAccountPurpose, setNewAccountPurpose] = useState("");
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
  const [selectedConnectionId, setSelectedConnectionId] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [attachmentFilter, setAttachmentFilter] = useState<AttachmentFilter>("all");
  const [showFilters, setShowFilters] = useState(false);

  const isLoggedIn = useMemo(() => Boolean(token && user), [token, user]);
  const selectedOrganization =
    organizations.find((organization) => String(organization.id) === selectedOrganizationId) ?? null;
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

  useEffect(() => {
    if (!token) return;
    refreshOrganizations(token);
  }, [token]);

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
    if (!selectedOrganizationId) return;
    localStorage.setItem("selected_organization_id", selectedOrganizationId);
  }, [selectedOrganizationId]);

  useEffect(() => {
    setEditName(selectedConnection?.display_name || selectedConnection?.email || "");
    setEditPurpose(selectedConnection?.purpose || "");
    setIsEditingConnection(false);
  }, [selectedConnectionId, selectedConnection?.display_name, selectedConnection?.purpose, selectedConnection?.email]);

  async function refreshConnections(activeToken = token) {
    try {
      setConnections(await listConnections(activeToken));
      setMessages(await listMessages(activeToken));
      setAttachments(await listAttachments(activeToken));
      setRules(await listRules(activeToken));
      setEvents(await listEvents(activeToken));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudieron cargar las cuentas");
    }
  }

  async function refreshOrganizations(activeToken = token) {
    try {
      const items = await listOrganizations(activeToken);
      setOrganizations(items);
      const storedOrganizationId = localStorage.getItem("selected_organization_id");
      const storedStillExists = items.some((organization) => String(organization.id) === storedOrganizationId);
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
        emailMessage.subject,
        emailMessage.sender,
        emailMessage.connection_email,
        emailMessage.snippet,
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
      await refreshOrganizations(response.access_token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo iniciar sesion");
    } finally {
      setLoading(false);
    }
  }

  async function handleStartGoogleOAuth(event?: FormEvent) {
    event?.preventDefault();
    if (!newAccountName.trim()) {
      setMessage("Escribe un nombre para identificar la cuenta.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const response = await startGoogleOAuth(token, {
        display_name: newAccountName.trim(),
        purpose: newAccountPurpose.trim(),
      });
      window.location.href = response.authorization_url;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo iniciar OAuth con Google");
      setLoading(false);
    }
  }

  function resetAccountModal() {
    setNewAccountName("");
    setNewAccountPurpose("");
    setIsAccountModalOpen(false);
  }

  async function handleDeleteConnection(id: number) {
    setLoading(true);
    setMessage("");

    try {
      await deleteConnection(token, id);
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
    if (connectionRuleCount(id) === 0) {
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
    setWhatsAppModalMessage("");
  }

  function closeWhatsAppModal() {
    setWhatsAppConnectionTarget(null);
    setWhatsAppModalMessage("");
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

  if (!isLoggedIn) {
    return (
      <main className="auth-shell">
        <section className="auth-panel">
          <div>
            <p className="eyebrow">Email Assistance</p>
            <h1>Acceso de prueba</h1>
            <p className="muted">Entra con el usuario demo y empieza vinculando cuentas de correo.</p>
          </div>

          <form onSubmit={handleLogin} className="form">
            <label>
              Correo
              <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" />
            </label>
            <label>
              Password
              <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" />
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

  if (!selectedOrganization) {
    return (
      <main className="app-shell organization-shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">Email Assistance</p>
            <h1>Selecciona una organizacion</h1>
            <p className="muted">Las cuentas de correo, reglas y sincronizaciones se administran dentro de una organizacion.</p>
          </div>
          <div className="session">
            <span>{activeUser.email}</span>
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
              <button onClick={() => openOrganizationModal()} type="button">
                <Plus size={18} />
                Agregar organizacion
              </button>
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
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Email Assistance</p>
          <h1>Centro de procesamiento</h1>
          <p className="muted">Organizacion activa: {selectedOrganization.name}</p>
        </div>
        <div className="session">
          <button className="secondary-button" onClick={returnToOrganizationSelector} type="button">
            <Building2 size={17} />
            Cambiar organizacion
          </button>
          <span>{activeUser.email}</span>
          <button className="icon-button" onClick={handleLogout} title="Cerrar sesion">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <section className="summary-grid" aria-label="Resumen operativo">
        <div className="metric-card">
          <span className="summary-number">{connections.length}</span>
          <span className="muted">cuentas</span>
        </div>
        <div className="metric-card">
          <span className="summary-number">{messages.length}</span>
          <span className="muted">correos</span>
        </div>
        <div className="metric-card">
          <span className="summary-number">{attachments.length}</span>
          <span className="muted">adjuntos</span>
        </div>
        <div className="metric-card">
          <span className="summary-number">{activeRules}</span>
          <span className="muted">reglas activas</span>
        </div>
        <div className="metric-card">
          <span className="summary-number">{events.length}</span>
          <span className="muted">eventos</span>
        </div>
      </section>

      {message && (
        <p className="message app-message" role="status">
          {message}
        </p>
      )}

      <section className="workspace">
        <div className="workspace-toolbar">
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
            <button onClick={() => setIsAccountModalOpen(true)} type="button">
              <Plus size={18} />
              Agregar
            </button>
          </div>
        </div>

        {activeMainTab === "rules" ? (
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
                          <button
                            className="icon-button"
                            disabled={loading}
                            onClick={() => openWhatsAppModal(connection)}
                            title="Configurar WhatsApp"
                          >
                            <MessageCircle size={17} />
                          </button>
                          <button
                            className="icon-button danger"
                            disabled={loading}
                            onClick={() => handleDeleteConnection(connection.id)}
                            title="Desconectar cuenta"
                          >
                            <Trash2 size={17} />
                          </button>
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
                    <button className="icon-button subtle-icon" onClick={() => setIsEditingConnection((current) => !current)} title="Editar cuenta" type="button">
                      <Pencil size={16} />
                    </button>
                  </div>
                  <p className="muted">{selectedConnection.email}</p>
                </div>
                <div className="account-status-strip">
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
                </div>
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
                </div>
                {isEditingConnection && (
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
              <button className={activePanel === "events" ? "active" : ""} onClick={() => setActivePanel("events")} type="button">
                <Bell size={18} />
                Eventos
              </button>
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
                        className={`message-item ${selectedMessage?.id === emailMessage.id ? "selected" : ""}`}
                        key={emailMessage.id}
                        onClick={() => setSelectedMessageId(emailMessage.id)}
                        type="button"
                      >
                        <div className="account-cell">{emailMessage.connection_email || "Cuenta no disponible"}</div>
                        <div className="message-main">
                          <h3>{emailMessage.subject || "Sin asunto"}</h3>
                          <p>{emailMessage.sender || "Remitente no disponible"}</p>
                          {emailMessage.snippet && <p className="snippet">{emailMessage.snippet}</p>}
                        </div>
                        <div className="message-meta">
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
                        <h3>{selectedMessage.subject || "Sin asunto"}</h3>
                        <dl>
                          <div>
                            <dt>Remitente</dt>
                            <dd>{selectedMessage.sender || "No disponible"}</dd>
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
                        {selectedMessage.snippet && <p className="detail-snippet">{selectedMessage.snippet}</p>}
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
                  <button onClick={openRuleModal} type="button">
                    <Plus size={18} />
                    Nueva regla
                  </button>
                </div>
                <div className="rules-table-list">
                  {visibleRules.map((rule) => (
                    <article className="rule-row" key={rule.id}>
                      <div>
                        <strong>{rule.name}</strong>
                        <span>{ruleSummary(rule)}</span>
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
                        <button className="icon-button danger" onClick={() => handleDeleteRule(rule.id)} title="Eliminar regla" type="button">
                          <Trash2 size={16} />
                        </button>
                      </div>
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

            {activePanel === "events" && (
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Actividad</p>
                    <h2>Eventos recientes</h2>
                  </div>
                </div>
                <div className="compact-list">
                  {visibleEvents.map((event) => (
                    <div className="event-row" key={event.id}>
                      <span className="status neutral">{event.level}</span>
                      <strong>{event.event_type}</strong>
                      <span>{event.message}</span>
                      <time>{formatDate(event.created_at)}</time>
                    </div>
                  ))}
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
                <p className="eyebrow">Nueva cuenta</p>
                <h2 id="account-modal-title">Agregar conexion Gmail</h2>
              </div>
              <button className="icon-button" onClick={resetAccountModal} title="Cerrar" type="button">
                <X size={18} />
              </button>
            </div>
            <p className="muted">
              Define como identificaras esta cuenta dentro del sistema. Luego Google confirmara el correo real y creara la conexion.
            </p>
            <form onSubmit={handleStartGoogleOAuth} className="modal-form">
              <label>
                Nombre de la cuenta
                <input
                  value={newAccountName}
                  onChange={(event) => setNewAccountName(event.target.value)}
                  placeholder="Facturas proveedores"
                />
              </label>
              <label>
                Proposito
                <textarea
                  value={newAccountPurpose}
                  onChange={(event) => setNewAccountPurpose(event.target.value)}
                  placeholder="Recibe facturas con PDF para enviarlas al flujo contable"
                />
              </label>
              <button disabled={loading} type="submit">
                <ShieldCheck size={18} />
                Vincular cuenta de Google
              </button>
            </form>
          </section>
        </div>
      )}

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
                  1 ano
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
            <form className="modal-form" onSubmit={handleSubmitWhatsApp}>
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
