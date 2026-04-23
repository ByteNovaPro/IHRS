const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const AUTH_STORAGE_KEY = "ihrs-auth-session";

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

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
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

export function listAdminAppointments() {
  return request("/api/admin/appointments");
}

export function cancelAppointment(id) {
  return request(`/api/admin/appointments/${id}/cancel`, {
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
