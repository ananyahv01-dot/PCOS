import axios from "axios";

// If VITE_API_URL is set we call it directly; otherwise we use relative URLs
// which the Vite dev server proxies to the backend (see vite.config.js).
const baseURL = import.meta.env.VITE_API_URL || "";

const api = axios.create({ baseURL });

// Attach the auth token (if any) to every request. Reading from sessionStorage
// at request time avoids React effect-ordering races on the Authorization header.
export const AUTH_STORAGE_KEY = "pcos_auth";
api.interceptors.request.use((config) => {
  try {
    const raw = sessionStorage.getItem(AUTH_STORAGE_KEY);
    if (raw) {
      const { token } = JSON.parse(raw);
      if (token) config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    /* ignore malformed storage */
  }
  return config;
});

// ---- Auth ----------------------------------------------------------------
export const register = (name, email, password) =>
  api.post("/api/auth/register", { name, email, password }).then((r) => r.data);

export const login = (email, password) =>
  api.post("/api/auth/login", { email, password }).then((r) => r.data);

export const forgotPassword = (email) =>
  api.post("/api/auth/forgot-password", { email }).then((r) => r.data);

export const resetPassword = (token, newPassword) =>
  api
    .post("/api/auth/reset-password", { token, new_password: newPassword })
    .then((r) => r.data);

// ---- Assessment ----------------------------------------------------------
export const predict = (payload) =>
  api.post("/api/predict", payload).then((r) => r.data);

// ---- Providers (doctors & counselors) -------------------------------------
export const getProviders = () => api.get("/api/providers").then((r) => r.data);

export const setAvailability = (available) =>
  api.patch("/api/provider/availability", { available }).then((r) => r.data);

export const selectProvider = (providerId) =>
  api
    .post("/api/patient/select-provider", { provider_id: providerId })
    .then((r) => r.data);

// ---- Patient -------------------------------------------------------------
export const getHistory = () =>
  api.get("/api/patient/history").then((r) => r.data);

// ---- Assessment detail (for reports) -------------------------------------
export const getAssessment = (id) =>
  api.get(`/api/assessments/${id}`).then((r) => r.data);

// ---- Doctor --------------------------------------------------------------
export const getDoctorAssessments = () =>
  api.get("/api/doctor/assessments").then((r) => r.data);

export const uploadPrescription = ({ patientEmail, note, assessmentId, file }) => {
  const form = new FormData();
  form.append("patient_email", patientEmail);
  if (note) form.append("note", note);
  if (assessmentId != null) form.append("assessment_id", assessmentId);
  form.append("file", file);
  return api
    .post("/api/doctor/prescriptions", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

// ---- Prescriptions -------------------------------------------------------
export const getPatientPrescriptions = () =>
  api.get("/api/patient/prescriptions").then((r) => r.data);

// Download a prescription as a blob (keeps the Authorization header) and
// trigger a browser save with the original filename.
export const downloadPrescription = async (id, filename) => {
  const res = await api.get(`/api/prescriptions/${id}/download`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || `prescription-${id}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

// ---- Blood reports (patient uploads, for High-risk assessments only) -----
export const uploadBloodReport = ({ note, assessmentId, file }) => {
  const form = new FormData();
  if (note) form.append("note", note);
  if (assessmentId != null) form.append("assessment_id", assessmentId);
  form.append("file", file);
  return api
    .post("/api/patient/blood-reports", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const getPatientBloodReports = () =>
  api.get("/api/patient/blood-reports").then((r) => r.data);

export const getProviderBloodReports = (patientEmail) =>
  api
    .get("/api/doctor/blood-reports", { params: { patient_email: patientEmail } })
    .then((r) => r.data);

export const downloadBloodReport = async (id, filename) => {
  const res = await api.get(`/api/blood-reports/${id}/download`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || `blood-report-${id}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

// ---- Admin ---------------------------------------------------------------
export const getMetrics = () => api.get("/api/admin/metrics").then((r) => r.data);
export const getStats = () => api.get("/api/admin/stats").then((r) => r.data);
export const retrain = () => api.post("/api/admin/retrain", {}).then((r) => r.data);

export default api;
