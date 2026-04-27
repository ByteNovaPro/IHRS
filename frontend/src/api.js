const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const AUTH_STORAGE_KEY = "ihrs-auth-session";
const AUTH_EXPIRED_EVENT = "ihrs-auth-expired";

export function getStoredAuth() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return JSON.parse(window.localStorage.getItem(AUTH_STORAGE_KEY));
  } catch {
    return null;
  }
}

export function storeAuth(auth) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
  }
}

export function clearStoredAuth() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }
}

export function notifyAuthExpired(message = "登录状态已过期，请重新登录") {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(
    new CustomEvent(AUTH_EXPIRED_EVENT, {
      detail: { message },
    }),
  );
}

export function getAuthExpiredEventName() {
  return AUTH_EXPIRED_EVENT;
}

async function request(path, options = {}) {
  const auth = getStoredAuth();
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (auth?.token) {
    headers.Authorization = `Bearer ${auth.token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
    ...options,
  });

  if (!response.ok) {
    let message = `请求失败（${response.status}）`;

    try {
      const errorBody = await response.json();
      message = errorBody.message || message;
    } catch {
      // Keep the status-based message when the response is not JSON.
    }

    if (response.status === 401 && auth?.token) {
      notifyAuthExpired(message);
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function buildAuthHeaders(extraHeaders = {}) {
  const auth = getStoredAuth();
  const headers = {
    "Content-Type": "application/json",
    ...extraHeaders,
  };

  if (auth?.token) {
    headers.Authorization = `Bearer ${auth.token}`;
  }

  return headers;
}

function buildConsultUserKey() {
  const auth = getStoredAuth();
  if (!auth) {
    return "";
  }

  if (auth.role === "ADMIN") {
    return `ADMIN:${auth.phone || auth.name || "system"}`;
  }

  if (auth.id != null) {
    return `USER:${auth.id}`;
  }

  if (auth.phone) {
    return `USER_PHONE:${auth.phone}`;
  }

  if (auth.token) {
    return `TOKEN:${auth.token}`;
  }

  return "";
}

function buildConsultHeaders(extraHeaders = {}) {
  const consultUserKey = buildConsultUserKey();
  return buildAuthHeaders({
    ...(consultUserKey ? { "X-Consult-User-Key": consultUserKey } : {}),
    ...extraHeaders,
  });
}

export function listHospitals() {
  return request("/api/catalog/hospitals");
}

export function createHospital(payload) {
  return request("/api/admin/hospitals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listAdminHospitals(params = {}) {
  const query = new URLSearchParams({
    page: String(params.page ?? 0),
    size: String(params.size ?? 12),
    keyword: params.keyword ?? "",
  });
  return request(`/api/admin/hospitals?${query.toString()}`);
}

export function updateHospital(id, payload) {
  return request(`/api/admin/hospitals/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteHospital(id) {
  return request(`/api/admin/hospitals/${id}`, {
    method: "DELETE",
  });
}

export function listRooms() {
  return request("/api/catalog/rooms");
}

export function createRoom(payload) {
  return request("/api/admin/rooms", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listAdminRooms(params = {}) {
  const query = new URLSearchParams({
    page: String(params.page ?? 0),
    size: String(params.size ?? 12),
    keyword: params.keyword ?? "",
  });

  if (params.hospitalId) {
    query.set("hospitalId", String(params.hospitalId));
  }

  return request(`/api/admin/rooms?${query.toString()}`);
}

export function updateRoom(id, payload) {
  return request(`/api/admin/rooms/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteRoom(id) {
  return request(`/api/admin/rooms/${id}`, {
    method: "DELETE",
  });
}

export function listDoctors() {
  return request("/api/catalog/doctors");
}

export function createDoctor(payload) {
  return request("/api/admin/doctors", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listAdminDoctors(params = {}) {
  const query = new URLSearchParams({
    page: String(params.page ?? 0),
    size: String(params.size ?? 12),
    keyword: params.keyword ?? "",
  });

  if (params.hospitalId) {
    query.set("hospitalId", String(params.hospitalId));
  }

  if (params.roomId) {
    query.set("roomId", String(params.roomId));
  }

  if (params.workTimeSlot) {
    query.set("workTimeSlot", params.workTimeSlot);
  }

  return request(`/api/admin/doctors?${query.toString()}`);
}

export function updateDoctor(id, payload) {
  return request(`/api/admin/doctors/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteDoctor(id) {
  return request(`/api/admin/doctors/${id}`, {
    method: "DELETE",
  });
}

export function createAppointment(payload) {
  return request("/api/appointments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listAppointments(patientPhone) {
  const query = patientPhone ? `?patientPhone=${encodeURIComponent(patientPhone)}` : "";
  return request(`/api/appointments${query}`);
}

export function getAppointmentQuota({ doctorId, appointmentDate, timeSlot }) {
  const query = new URLSearchParams({
    doctorId: String(doctorId),
    appointmentDate,
    timeSlot,
  });
  return request(`/api/appointments/quota?${query.toString()}`);
}

export function getAppointmentQuotaCalendar({ doctorIds, startDate, endDate }) {
  const query = new URLSearchParams({
    startDate,
    endDate,
  });

  doctorIds.forEach((doctorId) => {
    query.append("doctorIds", String(doctorId));
  });

  return request(`/api/appointments/quota-calendar?${query.toString()}`);
}

export function listAdminAppointments() {
  return request("/api/admin/appointments");
}

export function cancelAppointment(id) {
  return request(`/api/admin/appointments/${id}/cancel`, {
    method: "PUT",
  });
}

export function cancelMyAppointment(id) {
  return request(`/api/appointments/${id}/cancel`, {
    method: "PUT",
  });
}

export function deleteAppointment(id) {
  return request(`/api/admin/appointments/${id}`, {
    method: "DELETE",
  });
}

export function consultSymptom(payload) {
  return request("/agent/consult", {
    method: "POST",
    headers: buildConsultHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function consultSymptomStream(payload, handlers = {}) {
  const auth = getStoredAuth();
  const response = await fetch(`${API_BASE_URL}/agent/consult/stream`, {
    method: "POST",
    headers: buildConsultHeaders(),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `请求失败（${response.status}）`;

    try {
      const errorBody = await response.json();
      message = errorBody.message || message;
    } catch {
      // Keep the status-based message when the response is not JSON.
    }

    if (response.status === 401 && auth?.token) {
      notifyAuthExpired(message);
    }

    throw new Error(message);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("浏览器不支持流式响应");
  }

  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done }).replace(/\r\n/g, "\n");

    let separatorIndex = buffer.indexOf("\n\n");
    while (separatorIndex !== -1) {
      const rawEvent = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);
      parseStreamEvent(rawEvent, handlers);
      separatorIndex = buffer.indexOf("\n\n");
    }

    if (done) {
      if (buffer.trim()) {
        parseStreamEvent(buffer, handlers);
      }
      break;
    }
  }
}

export function deleteConsultConversation(conversationId) {
  return request(`/agent/consult/conversations/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
    headers: buildConsultHeaders(),
  });
}

export function getConsultSession() {
  return request("/agent/consult/session", {
    headers: buildConsultHeaders(),
  });
}

function parseStreamEvent(rawEvent, handlers) {
  const lines = rawEvent
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) {
    return;
  }

  let eventName = "message";
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!dataLines.length) {
    return;
  }

  const dataText = dataLines.join("\n");
  let payload = dataText;

  try {
    payload = JSON.parse(dataText);
  } catch {
    // Keep plain-text payloads when the event data is not JSON.
  }

  const handler = handlers[eventName];
  if (typeof handler === "function") {
    handler(payload);
  }
}

export function getRagStats() {
  return request("/agent/rag/stats");
}

export function listRagDocuments(limit = 20) {
  return request(`/agent/rag/documents?limit=${encodeURIComponent(limit)}`);
}

export function searchRagDocuments(payload) {
  return request("/agent/rag/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(payload) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function register(payload) {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function logout() {
  return request("/api/auth/logout", {
    method: "POST",
  });
}
