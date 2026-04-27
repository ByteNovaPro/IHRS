<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  cancelAppointment,
  cancelMyAppointment,
  clearStoredAuth,
  consultSymptomStream,
  createAppointment,
  createDoctor,
  createHospital,
  createRoom,
  deleteAppointment,
  deleteConsultConversation,
  deleteDoctor,
  deleteHospital,
  deleteRoom,
  getConsultSession,
  getAppointmentQuota,
  getAppointmentQuotaCalendar,
  getAuthExpiredEventName,
  getRagStats,
  getStoredAuth,
  listAdminDoctors,
  listAdminHospitals,
  listAdminRooms,
  listAdminAppointments,
  listDoctors,
  listHospitals,
  listAppointments,
  listRagDocuments,
  listRooms,
  login,
  logout,
  register,
  searchRagDocuments,
  storeAuth,
  updateDoctor,
  updateHospital,
  updateRoom,
} from "./api";

const VIEW_STORAGE_KEY = "ihrs-current-view";
const MODULE_STORAGE_KEY = "ihrs-active-module";

const savedView =
  typeof window !== "undefined" ? window.localStorage.getItem(VIEW_STORAGE_KEY) : null;
const savedModule =
  typeof window !== "undefined" ? window.localStorage.getItem(MODULE_STORAGE_KEY) : null;

const validViews = ["home", "admin", "appointment", "consult", "rag"];
const validModules = ["hospital", "room", "doctor", "appointment"];
const initialRoute = getRouteState();
const currentView = ref(initialRoute.view ?? (["admin", "appointment", "consult", "rag"].includes(savedView) ? savedView : "home"));
const activeModule = ref(initialRoute.module ?? (validModules.includes(savedModule) ? savedModule : "hospital"));
let isApplyingBrowserRoute = false;

const hospitals = ref([]);
const rooms = ref([]);
const doctors = ref([]);
const appointments = ref([]);
const adminHospitals = ref([]);
const adminRooms = ref([]);
const adminDoctors = ref([]);
const userAppointments = ref([]);
const isLoadingCatalog = ref(false);
const isSavingRecord = ref(false);
const isSubmittingAppointment = ref(false);
const isLoadingQuota = ref(false);
const isConsulting = ref(false);
const isAuthenticating = ref(false);
const currentUser = ref(getStoredAuth());
const AUTH_MODE_LOGIN = "login";
const AUTH_MODE_REGISTER = "register";
const AUTH_MODE_ADMIN = "admin";
const AUTH_EXPIRED_EVENT = getAuthExpiredEventName();

const ADMIN_PHONE = "13800000000";

const authMode = ref(AUTH_MODE_LOGIN);

const moduleMeta = {
  hospital: {
    title: "医院管理",
    subtitle: "维护医院基础资料、入口说明与展示文案。",
  },
  room: {
    title: "诊室管理",
    subtitle: "维护所属医院、楼层位置与诊室服务简介。",
  },
  doctor: {
    title: "医生管理",
    subtitle: "维护医生头衔、所属诊室与诊疗方向说明。",
  },
  appointment: {
    title: "预约管理",
    subtitle: "查看患者挂号预约，支持取消或删除预约记录。",
  },
};

const detailDialog = reactive({
  visible: false,
  type: "hospital",
  item: null,
});

const editorDialog = reactive({
  visible: false,
  type: "hospital",
  mode: "create",
});

const hospitalForm = reactive({
  id: null,
  name: "",
  level: "",
  location: "",
  shortIntro: "",
  detailIntro: "",
});

const roomForm = reactive({
  id: null,
  hospitalId: null,
  name: "",
  floor: "",
  shortIntro: "",
  detailIntro: "",
});

const doctorForm = reactive({
  id: null,
  hospitalId: null,
  roomId: null,
  name: "",
  title: "",
  specialty: "",
  workTimeSlot: "上午 08:30-10:30",
  shortIntro: "",
  detailIntro: "",
});

const workTimeOptions = [
  "上午 08:30-10:30",
  "上午 10:30-12:00",
  "下午 14:00-16:00",
  "下午 16:00-17:30",
];
const APPOINTMENT_DATE_FUTURE_DAYS = 15;
const CONSULT_REGION_CITY_ALIASES = {
  广东: ["广州", "深圳"],
  广东省: ["广州", "深圳"],
  浙江: ["杭州", "宁波"],
  浙江省: ["杭州", "宁波"],
  江苏: ["南京", "苏州"],
  江苏省: ["南京", "苏州"],
  山东: ["济南", "青岛"],
  山东省: ["济南", "青岛"],
  福建: ["福州", "厦门"],
  福建省: ["福州", "厦门"],
  湖南: ["长沙"],
  湖南省: ["长沙"],
  湖北: ["武汉"],
  湖北省: ["武汉"],
  河南: ["郑州"],
  河南省: ["郑州"],
  安徽: ["合肥"],
  安徽省: ["合肥"],
  四川: ["成都"],
  四川省: ["成都"],
  陕西: ["西安"],
  陕西省: ["西安"],
  上海: ["上海"],
  上海市: ["上海"],
  北京: ["北京"],
  北京市: ["北京"],
  天津: ["天津"],
  天津市: ["天津"],
  重庆: ["重庆"],
  重庆市: ["重庆"],
};
const CONSULT_DIRECT_CITY_HINTS = [
  "上海",
  "北京",
  "广州",
  "深圳",
  "杭州",
  "南京",
  "苏州",
  "成都",
  "重庆",
  "武汉",
  "西安",
  "天津",
  "长沙",
  "郑州",
  "青岛",
  "合肥",
  "宁波",
  "厦门",
  "福州",
  "济南",
];

const appointmentForm = reactive({
  hospitalId: null,
  roomId: null,
  doctorId: null,
  patientName: "",
  patientPhone: "",
  appointmentDate: "",
  timeSlot: "上午 08:30-10:30",
  symptom: "",
});

const appointmentStep = ref(1);
const expandedHospitalIds = ref([]);
const expandedRoomIds = ref([]);
const browsedHospitalId = ref(null);
const browsedRoomId = ref(null);

const authForm = reactive({
  phone: "",
  password: "",
  name: "",
});

const consultForm = reactive({
  symptom: "",
});

const consultResult = ref(null);
const consultRecommendations = ref([]);
const consultMessages = ref([]);
const activeConsultSymptom = ref("");
const consultConversationId = ref("");
const consultRecommendationRequested = ref(false);
const consultRecommendationCollapseNames = ref([]);
const consultChatViewport = ref(null);
const activeConsultAssistantMessageId = ref("");
let consultMessageSequence = 0;
const ragStats = ref(null);
const ragDocuments = ref([]);
const ragSearchResults = ref([]);
const isLoadingRag = ref(false);
const isSearchingRag = ref(false);
const ragDocumentLimit = ref(12);
const ragSearchForm = reactive({
  query: "",
  topK: 5,
});
const appointmentQuota = ref(null);
const appointmentCalendarQuotas = ref([]);
const isLoadingAppointmentCalendar = ref(false);

const filters = reactive({
  keyword: "",
  hospitalId: "",
  roomId: "",
  workTimeSlot: "",
});
const adminPagination = reactive({
  hospital: { page: 1, size: 12, total: 0 },
  room: { page: 1, size: 12, total: 0 },
  doctor: { page: 1, size: 12, total: 0 },
});

const currentTitle = computed(() => moduleMeta[activeModule.value].title);
const currentSubtitle = computed(() => moduleMeta[activeModule.value].subtitle);
const isLoggedIn = computed(() => Boolean(currentUser.value?.token));
const isAdminUser = computed(() => currentUser.value?.role === "ADMIN");
const appointmentHospitals = computed(() => hospitals.value.filter(Boolean));
const selectedAppointmentHospital = computed(() =>
  hospitals.value.find((hospital) => hospital.id === Number(appointmentForm.hospitalId)),
);
const selectedAppointmentRoom = computed(() =>
  rooms.value.find((room) => room.id === Number(appointmentForm.roomId)),
);
const selectedAppointmentDoctor = computed(() =>
  doctors.value.find((doctor) => doctor.id === Number(appointmentForm.doctorId)),
);
const selectedAppointmentHospitalRooms = computed(() => getHospitalRooms(appointmentForm.hospitalId));
const selectedAppointmentHospitalDoctors = computed(() => getHospitalDoctors(appointmentForm.hospitalId));
const selectedAppointmentRoomDoctors = computed(() => getRoomDoctors(appointmentForm.roomId));
const appointmentFocusedHospital = computed(
  () =>
    hospitals.value.find((hospital) => hospital.id === Number(browsedHospitalId.value))
    || selectedAppointmentHospital.value
    || appointmentHospitals.value[0]
    || null,
);
const appointmentFocusedRoom = computed(
  () =>
    rooms.value.find((room) => room.id === Number(browsedRoomId.value))
    || selectedAppointmentRoom.value
    || appointmentFocusedHospitalRooms.value[0]
    || null,
);
const appointmentFocusedHospitalRooms = computed(() => getHospitalRooms(appointmentFocusedHospital.value?.id));
const appointmentFocusedHospitalDoctors = computed(() => getHospitalDoctors(appointmentFocusedHospital.value?.id));
const appointmentFocusedRoomDoctors = computed(() => getRoomDoctors(appointmentFocusedRoom.value?.id));
const selectedDateDoctorQuotaMap = computed(() => {
  const quotaMap = new Map();

  for (const quota of appointmentCalendarQuotas.value) {
    if (quota.appointmentDate === appointmentForm.appointmentDate) {
      quotaMap.set(quota.doctorId, quota);
    }
  }

  return quotaMap;
});
const appointmentDateSummaries = computed(() => {
  const roomDoctors = selectedAppointmentRoomDoctors.value.filter(Boolean);
  if (!roomDoctors.length) {
    return [];
  }

  const doctorIds = new Set(roomDoctors.map((doctor) => doctor.id));
  const summaryMap = new Map();

  for (const quota of appointmentCalendarQuotas.value) {
    if (!doctorIds.has(quota.doctorId)) {
      continue;
    }

    const current = summaryMap.get(quota.appointmentDate) || {
      date: quota.appointmentDate,
      totalRemaining: 0,
      totalReserved: 0,
      totalCapacity: 0,
      availableDoctors: 0,
      doctorCount: roomDoctors.length,
    };

    current.totalRemaining += quota.remainingCount;
    current.totalReserved += quota.reservedCount;
    current.totalCapacity += quota.capacity;
    if (quota.remainingCount > 0) {
      current.availableDoctors += 1;
    }

    summaryMap.set(quota.appointmentDate, current);
  }

  return [...summaryMap.values()]
    .sort((left, right) => left.date.localeCompare(right.date))
    .map((item) => ({
      ...item,
      status: item.availableDoctors === 0 ? "full" : item.availableDoctors === item.doctorCount ? "available" : "partial",
      label:
        item.availableDoctors === 0
          ? "已满"
          : item.availableDoctors === item.doctorCount
            ? "可约"
            : "部分可约",
    }));
});
const appointmentDateSummaryMap = computed(
  () => new Map(appointmentDateSummaries.value.map((item) => [item.date, item])),
);
const appointmentMaxUnlockedStep = computed(() => {
  if (!appointmentForm.hospitalId) {
    return 1;
  }

  if (!appointmentForm.roomId) {
    return 2;
  }

  if (!appointmentForm.doctorId || !appointmentForm.appointmentDate) {
    return 3;
  }

  return 4;
});
const appointmentStepItems = computed(() => [
  {
    step: 1,
    label: "选医院",
    hint: "先看地址、诊室和简介",
  },
  {
    step: 2,
    label: "选诊室",
    hint: "比较诊室方向和医生配置",
  },
  {
    step: 3,
    label: "选医生",
    hint: "结合擅长方向和出诊时段",
  },
  {
    step: 4,
    label: "填信息",
    hint: "确认资料并完成预约",
  },
]);
const isAppointmentSlotFull = computed(() => appointmentQuota.value?.remainingCount === 0);
const bookedSlotKeys = computed(
  () =>
    new Set(
      userAppointments.value
        .filter((item) => item?.status === "已预约")
        .map((item) => buildSlotKey(item.doctorId, item.appointmentDate, item.timeSlot)),
    ),
);
const isCurrentSlotBooked = computed(() =>
  isSlotBooked(appointmentForm.doctorId, appointmentForm.appointmentDate, appointmentForm.timeSlot),
);
const visibleHospitals = computed(() => adminHospitals.value.filter(Boolean));
const visibleRooms = computed(() => adminRooms.value.filter(Boolean));
const visibleDoctors = computed(() => adminDoctors.value.filter(Boolean));
const visibleAppointments = computed(() => appointments.value.filter(Boolean));
const homeAppointments = computed(() =>
  [...userAppointments.value]
    .filter(Boolean)
    .filter((appointment) => appointment.status === "已预约")
    .map((appointment) => {
      const hospitalId = Number(appointment.hospitalId);
      const roomId = Number(appointment.roomId);
      const hospital = hospitals.value.find((item) => Number(item?.id) === hospitalId);
      const room = rooms.value.find((item) => Number(item?.id) === roomId);

      return {
        ...appointment,
        hospitalLocation: hospital?.location || "",
        roomFloor: room?.floor || "",
      };
    })
    .sort((left, right) => {
      const leftValue = `${left.appointmentDate || ""} ${left.timeSlot || ""}`;
      const rightValue = `${right.appointmentDate || ""} ${right.timeSlot || ""}`;
      return rightValue.localeCompare(leftValue);
    }),
);
const selectedHospitalIds = ref([]);
const selectedRoomIds = ref([]);
const selectedDoctorIds = ref([]);
const selectedAppointmentIds = ref([]);

const currentSelection = computed(() => {
  if (activeModule.value === "hospital") {
    return selectedHospitalIds.value;
  }

  if (activeModule.value === "room") {
    return selectedRoomIds.value;
  }

  if (activeModule.value === "doctor") {
    return selectedDoctorIds.value;
  }

  return selectedAppointmentIds.value;
});

const currentVisibleItems = computed(() => {
  if (activeModule.value === "hospital") {
    return visibleHospitals.value;
  }

  if (activeModule.value === "room") {
    return visibleRooms.value;
  }

  if (activeModule.value === "doctor") {
    return visibleDoctors.value;
  }

  return visibleAppointments.value;
});
const currentAdminPagination = computed(() => {
  if (activeModule.value === "hospital") {
    return adminPagination.hospital;
  }

  if (activeModule.value === "room") {
    return adminPagination.room;
  }

  if (activeModule.value === "doctor") {
    return adminPagination.doctor;
  }

  return null;
});

const isAllSelected = computed(
  () =>
    currentVisibleItems.value.length > 0 &&
    currentSelection.value.length === currentVisibleItems.value.length,
);

const hospitalOptions = computed(() =>
  hospitals.value
    .filter(Boolean)
    .map((hospital) => ({
      label: hospital.name,
      value: hospital.id,
    })),
);

const roomOptions = computed(() => {
  const currentHospitalId = Number(doctorForm.hospitalId);

  return rooms.value
    .filter((room) => room && (!currentHospitalId || room.hospitalId === currentHospitalId))
    .map((room) => ({
      label: `${room.name} · ${getHospitalName(room.hospitalId)}`,
      value: room.id,
    }));
});

const appointmentRoomOptions = computed(() => {
  const hospitalId = Number(appointmentForm.hospitalId);

  return rooms.value
    .filter((room) => room && (!hospitalId || room.hospitalId === hospitalId))
    .map((room) => ({
      label: `${room.name} · ${getHospitalName(room.hospitalId)}`,
      value: room.id,
    }));
});

const appointmentDoctorOptions = computed(() => {
  const hospitalId = Number(appointmentForm.hospitalId);
  const roomId = Number(appointmentForm.roomId);

  return doctors.value
    .filter(
      (doctor) =>
        doctor &&
        (!hospitalId || doctor.hospitalId === hospitalId) &&
        (!roomId || doctor.roomId === roomId) &&
        doctor.workTimeSlot === appointmentForm.timeSlot,
    )
    .map((doctor) => ({
      label: `${doctor.name} · ${doctor.title} · ${doctor.workTimeSlot}`,
      value: doctor.id,
    }));
});

const appointmentDoctorCards = computed(() => {
  const hospitalId = Number(appointmentForm.hospitalId);
  const roomId = Number(appointmentForm.roomId);

  return doctors.value
    .filter(
      (doctor) =>
        doctor &&
        (!hospitalId || doctor.hospitalId === hospitalId) &&
        (!roomId || doctor.roomId === roomId),
    )
    .sort((left, right) => workTimeOptions.indexOf(left.workTimeSlot) - workTimeOptions.indexOf(right.workTimeSlot));
});

const filterRoomOptions = computed(() => {
  const hospitalId = Number(filters.hospitalId);

  return rooms.value
    .filter((room) => room && (!hospitalId || room.hospitalId === hospitalId))
    .map((room) => ({
      label: `${room.name} · ${getHospitalName(room.hospitalId)}`,
      value: room.id,
    }));
});

function normalizeText(value) {
  return String(value ?? "").toLowerCase();
}

function formatLocalDate(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function matchesKeyword(values) {
  if (!normalizedKeyword.value) {
    return true;
  }

  return values.some((value) => normalizeText(value).includes(normalizedKeyword.value));
}

function buildSlotKey(doctorId, appointmentDate, timeSlot) {
  return `${doctorId || ""}|${appointmentDate || ""}|${timeSlot || ""}`;
}

function isSlotBooked(doctorId, appointmentDate, timeSlot) {
  if (!doctorId || !appointmentDate || !timeSlot) {
    return false;
  }

  return bookedSlotKeys.value.has(buildSlotKey(doctorId, appointmentDate, timeSlot));
}

function getDoctorQuotaForSelectedDate(doctorId) {
  return selectedDateDoctorQuotaMap.value.get(Number(doctorId)) || null;
}

function getDateSummaryLabel(dateString) {
  return appointmentDateSummaryMap.value.get(dateString)?.label || "待加载";
}

function getDateSummary(dateString) {
  return appointmentDateSummaryMap.value.get(dateString) || null;
}

function getCalendarCellDateString(cell) {
  return cell?.dayjs?.format("YYYY-MM-DD") || "";
}

function getCalendarCellSummary(cell) {
  return getDateSummary(getCalendarCellDateString(cell));
}

function isCalendarOutsideMonth(cell) {
  return cell?.type === "prev-month" || cell?.type === "next-month";
}

function getAppointmentWindowStartDateString() {
  return formatLocalDate(new Date());
}

function getAppointmentWindowEndDateString() {
  return formatLocalDate(new Date(Date.now() + APPOINTMENT_DATE_FUTURE_DAYS * 24 * 60 * 60 * 1000));
}

function isDateInAppointmentWindow(dateString) {
  if (!dateString) {
    return false;
  }

  return dateString >= getAppointmentWindowStartDateString() && dateString <= getAppointmentWindowEndDateString();
}

function getCalendarCellMeta(cell) {
  if (isCalendarOutsideMonth(cell)) {
    return null;
  }

  const dateString = getCalendarCellDateString(cell);
  if (!isDateInAppointmentWindow(dateString)) {
    return null;
  }

  const summary = getCalendarCellSummary(cell);

  if (summary) {
    return {
      status: getDateSummaryLabel(dateString),
      lines: [`可约 ${summary.availableDoctors} 位医生`, `剩余 ${summary.totalRemaining} 个号`],
    };
  }
  return {
    status: "待放号",
    lines: ["暂无号源", "请换日期"],
  };
}

function formatAppointmentCardDate(dateString) {
  if (!dateString) {
    return "";
  }

  const date = new Date(`${dateString}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return dateString;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
  }).format(date);
}

function formatAppointmentCardWeekday(dateString) {
  if (!dateString) {
    return "";
  }

  const date = new Date(`${dateString}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    weekday: "short",
  }).format(date);
}

function getDateSummaryLine(dateString) {
  const summary = appointmentDateSummaryMap.value.get(dateString);
  if (!summary) {
    return "号源信息加载中";
  }

  if (summary.availableDoctors === 0) {
    return `当日全部排满，共 ${summary.doctorCount} 位医生`;
  }

  return `可约 ${summary.availableDoctors} 位医生，剩余 ${summary.totalRemaining} 个号`;
}

function disabledAppointmentDate(date) {
  const dateString = formatLocalDate(date);
  const startDate = getAppointmentWindowStartDateString();
  const endDate = getAppointmentWindowEndDateString();

  if (!dateString || dateString < startDate || dateString > endDate) {
    return true;
  }

  if (!selectedAppointmentRoomDoctors.value.length) {
    return false;
  }

  const summary = appointmentDateSummaryMap.value.get(dateString);
  return Boolean(summary && summary.availableDoctors === 0);
}

function handleAppointmentDateChange(value) {
  if (!value) {
    appointmentQuota.value = null;
    return;
  }

  const selectedDoctorQuota = getDoctorQuotaForSelectedDate(appointmentForm.doctorId);
  if (selectedDoctorQuota) {
    appointmentQuota.value = selectedDoctorQuota;
    return;
  }

  loadAppointmentQuota();
}

function toggleAppointmentDate(dateString) {
  if (!dateString) {
    return;
  }

  if (appointmentForm.appointmentDate === dateString) {
    appointmentForm.appointmentDate = "";
    appointmentForm.doctorId = null;
    appointmentQuota.value = null;
    return;
  }

  appointmentForm.appointmentDate = dateString;
  handleAppointmentDateChange(dateString);
}

async function submitAuth() {
  if (authMode.value === AUTH_MODE_ADMIN) {
    if (!authForm.password.trim()) {
      ElMessage.warning("请输入管理员口令");
      return;
    }
  } else if (!authForm.phone.trim() || !authForm.password.trim()) {
    ElMessage.warning("请输入手机号和密码");
    return;
  }

  if (authMode.value === AUTH_MODE_REGISTER && !authForm.name.trim()) {
    ElMessage.warning("请输入姓名");
    return;
  }

  isAuthenticating.value = true;

  try {
    const auth =
      authMode.value === AUTH_MODE_REGISTER
        ? await register({
            phone: authForm.phone.trim(),
            password: authForm.password,
            name: authForm.name.trim(),
          })
        : authMode.value === AUTH_MODE_ADMIN
          ? await login({
              phone: ADMIN_PHONE,
              password: authForm.password.trim(),
            })
        : await login({
            phone: authForm.phone.trim(),
            password: authForm.password,
          });

    currentUser.value = auth;
    storeAuth(auth);
    clearConsultSessionLocally();
    applyLoggedInUserToAppointment();
    authForm.password = "";
    authForm.name = "";
    authForm.phone = "";
    currentView.value = "home";
    pushRouteState();
    ElMessage.success(authMode.value === AUTH_MODE_REGISTER ? "注册并登录成功" : "登录成功");
  } catch (error) {
    ElMessage.error(error.message || "登录失败");
  } finally {
    isAuthenticating.value = false;
  }
}

async function logoutCurrentUser() {
  try {
    await logout();
  } catch {
    // Local logout should still work even when the server session has expired.
  }

  clearStoredAuth();
  currentUser.value = null;
  clearConsultSessionLocally();
  userAppointments.value = [];
  appointments.value = [];
  currentView.value = "home";
  pushRouteState();
  ElMessage.success("已退出登录");
}

function switchAuthMode(mode) {
  authMode.value = mode;
  authForm.password = "";
  if (mode === AUTH_MODE_ADMIN) {
    authForm.phone = "";
    authForm.name = "";
  }
}

function resetToLoginOnSessionExpired(message = "登录状态已过期，请重新登录") {
  clearStoredAuth();
  currentUser.value = null;
  userAppointments.value = [];
  appointments.value = [];
  consultResult.value = null;
  consultRecommendations.value = [];
  consultRecommendationCollapseNames.value = [];
  consultMessages.value = [];
  activeConsultSymptom.value = "";
  consultConversationId.value = "";
  activeConsultAssistantMessageId.value = "";
  authMode.value = AUTH_MODE_LOGIN;
  authForm.password = "";
  currentView.value = "home";
  pushRouteState();
  ElMessage.warning(message);
}

function ensureLoggedIn(message = "请先登录") {
  if (isLoggedIn.value) {
    return true;
  }

  currentView.value = "home";
  pushRouteState();
  ElMessage.warning(message);
  return false;
}

function ensureAdminLoggedIn(message = "只有管理员可以访问后台管理") {
  if (isAdminUser.value) {
    return true;
  }

  currentView.value = "home";
  pushRouteState();
  ElMessage.warning(message);
  return false;
}

function applyLoggedInUserToAppointment() {
  if (!currentUser.value || currentUser.value.role === "ADMIN") {
    return;
  }

  appointmentForm.patientPhone = currentUser.value.phone;
  if (!appointmentForm.patientName) {
    appointmentForm.patientName = currentUser.value.name;
  }
}

function getRouteState() {
  if (typeof window === "undefined") {
    return {};
  }

  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  const module = params.get("module");

  return {
    view: validViews.includes(view) ? view : null,
    module: validModules.includes(module) ? module : null,
  };
}

function buildRouteUrl(view = currentView.value, module = activeModule.value) {
  if (typeof window === "undefined") {
    return "";
  }

  const url = new URL(window.location.href);
  url.search = "";

  if (view !== "home") {
    url.searchParams.set("view", view);
  }

  if (view === "admin") {
    url.searchParams.set("module", module);
  }

  return `${url.pathname}${url.search}${url.hash}`;
}

function pushRouteState() {
  if (typeof window === "undefined" || isApplyingBrowserRoute) {
    return;
  }

  const nextUrl = buildRouteUrl();
  const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;

  if (nextUrl !== currentUrl) {
    window.history.pushState({ view: currentView.value, module: activeModule.value }, "", nextUrl);
  }
}

async function applyRouteState({ view, module }) {
  isApplyingBrowserRoute = true;
  currentView.value =
    (
      (view === "admin" && !isAdminUser.value) ||
      (view === "appointment" && !isLoggedIn.value) ||
      (view === "consult" && !isLoggedIn.value) ||
      (view === "rag" && !isLoggedIn.value)
    )
      ? "home"
      : view || "home";

  if (module && validModules.includes(module)) {
    activeModule.value = module;
  }

  isApplyingBrowserRoute = false;

  if (currentView.value === "admin") {
    await loadAdminCatalog();
  } else if (currentView.value === "appointment") {
    await loadAppointmentResources();
  } else if (currentView.value === "consult") {
    await loadConsultSessionState();
  } else if (currentView.value === "rag") {
    await loadRagDashboard();
  }
}

async function loadRagDashboard() {
  if (!ensureLoggedIn("请先登录后再查看知识库")) {
    return;
  }

  isLoadingRag.value = true;

  try {
    const [stats, docs] = await Promise.all([
      getRagStats(),
      listRagDocuments(ragDocumentLimit.value),
    ]);

    ragStats.value = stats;
    ragDocuments.value = (docs.ids || []).map((id, index) => ({
      id,
      text: docs.documents?.[index] || "",
      metadata: docs.metadatas?.[index] || {},
    }));
  } catch (error) {
    ElMessage.error(error.message || "知识库数据加载失败");
  } finally {
    isLoadingRag.value = false;
  }
}

async function loadAdminCatalog() {
  if (!ensureAdminLoggedIn("只有管理员可以访问后台管理")) {
    return;
  }

  isLoadingCatalog.value = true;

  try {
    const [hospitalItems, roomItems, appointmentItems] = await Promise.all([
      listHospitals(),
      listRooms(),
      listAdminAppointments(),
    ]);

    hospitals.value = hospitalItems;
    rooms.value = roomItems;
    appointments.value = appointmentItems;
    await loadAdminModulePage();
    pruneSelections();
  } catch (error) {
    ElMessage.error(error.message || "后台数据加载失败");
  } finally {
    isLoadingCatalog.value = false;
  }
}

function pruneSelections() {
  selectedHospitalIds.value = selectedHospitalIds.value.filter((id) =>
    adminHospitals.value.some((hospital) => hospital.id === id),
  );
  selectedRoomIds.value = selectedRoomIds.value.filter((id) =>
    adminRooms.value.some((room) => room.id === id),
  );
  selectedDoctorIds.value = selectedDoctorIds.value.filter((id) =>
    adminDoctors.value.some((doctor) => doctor.id === id),
  );
  selectedAppointmentIds.value = selectedAppointmentIds.value.filter((id) =>
    appointments.value.some((appointment) => appointment.id === id),
  );
}

function getHospitalName(hospitalId) {
  return hospitals.value.find((hospital) => hospital?.id === hospitalId)?.name ?? "未关联医院";
}

function getRoomName(roomId) {
  return rooms.value.find((room) => room?.id === roomId)?.name ?? "未关联诊室";
}

function sortRoomsByPresentation(left, right) {
  return String(left?.floor ?? "").localeCompare(String(right?.floor ?? ""), "zh-Hans-CN")
    || String(left?.name ?? "").localeCompare(String(right?.name ?? ""), "zh-Hans-CN");
}

function sortDoctorsBySchedule(left, right) {
  return workTimeOptions.indexOf(left?.workTimeSlot) - workTimeOptions.indexOf(right?.workTimeSlot)
    || String(left?.name ?? "").localeCompare(String(right?.name ?? ""), "zh-Hans-CN");
}

function getHospitalRooms(hospitalId) {
  const normalizedHospitalId = Number(hospitalId);
  if (!normalizedHospitalId) {
    return [];
  }

  return rooms.value
    .filter((room) => room?.hospitalId === normalizedHospitalId)
    .sort(sortRoomsByPresentation);
}

function getHospitalDoctors(hospitalId) {
  const normalizedHospitalId = Number(hospitalId);
  if (!normalizedHospitalId) {
    return [];
  }

  return doctors.value
    .filter((doctor) => doctor?.hospitalId === normalizedHospitalId)
    .sort(sortDoctorsBySchedule);
}

function getRoomDoctors(roomId) {
  const normalizedRoomId = Number(roomId);
  if (!normalizedRoomId) {
    return [];
  }

  return doctors.value
    .filter((doctor) => doctor?.roomId === normalizedRoomId)
    .sort(sortDoctorsBySchedule);
}

function getAppointmentStepDescription() {
  if (appointmentStep.value === 1) {
    return "先看医院位置、等级与资源分布，再决定去哪里就诊。";
  }

  if (appointmentStep.value === 2) {
    return "在已选医院里继续比较诊室介绍、楼层位置和医生配置。";
  }

  if (appointmentStep.value === 3) {
    return "先选预约日期，再根据医生擅长方向和出诊时段完成医生选择。";
  }

  return "最后确认预约路径，填写就诊人资料并提交预约。";
}

function getAppointmentStepTitle() {
  if (appointmentStep.value === 1) {
    return "第一步：先选医院";
  }

  if (appointmentStep.value === 2) {
    return "第二步：再选诊室";
  }

  if (appointmentStep.value === 3) {
    return "第三步：选医生与预约日期";
  }

  return "第四步：填写就诊人信息";
}

function openAppointmentStep(step) {
  appointmentStep.value = Math.max(1, Math.min(step, appointmentMaxUnlockedStep.value));
}

function isHospitalPreviewExpanded(hospitalId) {
  return expandedHospitalIds.value.includes(Number(hospitalId));
}

function isRoomDoctorPreviewExpanded(roomId) {
  return expandedRoomIds.value.includes(Number(roomId));
}

function showHospitalDetails(hospitalId) {
  browsedHospitalId.value = Number(hospitalId);
}

function showRoomDetails(roomId) {
  browsedRoomId.value = Number(roomId);
}

function toggleHospitalPreview(hospitalId) {
  const normalizedHospitalId = Number(hospitalId);
  showHospitalDetails(normalizedHospitalId);
  if (isHospitalPreviewExpanded(normalizedHospitalId)) {
    expandedHospitalIds.value = expandedHospitalIds.value.filter((id) => id !== normalizedHospitalId);
    return;
  }

  expandedHospitalIds.value = [...expandedHospitalIds.value, normalizedHospitalId];
}

function toggleRoomDoctorPreview(roomId) {
  const normalizedRoomId = Number(roomId);
  showRoomDetails(normalizedRoomId);
  if (isRoomDoctorPreviewExpanded(normalizedRoomId)) {
    expandedRoomIds.value = expandedRoomIds.value.filter((id) => id !== normalizedRoomId);
    return;
  }

  expandedRoomIds.value = [...expandedRoomIds.value, normalizedRoomId];
}

function selectAppointmentHospital(hospital) {
  showHospitalDetails(hospital.id);
  appointmentForm.hospitalId = hospital.id;
  appointmentForm.roomId = null;
  appointmentForm.doctorId = null;
  appointmentForm.appointmentDate = "";
  appointmentForm.timeSlot = workTimeOptions[0];
  appointmentQuota.value = null;
  appointmentCalendarQuotas.value = [];
  openAppointmentStep(2);
}

async function selectAppointmentRoom(room) {
  showHospitalDetails(room.hospitalId);
  showRoomDetails(room.id);
  appointmentForm.hospitalId = room.hospitalId;
  appointmentForm.roomId = room.id;
  appointmentForm.doctorId = null;
  appointmentForm.appointmentDate = "";
  appointmentForm.timeSlot = workTimeOptions[0];
  appointmentQuota.value = null;
  await loadAppointmentCalendarQuota(room.id);
  openAppointmentStep(3);
}

function selectAppointmentDoctor(doctor) {
  if (!appointmentForm.appointmentDate) {
    ElMessage.warning("请先选择预约日期，再继续选择医生");
    return;
  }

  showHospitalDetails(doctor.hospitalId);
  showRoomDetails(doctor.roomId);
  appointmentForm.hospitalId = doctor.hospitalId;
  appointmentForm.roomId = doctor.roomId;
  appointmentForm.doctorId = doctor.id;
  appointmentForm.timeSlot = doctor.workTimeSlot || workTimeOptions[0];

  const doctorQuota = getDoctorQuotaForSelectedDate(doctor.id);
  if (doctorQuota?.remainingCount === 0) {
    ElMessage.warning("该医生在所选日期的号源已满，请选择其他医生或日期");
    appointmentQuota.value = doctorQuota;
    return;
  }

  applyLoggedInUserToAppointment();
  appointmentQuota.value = doctorQuota || null;
  loadAppointmentQuota();
  openAppointmentStep(4);
}

function ensureAppointmentSelectionConsistency() {
  const normalizedHospitalId = Number(appointmentForm.hospitalId);
  const normalizedRoomId = Number(appointmentForm.roomId);
  const normalizedDoctorId = Number(appointmentForm.doctorId);

  const hospitalExists = hospitals.value.some((hospital) => hospital?.id === normalizedHospitalId);
  if (!hospitalExists) {
    appointmentForm.hospitalId = null;
    appointmentForm.roomId = null;
    appointmentForm.doctorId = null;
    appointmentForm.appointmentDate = "";
    appointmentForm.timeSlot = workTimeOptions[0];
    appointmentQuota.value = null;
    appointmentCalendarQuotas.value = [];
    browsedHospitalId.value = appointmentHospitals.value[0]?.id ?? null;
    browsedRoomId.value = null;
    appointmentStep.value = 1;
    return;
  }

  const roomExists = rooms.value.some(
    (room) => room?.id === normalizedRoomId && room.hospitalId === normalizedHospitalId,
  );
  if (!roomExists) {
    appointmentForm.roomId = null;
    appointmentForm.doctorId = null;
    appointmentForm.appointmentDate = "";
    appointmentForm.timeSlot = workTimeOptions[0];
    appointmentQuota.value = null;
    appointmentCalendarQuotas.value = [];
    browsedHospitalId.value = normalizedHospitalId;
    browsedRoomId.value = getHospitalRooms(normalizedHospitalId)[0]?.id ?? null;
    appointmentStep.value = 2;
    return;
  }

  const doctor = doctors.value.find(
    (item) =>
      item?.id === normalizedDoctorId &&
      item.hospitalId === normalizedHospitalId &&
      item.roomId === normalizedRoomId,
  );

  if (!doctor) {
    appointmentForm.doctorId = null;
    appointmentQuota.value = null;
    browsedHospitalId.value = normalizedHospitalId;
    browsedRoomId.value = normalizedRoomId;
    appointmentStep.value = 3;
    return;
  }

  browsedHospitalId.value = normalizedHospitalId;
  browsedRoomId.value = normalizedRoomId;
  appointmentForm.timeSlot = doctor.workTimeSlot || appointmentForm.timeSlot;
  appointmentStep.value = appointmentForm.appointmentDate ? Math.min(Math.max(appointmentStep.value, 4), 4) : 3;
}

async function goToAdmin() {
  if (!ensureAdminLoggedIn("只有管理员可以访问后台管理")) {
    return;
  }

  currentView.value = "admin";
  pushRouteState();
  await loadAdminCatalog();
}

async function goToAppointment() {
  if (!ensureLoggedIn("请先登录后再预约")) {
    return;
  }

  currentView.value = "appointment";
  pushRouteState();
  await loadAppointmentResources();
}

async function goToConsult() {
  if (!ensureLoggedIn("请先登录后再使用 AI 问诊")) {
    return;
  }

  currentView.value = "consult";
  pushRouteState();
  await loadConsultSessionState();
}

async function goToRag() {
  if (!ensureLoggedIn("请先登录后再查看知识库")) {
    return;
  }

  currentView.value = "rag";
  pushRouteState();
  await loadRagDashboard();
}

function goHome() {
  currentView.value = "home";
  pushRouteState();

  if (isLoggedIn.value && !isAdminUser.value) {
    loadHomeAppointments();
  }
}

async function refreshRagDocuments() {
  await loadRagDashboard();
}

async function submitRagSearch() {
  if (!ragSearchForm.query.trim()) {
    ElMessage.warning("请输入检索关键词");
    return;
  }

  isSearchingRag.value = true;
  try {
    const result = await searchRagDocuments({
      query: ragSearchForm.query.trim(),
      top_k: Number(ragSearchForm.topK) || 5,
    });
    ragSearchResults.value = result.results || [];
  } catch (error) {
    ElMessage.error(error.message || "知识库检索失败");
  } finally {
    isSearchingRag.value = false;
  }
}

function formatMetadata(metadata) {
  return JSON.stringify(metadata || {}, null, 2);
}

function switchModule(moduleKey) {
  activeModule.value = moduleKey;
  resetFilters();
  resetAdminPagination(moduleKey);
  pushRouteState();
  if (currentView.value === "admin") {
    loadAdminCatalog();
  }
}

function isSelected(type, id) {
  return getSelectionRef(type).value.includes(id);
}

function toggleSelection(type, id) {
  const selection = getSelectionRef(type).value;
  const index = selection.indexOf(id);

  if (index === -1) {
    selection.push(id);
    return;
  }

  selection.splice(index, 1);
}

function toggleSelectAllCurrentModule() {
  const selectionRef = getSelectionRef(activeModule.value);

  if (isAllSelected.value) {
    selectionRef.value = [];
    return;
  }

  selectionRef.value = currentVisibleItems.value.map((item) => item.id);
}

function clearCurrentSelection() {
  getSelectionRef(activeModule.value).value = [];
}

function resetFilters() {
  filters.keyword = "";
  filters.hospitalId = "";
  filters.roomId = "";
  filters.workTimeSlot = "";
}

function resetAdminPagination(moduleKey = activeModule.value) {
  const target = adminPagination[moduleKey];
  if (target) {
    target.page = 1;
  }
}

function syncFilterRooms() {
  const roomStillVisible = rooms.value.some(
    (room) =>
      room.id === Number(filters.roomId) &&
      (!filters.hospitalId || room.hospitalId === Number(filters.hospitalId)),
  );

  if (!roomStillVisible) {
    filters.roomId = "";
  }
}

async function loadAdminModulePage() {
  if (activeModule.value === "hospital") {
    const result = await listAdminHospitals({
      page: adminPagination.hospital.page - 1,
      size: adminPagination.hospital.size,
      keyword: filters.keyword.trim(),
    });
    adminHospitals.value = result.items || [];
    adminPagination.hospital.total = result.totalElements || 0;
    return;
  }

  if (activeModule.value === "room") {
    const result = await listAdminRooms({
      page: adminPagination.room.page - 1,
      size: adminPagination.room.size,
      keyword: filters.keyword.trim(),
      hospitalId: filters.hospitalId || undefined,
    });
    adminRooms.value = result.items || [];
    adminPagination.room.total = result.totalElements || 0;
    return;
  }

  if (activeModule.value === "doctor") {
    const result = await listAdminDoctors({
      page: adminPagination.doctor.page - 1,
      size: adminPagination.doctor.size,
      keyword: filters.keyword.trim(),
      hospitalId: filters.hospitalId || undefined,
      roomId: filters.roomId || undefined,
      workTimeSlot: filters.workTimeSlot || undefined,
    });
    adminDoctors.value = result.items || [];
    adminPagination.doctor.total = result.totalElements || 0;
  }
}

async function handleAdminPageChange(page) {
  const target = currentAdminPagination.value;
  if (!target) {
    return;
  }
  target.page = page;
  await loadAdminCatalog();
}

async function handleAdminPageSizeChange(size) {
  const target = currentAdminPagination.value;
  if (!target) {
    return;
  }
  target.size = size;
  target.page = 1;
  await loadAdminCatalog();
}

function getSelectionRef(type) {
  if (type === "hospital") {
    return selectedHospitalIds;
  }

  if (type === "room") {
    return selectedRoomIds;
  }

  if (type === "doctor") {
    return selectedDoctorIds;
  }

  return selectedAppointmentIds;
}

async function loadAppointmentResources() {
  if (!ensureLoggedIn("请先登录后再预约")) {
    return;
  }

  isLoadingCatalog.value = true;

  try {
    applyLoggedInUserToAppointment();

    const [hospitalItems, roomItems, doctorItems, appointmentItems] = await Promise.all([
      listHospitals(),
      listRooms(),
      listDoctors(),
      isLoggedIn.value ? listAppointments() : Promise.resolve([]),
    ]);

    hospitals.value = hospitalItems;
    rooms.value = roomItems;
    doctors.value = doctorItems;
    userAppointments.value = appointmentItems;
    if (!browsedHospitalId.value && hospitals.value.length) {
      browsedHospitalId.value = hospitals.value[0].id;
    }
    ensureAppointmentSelectionConsistency();

    if (appointmentForm.roomId) {
      await loadAppointmentCalendarQuota(appointmentForm.roomId);
    } else {
      appointmentCalendarQuotas.value = [];
    }

    if (appointmentForm.doctorId && appointmentForm.appointmentDate) {
      await loadAppointmentQuota();
    }
  } catch (error) {
    ElMessage.error(error.message || "预约资源加载失败");
  } finally {
    isLoadingCatalog.value = false;
  }
}

async function loadHomeAppointments() {
  if (!isLoggedIn.value || isAdminUser.value) {
    userAppointments.value = [];
    return;
  }

  try {
    const [appointmentItems, hospitalItems, roomItems] = await Promise.all([
      listAppointments(),
      hospitals.value.length ? Promise.resolve(hospitals.value) : listHospitals(),
      rooms.value.length ? Promise.resolve(rooms.value) : listRooms(),
    ]);

    userAppointments.value = appointmentItems;
    hospitals.value = hospitalItems;
    rooms.value = roomItems;
  } catch (error) {
    ElMessage.error(error.message || "我的预约加载失败");
  }
}

function showDetail(type, item) {
  detailDialog.type = type;
  detailDialog.item = item;
  detailDialog.visible = true;
}

function openCreateDialog(type) {
  editorDialog.type = type;
  editorDialog.mode = "create";
  resetForm(type);
  editorDialog.visible = true;
}

function openEditDialog(type, item) {
  editorDialog.type = type;
  editorDialog.mode = "edit";
  resetForm(type);

  if (type === "hospital") {
    Object.assign(hospitalForm, item);
  } else if (type === "room") {
    Object.assign(roomForm, item);
  } else {
    Object.assign(doctorForm, item);
    doctorForm.workTimeSlot = item.workTimeSlot || "上午 08:30-10:30";
  }

  editorDialog.visible = true;
}

function resetForm(type) {
  if (type === "hospital") {
    Object.assign(hospitalForm, {
      id: null,
      name: "",
      level: "",
      location: "",
      shortIntro: "",
      detailIntro: "",
    });
  } else if (type === "room") {
    Object.assign(roomForm, {
      id: null,
      hospitalId: hospitals.value[0]?.id ?? null,
      name: "",
      floor: "",
      shortIntro: "",
      detailIntro: "",
    });
  } else {
    Object.assign(doctorForm, {
      id: null,
      hospitalId: hospitals.value[0]?.id ?? null,
      roomId: null,
      name: "",
      title: "",
      specialty: "",
      workTimeSlot: "上午 08:30-10:30",
      shortIntro: "",
      detailIntro: "",
    });

    const initialRoom = rooms.value.find((room) => room?.hospitalId === doctorForm.hospitalId);
    doctorForm.roomId = initialRoom?.id ?? null;
  }
}

function syncDoctorRoomOptions() {
  const firstRoom = rooms.value.find((room) => room?.hospitalId === Number(doctorForm.hospitalId));

  if (!firstRoom) {
    doctorForm.roomId = null;
    return;
  }

  const currentRoomBelongsToHospital = rooms.value.some(
    (room) => room?.id === Number(doctorForm.roomId) && room.hospitalId === Number(doctorForm.hospitalId),
  );

  if (!currentRoomBelongsToHospital) {
    doctorForm.roomId = firstRoom.id;
  }
}

function syncAppointmentRoomOptions() {
  const firstRoom = rooms.value.find((room) => room?.hospitalId === Number(appointmentForm.hospitalId));
  appointmentForm.roomId = firstRoom?.id ?? null;
  syncAppointmentDoctorOptions();
}

function syncAppointmentDoctorOptions() {
  const firstDoctor = doctors.value.find(
    (doctor) =>
      doctor?.hospitalId === Number(appointmentForm.hospitalId) &&
      doctor.roomId === Number(appointmentForm.roomId) &&
      doctor.workTimeSlot === appointmentForm.timeSlot,
  );
  appointmentForm.doctorId = firstDoctor?.id ?? null;
  loadAppointmentQuota();
}

function selectDoctorSlot(doctor) {
  appointmentForm.hospitalId = doctor.hospitalId;
  appointmentForm.roomId = doctor.roomId;
  appointmentForm.timeSlot = doctor.workTimeSlot || "上午 08:30-10:30";
  appointmentForm.doctorId = doctor.id;
  applyLoggedInUserToAppointment();
  loadAppointmentQuota();
}

async function loadAppointmentCalendarQuota(roomId = appointmentForm.roomId) {
  const normalizedRoomId = Number(roomId);
  const roomDoctors = getRoomDoctors(normalizedRoomId).filter((doctor) => doctor?.id && doctor.workTimeSlot);

  if (!normalizedRoomId || !roomDoctors.length) {
    appointmentCalendarQuotas.value = [];
    return;
  }

  isLoadingAppointmentCalendar.value = true;
  const startDate = formatLocalDate(new Date());
  const endDate = getAppointmentWindowEndDateString();

  try {
    const response = await getAppointmentQuotaCalendar({
      doctorIds: roomDoctors.map((doctor) => doctor.id),
      startDate,
      endDate,
    });
    appointmentCalendarQuotas.value = response?.quotas || [];

    if (appointmentForm.appointmentDate) {
      const summary = appointmentDateSummaryMap.value.get(appointmentForm.appointmentDate);
      if (summary?.availableDoctors === 0) {
        appointmentForm.appointmentDate = "";
        appointmentForm.doctorId = null;
        appointmentQuota.value = null;
      } else {
        const selectedDoctorQuota = getDoctorQuotaForSelectedDate(appointmentForm.doctorId);
        if (selectedDoctorQuota) {
          appointmentQuota.value = selectedDoctorQuota;
        }
      }
    }
  } catch (error) {
    appointmentCalendarQuotas.value = [];
    ElMessage.error(error.message || "日期号源加载失败");
  } finally {
    isLoadingAppointmentCalendar.value = false;
  }
}

async function loadAppointmentQuota() {
  if (!appointmentForm.doctorId || !appointmentForm.appointmentDate || !appointmentForm.timeSlot) {
    appointmentQuota.value = null;
    return;
  }

  const cachedQuota = getDoctorQuotaForSelectedDate(appointmentForm.doctorId);
  if (cachedQuota && cachedQuota.timeSlot === appointmentForm.timeSlot) {
    appointmentQuota.value = cachedQuota;
    return;
  }

  isLoadingQuota.value = true;

  try {
    appointmentQuota.value = await getAppointmentQuota({
      doctorId: Number(appointmentForm.doctorId),
      appointmentDate: appointmentForm.appointmentDate,
      timeSlot: appointmentForm.timeSlot,
    });
  } catch (error) {
    appointmentQuota.value = null;
    ElMessage.error(error.message || "号源查询失败");
  } finally {
    isLoadingQuota.value = false;
  }
}

async function submitAppointment() {
  if (!ensureLoggedIn("请先登录后再预约")) {
    return;
  }

  applyLoggedInUserToAppointment();

  if (
    !appointmentForm.hospitalId ||
    !appointmentForm.roomId ||
    !appointmentForm.doctorId ||
    !appointmentForm.patientName.trim() ||
    !appointmentForm.patientPhone.trim() ||
    !appointmentForm.appointmentDate ||
    !appointmentForm.timeSlot
  ) {
    ElMessage.warning("请完整填写预约信息");
    return;
  }

  if (isAppointmentSlotFull.value) {
    ElMessage.warning("该医生当前时间段预约已满");
    return;
  }

  if (isCurrentSlotBooked.value) {
    ElMessage.warning("你已预约该医生当前时间段，不能重复预约");
    return;
  }

  isSubmittingAppointment.value = true;

  try {
    await createAppointment({
      hospitalId: Number(appointmentForm.hospitalId),
      roomId: Number(appointmentForm.roomId),
      doctorId: Number(appointmentForm.doctorId),
      patientName: appointmentForm.patientName.trim(),
      patientPhone: appointmentForm.patientPhone.trim(),
      appointmentDate: appointmentForm.appointmentDate,
      timeSlot: appointmentForm.timeSlot,
      symptom: appointmentForm.symptom.trim(),
    });
    ElMessage.success("预约提交成功");
    await loadAppointmentResources();
    await loadAppointmentQuota();
    Object.assign(appointmentForm, {
      patientName: currentUser.value?.name ?? appointmentForm.patientName,
      patientPhone: currentUser.value?.phone ?? appointmentForm.patientPhone,
      symptom: "",
    });
  } catch (error) {
    ElMessage.error(error.message || "预约提交失败");
  } finally {
    isSubmittingAppointment.value = false;
  }
}

async function submitConsult() {
  if (isConsulting.value) {
    return;
  }

  if (!ensureLoggedIn("请先登录后再使用 AI 问诊")) {
    return;
  }

  if (!consultForm.symptom.trim()) {
    ElMessage.warning("请先描述你的症状或就诊诉求");
    return;
  }

  isConsulting.value = true;
  const previousConsultResult = consultResult.value;
  const previousConsultRecommendations = [...consultRecommendations.value];
  const previousConsultRecommendationRequested = consultRecommendationRequested.value;

  try {
    const symptom = consultForm.symptom.trim();
    activeConsultSymptom.value = symptom;
    consultForm.symptom = "";
    consultRecommendationRequested.value = false;
    consultRecommendationCollapseNames.value = [];
    consultRecommendations.value = [];
    consultResult.value = {
      symptom,
      recommendationQueryText: symptom,
      patientSummary: "正在整理你刚才描述的情况，请稍等。",
      inputCategory: "medical",
      departmentRecommendation: "问诊分析中",
      doctorRecommendation: [],
      reason: "正在结合你的描述和知识库内容生成问诊建议，请稍等。",
      generatedAnswer: "",
      followUpQuestions: [],
      urgency: "",
      showDoctorRecommendationAction: false,
      doctorRecommendationButtonText: "推荐医生",
      doctorRecommendationPrompt: "",
      answerMode: "streaming",
      disclaimer: "AI 推荐仅供辅助参考，不能替代医生诊断。",
      knowledgeReferences: [],
    };
    appendConsultUserMessage(symptom);
    activeConsultAssistantMessageId.value = appendConsultAssistantMessage(consultResult.value);

    await consultSymptomStream(
      {
        symptom,
        conversationId: consultConversationId.value || undefined,
      },
      {
        meta(payload) {
          if (payload?.conversationId) {
            consultConversationId.value = payload.conversationId;
          }
          consultResult.value = {
            ...consultResult.value,
            ...payload,
          };
          syncActiveConsultAssistantMessage(consultResult.value);
        },
        delta(payload) {
          if (!consultResult.value) {
            return;
          }

          consultResult.value = {
            ...consultResult.value,
            generatedAnswer: `${consultResult.value.generatedAnswer || ""}${payload?.text || ""}`,
          };
          syncActiveConsultAssistantMessage(consultResult.value);
        },
        complete(payload) {
          if (payload?.conversationId) {
            consultConversationId.value = payload.conversationId;
          }
          consultResult.value = payload;
          syncActiveConsultAssistantMessage(consultResult.value);
        },
      },
    );

    ElMessage.success("问诊分析已生成");
  } catch (error) {
    consultResult.value = previousConsultResult;
    consultRecommendations.value = previousConsultRecommendations;
    consultRecommendationRequested.value = previousConsultRecommendationRequested;
    markActiveConsultAssistantMessageAsError(error.message || "AI 问诊失败，请稍后重试。");
    ElMessage.error(error.message || "AI 问诊失败");
  } finally {
    activeConsultAssistantMessageId.value = "";
    isConsulting.value = false;
  }
}

function buildConsultAssistantMessageText(result) {
  if (!result) {
    return "正在结合你的描述生成问诊建议，请稍等。";
  }

  const parts = [];
  const summary = String(result.patientSummary || "").trim();
  const department = String(result.departmentRecommendation || "").trim();
  const urgencyLabel = getConsultUrgencyLabel(result.urgency);
  const reason = String(result.reason || "").trim();
  const generatedAnswer = String(result.generatedAnswer || "").trim();
  const followUpQuestions = getConsultFollowUpQuestions(result);

  if (summary && !summary.includes("正在整理")) {
    parts.push(`情况总结：${summary}`);
  }

  if (department) {
    parts.push(`推荐科室：${department}${urgencyLabel ? ` · ${urgencyLabel}` : ""}`);
  }

  if (reason) {
    parts.push(reason);
  }

  if (generatedAnswer && generatedAnswer !== reason) {
    parts.push(generatedAnswer);
  }

  if (followUpQuestions.length) {
    parts.push(`建议继续补充：\n${followUpQuestions.map((question) => `- ${question}`).join("\n")}`);
  }

  if (!parts.length) {
    return "正在结合你的描述生成问诊建议，请稍等。";
  }

  return parts.join("\n\n");
}

function createConsultMessage(role, text, state = "done") {
  consultMessageSequence += 1;
  return {
    id: `consult-${consultMessageSequence}`,
    role,
    text,
    state,
  };
}

function scrollConsultChatToBottom() {
  void nextTick(() => {
    const viewport = consultChatViewport.value;
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  });
}

function appendConsultUserMessage(text) {
  consultMessages.value = [
    ...consultMessages.value,
    createConsultMessage("user", String(text || "").trim()),
  ];
  scrollConsultChatToBottom();
}

function hydrateConsultMessagesFromHistory(history) {
  consultMessages.value = [];
  consultMessageSequence = 0;
  if (!Array.isArray(history)) {
    return;
  }

  const restoredMessages = history
    .map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const role = item.role === "assistant" ? "assistant" : item.role === "user" ? "user" : "";
      const text = String(item.content || "").trim();
      if (!role || !text) {
        return null;
      }
      return createConsultMessage(role, text, "done");
    })
    .filter(Boolean);

  consultMessages.value = restoredMessages;
  activeConsultSymptom.value = [...restoredMessages].reverse().find((item) => item.role === "user")?.text || "";
  scrollConsultChatToBottom();
}

function appendConsultAssistantMessage(result) {
  const message = createConsultMessage("assistant", buildConsultAssistantMessageText(result), "streaming");
  consultMessages.value = [...consultMessages.value, message];
  scrollConsultChatToBottom();
  return message.id;
}

function updateConsultMessage(messageId, updater) {
  consultMessages.value = consultMessages.value.map((message) => {
    if (message.id !== messageId) {
      return message;
    }
    return updater(message);
  });
  scrollConsultChatToBottom();
}

function syncActiveConsultAssistantMessage(result) {
  if (!activeConsultAssistantMessageId.value) {
    return;
  }

  updateConsultMessage(activeConsultAssistantMessageId.value, (message) => ({
    ...message,
    text: buildConsultAssistantMessageText(result),
    state: result?.answerMode === "streaming" ? "streaming" : "done",
  }));
}

function markActiveConsultAssistantMessageAsError(text) {
  if (!activeConsultAssistantMessageId.value) {
    return;
  }

  updateConsultMessage(activeConsultAssistantMessageId.value, (message) => ({
    ...message,
    text: String(text || "AI 问诊失败，请稍后重试。"),
    state: "error",
  }));
}

async function loadConsultSessionState() {
  if (!isLoggedIn.value) {
    return;
  }

  try {
    const session = await getConsultSession();
    consultConversationId.value = String(session?.conversationId || "").trim();
    hydrateConsultMessagesFromHistory(session?.history || []);
    consultResult.value = null;
    consultRecommendations.value = [];
    consultRecommendationCollapseNames.value = [];
    consultRecommendationRequested.value = false;
  } catch (error) {
    ElMessage.error(error.message || "问诊会话恢复失败");
  }
}

function getConsultRecommendationQueryText(result) {
  return String(result?.recommendationQueryText || activeConsultSymptom.value || "").trim();
}

function extractConsultQueryTokens(queryText) {
  const normalized = normalizeText(queryText);
  const keywordCandidates = [
    "发热", "发烧", "高热", "高烧", "咳嗽", "咳痰", "喘", "气短", "呼吸困难",
    "胸闷", "胸痛", "心悸", "高血压", "胃痛", "反酸", "腹痛", "腹泻", "便秘",
    "牙痛", "牙龈", "口腔", "失眠", "乏力", "儿童", "孩子", "宝宝", "孕", "产检",
    "胎动", "颈", "肩", "腰", "腿痛", "康复", "针灸",
  ];
  const tokens = new Set(
    queryText
      .split(/[，。,.、；;：:\s]+/)
      .map((token) => token.trim())
      .filter((token) => token.length >= 2),
  );

  for (const keyword of keywordCandidates) {
    if (normalized.includes(keyword)) {
      tokens.add(keyword);
    }
  }

  return [...tokens];
}

function extractConsultLocationHints(queryText) {
  const normalized = normalizeText(queryText);
  const hints = [];

  for (const [region, cities] of Object.entries(CONSULT_REGION_CITY_ALIASES)) {
    if (!normalized.includes(normalizeText(region))) {
      continue;
    }
    for (const city of cities) {
      if (!hints.includes(city)) {
        hints.push(city);
      }
    }
  }

  for (const city of CONSULT_DIRECT_CITY_HINTS) {
    if (normalized.includes(normalizeText(city)) && !hints.includes(city)) {
      hints.push(city);
    }
  }

  return hints;
}

function hospitalMatchesConsultLocationHints(hospital, locationHints) {
  if (!locationHints.length) {
    return true;
  }

  const searchableText = normalizeText([
    hospital?.name,
    hospital?.location,
    hospital?.shortIntro,
    hospital?.detailIntro,
  ].join(" "));

  return locationHints.some((hint) => searchableText.includes(normalizeText(hint)));
}

function canBuildConsultRecommendationCandidates(result) {
  const queryText = getConsultRecommendationQueryText(result);
  const normalizedDepartment = normalizeText(result?.departmentRecommendation);

  if (!queryText) {
    return false;
  }

  if (result?.inputCategory !== "medical") {
    return false;
  }

  if (result?.urgency === "emergency") {
    return false;
  }

  if (!normalizedDepartment) {
    return false;
  }

  return true;
}

function normalizeConsultRecommendationItem(item) {
  if (!item || typeof item !== "object") {
    return null;
  }

  const hospital = item.hospital && typeof item.hospital === "object"
    ? {
        id: Number(item.hospital.id),
        name: String(item.hospital.name || "").trim(),
        level: String(item.hospital.level || "").trim(),
        location: String(item.hospital.location || "").trim(),
        shortIntro: String(item.hospital.shortIntro || "").trim(),
        detailIntro: String(item.hospital.detailIntro || "").trim(),
      }
    : null;
  const room = item.room && typeof item.room === "object"
    ? {
        id: Number(item.room.id),
        hospitalId: Number(item.room.hospitalId),
        hospitalName: String(item.room.hospitalName || "").trim(),
        name: String(item.room.name || "").trim(),
        floor: String(item.room.floor || "").trim(),
        shortIntro: String(item.room.shortIntro || "").trim(),
        detailIntro: String(item.room.detailIntro || "").trim(),
      }
    : null;
  const doctor = item.doctor && typeof item.doctor === "object"
    ? {
        id: Number(item.doctor.id),
        hospitalId: Number(item.doctor.hospitalId),
        hospitalName: String(item.doctor.hospitalName || "").trim(),
        roomId: Number(item.doctor.roomId),
        roomName: String(item.doctor.roomName || "").trim(),
        name: String(item.doctor.name || "").trim(),
        title: String(item.doctor.title || "").trim(),
        specialty: String(item.doctor.specialty || "").trim(),
        workTimeSlot: String(item.doctor.workTimeSlot || "").trim(),
        shortIntro: String(item.doctor.shortIntro || "").trim(),
        detailIntro: String(item.doctor.detailIntro || "").trim(),
      }
    : null;
  const quota = item.quota && typeof item.quota === "object"
    ? {
        doctorId: Number(item.quota.doctorId),
        appointmentDate: String(item.quota.appointmentDate || "").trim(),
        timeSlot: String(item.quota.timeSlot || "").trim(),
        reservedCount: Number(item.quota.reservedCount || 0),
        remainingCount: Number(item.quota.remainingCount || 0),
        capacity: Number(item.quota.capacity || 0),
      }
    : null;

  if (!hospital?.id || !room?.id || !doctor?.id) {
    return null;
  }

  return {
    score: Number(item.score || 0),
    matchReason: String(item.matchReason || "").trim(),
    hospital,
    room,
    doctor,
    quota,
  };
}

function getConsultServiceRecommendations(result, limit = 5) {
  const serviceRecommendations = Array.isArray(result?.doctorRecommendation)
    ? result.doctorRecommendation
      .map((item) => normalizeConsultRecommendationItem(item))
      .filter(Boolean)
    : [];

  return serviceRecommendations.slice(0, limit);
}

function getConsultResultRecommendations(result, limit = 5, includeLocalFallback = false) {
  const serviceRecommendations = getConsultServiceRecommendations(result, limit);
  if (serviceRecommendations.length || !includeLocalFallback) {
    return serviceRecommendations;
  }

  return buildConsultRecommendationCandidates(result, limit);
}

function getConsultPrimaryRecommendationOptions(result) {
  return getConsultResultRecommendations(result, 5);
}

function getConsultPrimaryRecommendation(result) {
  return getConsultPrimaryRecommendationOptions(result)[0] || null;
}

function buildConsultRecommendationCandidates(result, limit = 5) {
  if (!canBuildConsultRecommendationCandidates(result)) {
    return [];
  }

  const department = normalizeText(result?.departmentRecommendation);
  const queryText = getConsultRecommendationQueryText(result);
  const symptomText = normalizeText(queryText);
  const symptomTokens = extractConsultQueryTokens(queryText);
  const locationHints = extractConsultLocationHints(queryText);

  return doctors.value
    .map((doctor) => {
      const room = rooms.value.find((item) => item.id === doctor.roomId);
      const hospital = hospitals.value.find((item) => item.id === doctor.hospitalId);
      if (!hospitalMatchesConsultLocationHints(hospital, locationHints)) {
        return null;
      }
      const searchableText = normalizeText([
        hospital?.name,
        hospital?.level,
        hospital?.location,
        room?.name,
        room?.shortIntro,
        room?.detailIntro,
        doctor.name,
        doctor.title,
        doctor.specialty,
        doctor.shortIntro,
        doctor.detailIntro,
      ].join(" "));

      let score = 0;

      if (room && department && normalizeText(room.name).includes(department.replace("门诊", "").replace("专科", ""))) {
        score += 8;
      }

      if (department && searchableText.includes(department.replace("门诊", "").replace("专科", ""))) {
        score += 5;
      }

      for (const token of symptomTokens) {
        if (searchableText.includes(token)) {
          score += token.length >= 3 ? 3 : 2;
        }
      }

      if (department.includes("全科") && room) {
        const roomText = normalizeText(`${room.name} ${room.shortIntro || ""} ${room.detailIntro || ""}`);
        if (
          (symptomText.includes("发热") || symptomText.includes("发烧") || symptomText.includes("咳嗽"))
          && roomText.includes("呼吸")
        ) {
          score += 6;
        }
        if ((symptomText.includes("腹痛") || symptomText.includes("反酸") || symptomText.includes("腹泻")) && roomText.includes("消化")) {
          score += 6;
        }
        if ((symptomText.includes("胸闷") || symptomText.includes("胸痛") || symptomText.includes("心悸")) && roomText.includes("心内")) {
          score += 6;
        }
      }

      return {
        score,
        hospital,
        room,
        doctor,
      };
    })
    .filter(Boolean)
    .filter((item) => item.score > 0 && item.hospital && item.room)
    .sort((left, right) => right.score - left.score || left.doctor.id - right.doctor.id)
    .slice(0, limit);
}

function hasDoctorRecommendationIntent(symptomText) {
  return /(推荐.*医生|医生.*推荐|帮.*推荐.*医生|推荐.*可预约|可预约.*医生|挂哪个医生|适合.*医生|帮我找.*医生|帮我选.*医生)/.test(symptomText);
}

function getConsultPatientSummary(result, symptom) {
  const summary = String(result?.patientSummary ?? "").trim();
  if (summary) {
    return summary;
  }

  const symptomText = String(symptom ?? "").trim();
  return symptomText ? `你提到的主要情况是：${symptomText}` : "请先描述你的主要症状。";
}

function getConsultRecommendationSummary(result, primaryRecommendation) {
  if (result?.inputCategory !== "medical") {
    return "请先补充主要症状、持续时间和是否加重，我再为你推荐合适的医院、诊室和医生。";
  }

  if (result?.urgency === "emergency") {
    return "当前描述提示存在急症风险，建议优先前往最近的综合医院急诊，不建议先在线筛选门诊医生。";
  }

  if (primaryRecommendation) {
    return `结合当前描述，优先考虑 ${primaryRecommendation.hospital.name} 的 ${primaryRecommendation.room.name}，可先关注 ${primaryRecommendation.doctor.name} 医生。`;
  }

  return `目前建议先按 ${result?.departmentRecommendation || "推荐科室"} 挂号，补充更多细节后我再帮你进一步缩小到具体医院和医生。`;
}

function canShowDoctorRecommendationAction(result) {
  return Boolean(
    result?.showDoctorRecommendationAction &&
    result?.answerMode !== "streaming",
  );
}

async function requestConsultDoctorRecommendations() {
  if (!consultResult.value) {
    return;
  }

  if (!ensureLoggedIn("请先登录后再使用推荐医生功能")) {
    return;
  }

  consultRecommendationRequested.value = true;
  consultRecommendationCollapseNames.value = [];
  consultRecommendations.value = getConsultServiceRecommendations(consultResult.value, 5);

  if (!consultRecommendations.value.length && (!hospitals.value.length || !rooms.value.length || !doctors.value.length)) {
    await loadAppointmentResources();
  }

  if (!consultRecommendations.value.length) {
    consultRecommendations.value = getConsultResultRecommendations(consultResult.value, 5, true);
  }

  if (!consultRecommendations.value.length) {
    ElMessage.info("暂未匹配到更合适的可预约医生，请先按推荐科室挂号。");
  }
}

function getConsultFollowUpQuestions(result) {
  if (!Array.isArray(result?.followUpQuestions)) {
    return [];
  }

  return result.followUpQuestions
    .map((item) => String(item ?? "").trim())
    .filter(Boolean)
    .slice(0, 3);
}

function getConsultUrgencyLabel(urgency) {
  if (urgency === "emergency") {
    return "建议立即急诊";
  }

  if (urgency === "soon") {
    return "建议尽快就诊";
  }

  if (urgency === "normal") {
    return "可预约门诊";
  }

  return "";
}

function getConsultModeNote(result) {
  if (result?.answerMode === "streaming") {
    return "正在结合知识库和大模型流式生成问诊建议。";
  }

  if (result?.answerMode === "langchain" || result?.answerMode === "llm") {
    return "本次结果已结合知识库内容，由 LangChain 编排大模型生成问诊建议。";
  }

  return "当前未配置可用大模型，已使用知识库和规则做本地兜底回答。";
}

function getConsultRecommendationEmptyText(result, symptom) {
  if (result?.answerMode === "streaming" || !consultRecommendationRequested.value) {
    return "";
  }

  if (result?.urgency === "emergency") {
    return "当前更建议尽快线下就医，不建议继续在线筛选预约医生。";
  }

  return "暂未匹配到具体医生，可先按推荐科室进行挂号。";
}

function clearConsultState() {
  consultForm.symptom = "";
}

function clearConsultSessionLocally() {
  consultForm.symptom = "";
  consultResult.value = null;
  consultRecommendations.value = [];
  consultRecommendationCollapseNames.value = [];
  consultMessages.value = [];
  consultRecommendationRequested.value = false;
  activeConsultSymptom.value = "";
  consultConversationId.value = "";
  activeConsultAssistantMessageId.value = "";
}

async function resetConsultConversation() {
  if (isConsulting.value) {
    ElMessage.warning("当前问诊仍在生成中，请稍后再重置会话");
    return;
  }

  const hasConversation = Boolean(consultConversationId.value);
  const hasVisibleState = Boolean(consultResult.value || activeConsultSymptom.value || consultForm.symptom.trim());
  if (!hasConversation && !hasVisibleState) {
    ElMessage.info("当前没有需要重置的问诊会话");
    return;
  }

  try {
    await ElMessageBox.confirm(
      "重置后将清空当前问诊结果，并从 Redis 中物理删除这段会话记录。",
      "重置会话",
      {
        type: "warning",
        confirmButtonText: "确认重置",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  try {
    if (consultConversationId.value) {
      await deleteConsultConversation(consultConversationId.value);
    }
    clearConsultSessionLocally();
    ElMessage.success("问诊会话已重置");
  } catch (error) {
    ElMessage.error(error.message || "重置会话失败");
  }
}

async function useConsultRecommendation(item) {
  if (!ensureLoggedIn("请先登录后再预约")) {
    return;
  }

  const recommendedAppointmentDate = item.quota?.appointmentDate || "";
  const recommendedTimeSlot = item.quota?.timeSlot || item.doctor.workTimeSlot || "上午 08:30-10:30";
  Object.assign(appointmentForm, {
    hospitalId: item.hospital.id,
    roomId: item.room.id,
    doctorId: item.doctor.id,
    patientName: "",
    patientPhone: "",
    appointmentDate: recommendedAppointmentDate,
    timeSlot: recommendedTimeSlot,
    symptom: activeConsultSymptom.value,
  });
  currentView.value = "appointment";
  pushRouteState();
  await loadAppointmentResources();
  appointmentForm.hospitalId = item.hospital.id;
  appointmentForm.roomId = item.room.id;
  appointmentForm.appointmentDate = recommendedAppointmentDate || appointmentForm.appointmentDate;
  appointmentForm.timeSlot = recommendedTimeSlot || appointmentForm.timeSlot;
  appointmentForm.doctorId = item.doctor.id;
  appointmentForm.symptom = activeConsultSymptom.value;
  browsedHospitalId.value = item.hospital.id;
  browsedRoomId.value = item.room.id;
  applyLoggedInUserToAppointment();
  appointmentStep.value = 3;
}

async function saveCurrentRecord() {
  if (editorDialog.type === "hospital") {
    await saveHospital();
    return;
  }

  if (editorDialog.type === "room") {
    await saveRoom();
    return;
  }

  await saveDoctor();
}

async function saveHospital() {
  if (
    !hospitalForm.name.trim() ||
    !hospitalForm.level.trim() ||
    !hospitalForm.location.trim() ||
    !hospitalForm.shortIntro.trim() ||
    !hospitalForm.detailIntro.trim()
  ) {
    ElMessage.warning("请完整填写医院信息");
    return;
  }

  const payload = {
    name: hospitalForm.name.trim(),
    level: hospitalForm.level.trim(),
    location: hospitalForm.location.trim(),
    shortIntro: hospitalForm.shortIntro.trim(),
    detailIntro: hospitalForm.detailIntro.trim(),
  };

  await persistRecord(
    () =>
      editorDialog.mode === "create"
        ? createHospital(payload)
        : updateHospital(hospitalForm.id, payload),
    editorDialog.mode === "create" ? "医院已添加" : "医院信息已更新",
  );
}

async function saveRoom() {
  if (
    !roomForm.hospitalId ||
    !roomForm.name.trim() ||
    !roomForm.floor.trim() ||
    !roomForm.shortIntro.trim() ||
    !roomForm.detailIntro.trim()
  ) {
    ElMessage.warning("请完整填写诊室信息");
    return;
  }

  const payload = {
    hospitalId: Number(roomForm.hospitalId),
    name: roomForm.name.trim(),
    floor: roomForm.floor.trim(),
    shortIntro: roomForm.shortIntro.trim(),
    detailIntro: roomForm.detailIntro.trim(),
  };

  await persistRecord(
    () =>
      editorDialog.mode === "create"
        ? createRoom(payload)
        : updateRoom(roomForm.id, payload),
    editorDialog.mode === "create" ? "诊室已添加" : "诊室信息已更新",
  );
}

async function saveDoctor() {
  if (
    !doctorForm.hospitalId ||
    !doctorForm.roomId ||
    !doctorForm.name.trim() ||
    !doctorForm.title.trim() ||
    !doctorForm.specialty.trim() ||
    !doctorForm.workTimeSlot ||
    !doctorForm.shortIntro.trim() ||
    !doctorForm.detailIntro.trim()
  ) {
    ElMessage.warning("请完整填写医生信息");
    return;
  }

  const room = rooms.value.find((item) => item?.id === Number(doctorForm.roomId));

  if (!room || room.hospitalId !== Number(doctorForm.hospitalId)) {
    ElMessage.warning("医生所属诊室与医院不匹配");
    return;
  }

  const payload = {
    hospitalId: Number(doctorForm.hospitalId),
    roomId: Number(doctorForm.roomId),
    name: doctorForm.name.trim(),
    title: doctorForm.title.trim(),
    specialty: doctorForm.specialty.trim(),
    workTimeSlot: doctorForm.workTimeSlot,
    shortIntro: doctorForm.shortIntro.trim(),
    detailIntro: doctorForm.detailIntro.trim(),
  };

  await persistRecord(
    () =>
      editorDialog.mode === "create"
        ? createDoctor(payload)
        : updateDoctor(doctorForm.id, payload),
    editorDialog.mode === "create" ? "医生已添加" : "医生信息已更新",
  );
}

async function persistRecord(action, successMessage) {
  isSavingRecord.value = true;

  try {
    await action();
    editorDialog.visible = false;
    await loadAdminCatalog();
    ElMessage.success(successMessage);
  } catch (error) {
    ElMessage.error(error.message || "保存失败");
  } finally {
    isSavingRecord.value = false;
  }
}

async function confirmDanger(message, title) {
  try {
    await ElMessageBox.confirm(message, title, {
      type: "warning",
      confirmButtonText: "确认删除",
      cancelButtonText: "取消",
    });
    return true;
  } catch {
    return false;
  }
}

async function removeHospital(item) {
  const roomCount = item.roomCount ?? 0;
  const doctorCount = item.doctorCount ?? 0;

  const confirmed = await confirmDanger(
    `删除后将一并移除 ${roomCount} 个诊室和 ${doctorCount} 位医生，确认继续吗？`,
    `删除医院：${item.name}`,
  );

  if (!confirmed) {
    return;
  }

  await removeRecord(() => deleteHospital(item.id), "医院及关联数据已删除");
}

async function removeRoom(item) {
  const doctorCount = item.doctorCount ?? 0;

  const confirmed = await confirmDanger(
    `删除后将一并移除 ${doctorCount} 位医生，确认继续吗？`,
    `删除诊室：${item.name}`,
  );

  if (!confirmed) {
    return;
  }

  await removeRecord(() => deleteRoom(item.id), "诊室及关联医生已删除");
}

async function removeDoctor(item) {
  const confirmed = await confirmDanger(`确认删除医生“${item.name}”吗？`, "删除医生");

  if (!confirmed) {
    return;
  }

  await removeRecord(() => deleteDoctor(item.id), "医生已删除");
}

async function removeSelectedItems() {
  const ids = [...currentSelection.value];

  if (!ids.length) {
    ElMessage.warning("请先选择要删除的数据");
    return;
  }

  if (activeModule.value === "hospital") {
    const selectedHospitals = visibleHospitals.value.filter((item) => ids.includes(item.id));
    const roomCount = selectedHospitals.reduce((sum, item) => sum + (item.roomCount ?? 0), 0);
    const doctorCount = selectedHospitals.reduce((sum, item) => sum + (item.doctorCount ?? 0), 0);

    const confirmed = await confirmDanger(
      `确认删除 ${selectedHospitals.length} 家医院吗？这会同时删除 ${roomCount} 个诊室和 ${doctorCount} 位医生。`,
      "批量删除医院",
    );

    if (!confirmed) {
      return;
    }

    await removeRecord(
      () => Promise.all(ids.map((id) => deleteHospital(id))),
      "已批量删除医院及关联数据",
    );
    return;
  }

  if (activeModule.value === "room") {
    const selectedRooms = visibleRooms.value.filter((item) => ids.includes(item.id));
    const doctorCount = selectedRooms.reduce((sum, item) => sum + (item.doctorCount ?? 0), 0);

    const confirmed = await confirmDanger(
      `确认删除 ${selectedRooms.length} 个诊室吗？这会同时删除 ${doctorCount} 位医生。`,
      "批量删除诊室",
    );

    if (!confirmed) {
      return;
    }

    await removeRecord(
      () => Promise.all(ids.map((id) => deleteRoom(id))),
      "已批量删除诊室及关联医生",
    );
    return;
  }

  if (activeModule.value === "appointment") {
    const selectedAppointments = visibleAppointments.value.filter((item) => ids.includes(item.id));

    const confirmed = await confirmDanger(
      `确认删除 ${selectedAppointments.length} 条预约记录吗？`,
      "批量删除预约",
    );

    if (!confirmed) {
      return;
    }

    await removeRecord(
      () => Promise.all(ids.map((id) => deleteAppointment(id))),
      "已批量删除预约记录",
    );
    return;
  }

  const confirmed = await confirmDanger(`确认删除 ${ids.length} 位医生吗？`, "批量删除医生");

  if (!confirmed) {
    return;
  }

  await removeRecord(
    () => Promise.all(ids.map((id) => deleteDoctor(id))),
    "已批量删除医生",
  );
}

async function cancelSelectedAppointment(item) {
  const confirmed = await confirmDanger(`确认取消“${item.patientName}”的预约吗？`, "取消预约");

  if (!confirmed) {
    return;
  }

  await removeRecord(() => cancelAppointment(item.id), "预约已取消");
}

async function cancelHomeAppointment(item) {
  const confirmed = await confirmDanger(`确认取消“${item.patientName}”的预约吗？`, "取消预约");

  if (!confirmed) {
    return;
  }

  isLoadingCatalog.value = true;

  try {
    await cancelMyAppointment(item.id);
    await loadHomeAppointments();
    ElMessage.success("预约已取消");
  } catch (error) {
    ElMessage.error(error.message || "取消预约失败");
  } finally {
    isLoadingCatalog.value = false;
  }
}

async function removeAppointment(item) {
  const confirmed = await confirmDanger(`确认删除“${item.patientName}”的预约记录吗？`, "删除预约");

  if (!confirmed) {
    return;
  }

  await removeRecord(() => deleteAppointment(item.id), "预约记录已删除");
}

async function removeRecord(action, successMessage) {
  isLoadingCatalog.value = true;

  try {
    await action();
    await loadAdminCatalog();
    ElMessage.success(successMessage);
  } catch (error) {
    ElMessage.error(error.message || "删除失败");
  } finally {
    isLoadingCatalog.value = false;
  }
}

watch(currentView, (value) => {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(VIEW_STORAGE_KEY, value);
  }
});

watch(activeModule, (value) => {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(MODULE_STORAGE_KEY, value);
  }
});

watch(
  () => [filters.keyword, filters.hospitalId, filters.roomId, filters.workTimeSlot],
  async () => {
    if (currentView.value !== "admin" || activeModule.value === "appointment") {
      return;
    }
    resetAdminPagination();
    await loadAdminCatalog();
  },
);

onMounted(() => {
  if (!isLoggedIn.value && currentView.value !== "home") {
    currentView.value = "home";
  }

  if (currentView.value === "admin" && !isAdminUser.value) {
    currentView.value = "home";
  }

  applyLoggedInUserToAppointment();

  if (typeof window !== "undefined") {
    window.history.replaceState(
      { view: currentView.value, module: activeModule.value },
      "",
      buildRouteUrl(),
    );

    window.addEventListener("popstate", () => {
      applyRouteState(getRouteState());
    });

    window.addEventListener(AUTH_EXPIRED_EVENT, (event) => {
      const message = event?.detail?.message || "登录状态已过期，请重新登录";
      resetToLoginOnSessionExpired(message);
    });
  }

  if (currentView.value === "admin") {
    loadAdminCatalog();
  } else if (currentView.value === "appointment") {
    loadAppointmentResources();
  } else if (currentView.value === "home" && isLoggedIn.value && !isAdminUser.value) {
    loadHomeAppointments();
  }
});
</script>

<template>
  <div class="app-shell">
    <template v-if="currentView === 'home'">
      <section class="home-card">
        <div class="brand-lockup">
          <div class="brand-mark" aria-hidden="true">
            <span class="brand-mark-core"></span>
          </div>
          <div class="brand-copy">
            <p class="eyebrow" aria-label="QUICKCARE">
              <span>Q</span>
              <span>U</span>
              <span>I</span>
              <span>C</span>
              <span>K</span>
              <span>C</span>
              <span>A</span>
              <span>R</span>
              <span>E</span>
            </p>
            <h1>快快医</h1>
          </div>
        </div>
        <p class="hero-copy">
          快快医是一套面向患者与医院管理人员的智能就诊服务平台，支持 AI 问诊、挂号预约与后台管理，
          帮助用户更快找到合适科室、医生和就诊入口。
        </p>

        <div v-if="!isLoggedIn" class="auth-panel">
          <div class="auth-panel-header">
            <template v-if="authMode !== AUTH_MODE_ADMIN">
              <div class="auth-entry-row">
                <button
                  type="button"
                  class="admin-entry-button"
                  @click="switchAuthMode(AUTH_MODE_ADMIN)"
                >
                  管理入口
                </button>
              </div>
              <div class="auth-tabs">
                <button
                  type="button"
                  :class="{ active: authMode === AUTH_MODE_LOGIN }"
                  @click="switchAuthMode(AUTH_MODE_LOGIN)"
                >
                  手机号登录
                </button>
                <button
                  type="button"
                  :class="{ active: authMode === AUTH_MODE_REGISTER }"
                  @click="switchAuthMode(AUTH_MODE_REGISTER)"
                >
                  注册普通用户
                </button>
              </div>
            </template>
            <div v-else class="admin-auth-header">
              <button type="button" class="admin-back-button" @click="switchAuthMode(AUTH_MODE_LOGIN)">
                <span class="admin-back-icon" aria-hidden="true">‹</span>
                <span>返回</span>
              </button>
              <span class="admin-auth-title">管理入口</span>
            </div>
          </div>

          <el-form label-position="top" class="auth-form" @submit.prevent="submitAuth">
            <el-form-item v-if="authMode === AUTH_MODE_REGISTER" label="姓名">
              <el-input v-model="authForm.name" placeholder="请输入姓名" />
            </el-form-item>
            <el-form-item v-if="authMode !== AUTH_MODE_ADMIN" label="手机号">
              <el-input v-model="authForm.phone" maxlength="11" placeholder="请输入手机号" />
            </el-form-item>
            <el-form-item :label="authMode === AUTH_MODE_ADMIN ? '管理员口令' : '密码'">
              <el-input
                v-model="authForm.password"
                type="password"
                show-password
                :placeholder="authMode === AUTH_MODE_ADMIN ? '请输入管理员口令' : '请输入密码'"
                @keyup.enter="submitAuth"
              />
            </el-form-item>
            <el-button
              type="primary"
              native-type="submit"
              class="home-button"
              :class="{ 'admin-submit-button': authMode === AUTH_MODE_ADMIN }"
              :loading="isAuthenticating"
              @click="submitAuth"
            >
              {{ authMode === AUTH_MODE_REGISTER ? "注册并登录" : authMode === AUTH_MODE_ADMIN ? "进入后台" : "登录" }}
            </el-button>
          </el-form>
        </div>

        <div v-else class="user-switch-panel">
          <div>
            <p class="entity-tag">{{ isAdminUser ? "管理员" : "普通用户" }}</p>
            <h3>{{ currentUser.name }}</h3>
            <p>{{ isAdminUser ? "专用管理入口已登录" : currentUser.phone }}</p>
          </div>
          <el-button plain @click="logoutCurrentUser">切换用户</el-button>
        </div>

        <div v-if="isLoggedIn" class="action-list">
          <el-button type="primary" size="large" class="home-button" @click="goToConsult">
            <span class="button-label">AI 问诊</span>
          </el-button>
          <el-button size="large" plain class="home-button" @click="goToAppointment">
            <span class="button-label">挂号预约</span>
          </el-button>
          <el-button size="large" plain class="home-button" @click="goToRag">
            <span class="button-label">RAG 知识库</span>
          </el-button>
          <el-button v-if="isAdminUser" size="large" class="home-button admin-button" @click="goToAdmin">
            <span class="button-label">后台管理</span>
          </el-button>
        </div>

        <section v-if="isLoggedIn && !isAdminUser" class="home-appointments-panel">
          <div class="home-appointments-header">
            <div>
              <p class="entity-tag">我的预约</p>
              <h3>首页快速查看预约记录</h3>
            </div>
            <el-button plain @click="loadHomeAppointments">刷新</el-button>
          </div>

          <div v-if="homeAppointments.length" class="home-appointments-list">
            <article
              v-for="appointment in homeAppointments"
              :key="appointment.id"
              class="home-appointment-card"
            >
              <div class="home-appointment-top">
                <div>
                  <h4>{{ appointment.hospitalName }} / {{ appointment.roomName }}</h4>
                  <p>{{ appointment.doctorName }}{{ appointment.doctorTitle ? ` · ${appointment.doctorTitle}` : "" }}</p>
                </div>
                <span class="home-appointment-status" :class="{ canceled: appointment.status !== '已预约' }">
                  {{ appointment.status }}
                </span>
              </div>
              <p class="home-appointment-time">{{ appointment.appointmentDate }} · {{ appointment.timeSlot }}</p>
              <p v-if="appointment.hospitalLocation" class="home-appointment-meta">
                医院位置：{{ appointment.hospitalLocation }}
              </p>
              <p v-if="appointment.roomFloor" class="home-appointment-meta">
                诊室楼层：{{ appointment.roomFloor }}
              </p>
              <p class="home-appointment-meta">就诊人：{{ appointment.patientName }} · {{ appointment.patientPhone }}</p>
              <p v-if="appointment.symptom" class="home-appointment-meta">症状：{{ appointment.symptom }}</p>
              <div class="home-appointment-actions">
                <el-button
                  v-if="appointment.status === '已预约'"
                  type="danger"
                  plain
                  @click="cancelHomeAppointment(appointment)"
                >
                  取消预约
                </el-button>
              </div>
            </article>
          </div>
          <div v-else class="home-appointments-empty">
            暂无预约记录，选择医院、诊室和医生后即可提交挂号。
          </div>
        </section>
      </section>
    </template>

    <template v-else-if="currentView === 'consult'">
      <section class="appointment-shell consult-shell">
        <header class="appointment-header">
          <div>
            <p class="module-eyebrow">AI 问诊</p>
            <h2>描述症状，获取初步导诊建议</h2>
            <p class="module-copy">系统会根据症状生成推荐科室和就诊提示，结果仅作辅助参考。</p>
          </div>
          <el-button plain @click="goHome">返回首页</el-button>
        </header>

        <div class="appointment-layout consult-layout">
          <section class="appointment-panel consult-panel consult-chat-panel">
            <div ref="consultChatViewport" class="consult-chat-history">
              <article
                v-for="message in consultMessages"
                :key="message.id"
                class="consult-chat-message"
                :data-role="message.role"
                :data-state="message.state"
              >
                <p class="entity-tag">{{ message.role === "user" ? "你" : "AI 导诊" }}</p>
                <p class="consult-chat-text">{{ message.text }}</p>
              </article>
              <div v-if="!consultMessages.length" class="consult-chat-empty">
                这里会保留当前会话里的历史问答，你可以连续补充症状，系统会结合上下文继续分析。
              </div>
            </div>
            <el-form label-position="top" class="editor-form">
              <el-form-item label="症状描述">
                <el-input
                  v-model="consultForm.symptom"
                  type="textarea"
                  :rows="8"
                  maxlength="800"
                  show-word-limit
                  @keydown.enter.exact.prevent="submitConsult"
                />
              </el-form-item>

              <div class="appointment-actions">
                <el-button plain @click="clearConsultState">清空</el-button>
                <el-button plain type="danger" @click="resetConsultConversation">重置会话</el-button>
                <el-button type="primary" :loading="isConsulting" @click="submitConsult">
                  开始问诊
                </el-button>
              </div>
            </el-form>
          </section>

          <aside class="appointment-summary consult-result">
            <p class="entity-tag">问诊结果</p>
            <template v-if="consultResult">
              <div class="consult-result-header">
                <div>
                  <h3>{{ consultResult.departmentRecommendation }}</h3>
                  <p class="consult-mode-note">{{ getConsultModeNote(consultResult) }}</p>
                </div>
                <span
                  v-if="getConsultUrgencyLabel(consultResult.urgency)"
                  class="consult-urgency-badge"
                  :data-urgency="consultResult.urgency"
                >
                  {{ getConsultUrgencyLabel(consultResult.urgency) }}
                </span>
              </div>
              <div class="consult-insight-card">
                <section class="consult-section">
                  <p class="entity-tag">1. 情况总结</p>
                  <p class="consult-insight-lead">
                    {{ getConsultPatientSummary(consultResult, activeConsultSymptom) }}
                  </p>
                </section>

                <section class="consult-section">
                  <p class="entity-tag">2. 初步推荐</p>
                  <p class="consult-insight-lead">
                    {{ getConsultRecommendationSummary(consultResult, getConsultPrimaryRecommendation(consultResult)) }}
                  </p>
                  <div v-if="getConsultPrimaryRecommendation(consultResult)" class="consult-primary-card">
                    <p class="entity-tag">{{ getConsultPrimaryRecommendation(consultResult).hospital.name }}</p>
                    <h4>
                      {{ getConsultPrimaryRecommendation(consultResult).room.name }} / {{ getConsultPrimaryRecommendation(consultResult).doctor.name }}
                    </h4>
                    <p>{{ getConsultPrimaryRecommendation(consultResult).doctor.title }} · {{ getConsultPrimaryRecommendation(consultResult).doctor.specialty }}</p>
                    <p>建议时段：{{ getConsultPrimaryRecommendation(consultResult).doctor.workTimeSlot }}</p>
                  </div>
                  <p class="consult-generated-answer">
                    {{ consultResult.reason }}
                  </p>
                  <p v-if="consultResult.generatedAnswer" class="consult-generated-answer">
                    {{ consultResult.generatedAnswer }}
                  </p>
                </section>

                <section v-if="getConsultFollowUpQuestions(consultResult).length" class="consult-section consult-follow-up">
                  <p class="entity-tag">3. 建议继续补充</p>
                  <ul class="consult-follow-up-list">
                    <li
                      v-for="question in getConsultFollowUpQuestions(consultResult)"
                      :key="question"
                    >
                      {{ question }}
                    </li>
                  </ul>
                </section>
              </div>
              <div
                v-if="canShowDoctorRecommendationAction(consultResult) && !consultRecommendationRequested"
                class="consult-action-panel"
              >
                <p class="detail-line">
                  {{ consultResult.doctorRecommendationPrompt || "如果需要，我可以继续为你推荐可预约医生。" }}
                </p>
                <el-button type="primary" @click="requestConsultDoctorRecommendations">
                  {{ consultResult.doctorRecommendationButtonText || "推荐医生" }}
                </el-button>
              </div>
              <el-collapse
                v-if="consultRecommendations.length"
                v-model="consultRecommendationCollapseNames"
                class="consult-recommendation-collapse"
              >
                <el-collapse-item name="doctor-recommendations">
                  <template #title>
                    <div class="consult-recommendation-collapse-title">
                      <div>
                        <p class="consult-recommendation-collapse-heading">可预约医生</p>
                        <p class="consult-recommendation-collapse-hint">
                          点击展开查看 {{ consultRecommendations.length }} 位医生
                        </p>
                      </div>
                      <span class="consult-recommendation-collapse-count">
                        {{ consultRecommendations.length }} 位
                      </span>
                    </div>
                  </template>
                  <div class="consult-recommendations">
                    <article
                      v-for="item in consultRecommendations"
                      :key="item.doctor.id"
                      class="consult-recommendation-card"
                    >
                      <p class="entity-tag">{{ item.hospital.name }}</p>
                      <h4>{{ item.room.name }} / {{ item.doctor.name }}</h4>
                      <p>{{ item.doctor.title }} · {{ item.doctor.specialty }}</p>
                      <p>上班时间：{{ item.doctor.workTimeSlot }}</p>
                      <p v-if="item.quota?.appointmentDate">
                        可预约：{{ item.quota.appointmentDate }} · {{ item.quota.timeSlot }} · 剩余 {{ item.quota.remainingCount }} 个号
                      </p>
                      <el-button type="primary" plain @click="useConsultRecommendation(item)">
                        选择并预约
                      </el-button>
                    </article>
                  </div>
                </el-collapse-item>
              </el-collapse>
              <div v-else-if="getConsultRecommendationEmptyText(consultResult, activeConsultSymptom)" class="detail-line">
                {{ getConsultRecommendationEmptyText(consultResult, activeConsultSymptom) }}
              </div>
              <p class="consult-disclaimer">{{ consultResult.disclaimer }}</p>
            </template>
            <template v-else>
              <h3>等待输入症状</h3>
              <p>提交后会按“情况总结、初步推荐、继续追问”三部分展示结果。</p>
              <div class="detail-line">若出现剧烈胸痛、呼吸困难、意识异常等紧急情况，请优先急诊。</div>
            </template>
          </aside>
        </div>
      </section>
    </template>

    <template v-else-if="currentView === 'rag'">
      <section class="appointment-shell rag-shell" v-loading="isLoadingRag">
        <header class="appointment-header">
          <div>
            <p class="module-eyebrow">RAG 调试</p>
            <h2>Chroma 知识库查看器</h2>
            <p class="module-copy">查看集合统计、已入库文档和实时 query 结果，方便你调试导诊知识命中情况。</p>
          </div>
          <div class="rag-header-actions">
            <el-button plain @click="refreshRagDocuments">刷新数据</el-button>
            <el-button plain @click="goHome">返回首页</el-button>
          </div>
        </header>

        <div class="rag-overview-grid">
          <article class="rag-stat-card">
            <p class="entity-tag">Collection</p>
            <h3>{{ ragStats?.collection || "ihrs_knowledge" }}</h3>
            <p>{{ ragStats?.count ?? 0 }} 条知识</p>
          </article>
          <article class="rag-stat-card">
            <p class="entity-tag">Persist Dir</p>
            <h3>Chroma DB</h3>
            <p>{{ ragStats?.persistDirectory || "/app/chroma_db" }}</p>
          </article>
          <article class="rag-stat-card">
            <p class="entity-tag">Knowledge Dir</p>
            <h3>Source Files</h3>
            <p>{{ ragStats?.knowledgeDirectory || "/app/knowledge" }}</p>
          </article>
        </div>

        <div class="appointment-layout rag-layout">
          <section class="appointment-panel rag-panel">
            <div class="rag-panel-header">
              <div>
                <p class="entity-tag">已入库文档</p>
                <h3>前 {{ ragDocumentLimit }} 条知识内容</h3>
              </div>
            </div>

            <div v-if="ragDocuments.length" class="rag-document-list">
              <article
                v-for="item in ragDocuments"
                :key="item.id"
                class="rag-document-card"
              >
                <div class="rag-document-top">
                  <div>
                    <p class="entity-tag">{{ item.metadata.type || "knowledge" }}</p>
                    <h4>{{ item.id }}</h4>
                  </div>
                  <span class="detail-side">{{ item.metadata.department || "未分类" }}</span>
                </div>
                <p class="entity-intro">{{ item.text }}</p>
                <pre class="rag-metadata">{{ formatMetadata(item.metadata) }}</pre>
              </article>
            </div>
            <div v-else class="home-appointments-empty">
              当前还没有读到知识文档。
            </div>
          </section>

          <aside class="appointment-summary rag-summary">
            <p class="entity-tag">Query 测试</p>
            <el-form label-position="top" class="editor-form" @submit.prevent="submitRagSearch">
              <el-form-item label="检索问题">
                <el-input
                  v-model="ragSearchForm.query"
                  type="textarea"
                  :rows="4"
                  placeholder="例如：胸闷心悸，活动后气短，应该挂哪个科室？"
                />
              </el-form-item>
              <el-form-item label="Top K">
                <el-input v-model="ragSearchForm.topK" type="number" min="1" max="10" />
              </el-form-item>
              <div class="appointment-actions">
                <el-button type="primary" :loading="isSearchingRag" @click="submitRagSearch">
                  开始检索
                </el-button>
              </div>
            </el-form>

            <div class="rag-search-results">
              <h3>检索结果</h3>
              <div v-if="ragSearchResults.length" class="rag-search-list">
                <article
                  v-for="item in ragSearchResults"
                  :key="item.id"
                  class="rag-search-card"
                >
                  <div class="rag-document-top">
                    <div>
                      <p class="entity-tag">{{ item.metadata?.type || "knowledge" }}</p>
                      <h4>{{ item.id }}</h4>
                    </div>
                    <span class="detail-side">distance: {{ item.distance?.toFixed?.(4) ?? item.distance }}</span>
                  </div>
                  <p>{{ item.text }}</p>
                  <pre class="rag-metadata">{{ formatMetadata(item.metadata) }}</pre>
                </article>
              </div>
              <div v-else class="home-appointments-empty">
                先输入一个 query 试试检索效果。
              </div>
            </div>
          </aside>
        </div>
      </section>
    </template>

    <template v-else-if="currentView === 'appointment'">
      <section class="appointment-shell" v-loading="isLoadingCatalog">
        <header class="appointment-header">
          <div>
            <p class="module-eyebrow">挂号预约</p>
            <h2>按步骤完成预约</h2>
            <p class="module-copy">从医院到诊室，再到医生与预约日期，逐级查看详细介绍后再提交预约。</p>
          </div>
          <el-button plain @click="goHome">返回首页</el-button>
        </header>

        <div class="appointment-layout appointment-flow-layout">
          <section class="appointment-panel appointment-flow-panel">
            <div class="appointment-stepbar">
              <button
                v-for="item in appointmentStepItems"
                :key="item.step"
                type="button"
                class="appointment-step-pill"
                :class="{
                  active: item.step === appointmentStep,
                  available: item.step <= appointmentMaxUnlockedStep,
                }"
                @click="openAppointmentStep(item.step)"
              >
                <span class="appointment-step-number">0{{ item.step }}</span>
                <span class="appointment-step-copy">
                  <strong>{{ item.label }}</strong>
                  <small>{{ item.hint }}</small>
                </span>
              </button>
            </div>

            <div class="appointment-stage-header">
              <div>
                <p class="entity-tag">第 {{ appointmentStep }} 步</p>
                <h3>{{ getAppointmentStepTitle() }}</h3>
                <p>{{ getAppointmentStepDescription() }}</p>
              </div>
              <div class="appointment-stage-nav">
                <el-button v-if="appointmentStep > 1" plain @click="openAppointmentStep(appointmentStep - 1)">
                  上一步
                </el-button>
              </div>
            </div>

            <template v-if="appointmentStep === 1">
              <div v-if="appointmentHospitals.length" class="appointment-stage-list appointment-hospital-list">
                <article
                  v-for="hospital in appointmentHospitals"
                  :key="hospital.id"
                  class="appointment-resource-card"
                  :class="{ active: hospital.id === Number(appointmentForm.hospitalId) }"
                >
                  <div class="appointment-resource-top">
                    <div>
                      <p class="entity-tag">{{ hospital.level || "医院" }}</p>
                      <h4>{{ hospital.name }}</h4>
                    </div>
                    <span class="appointment-count-badge">
                      {{ getHospitalRooms(hospital.id).length }} 个诊室 / {{ getHospitalDoctors(hospital.id).length }} 位医生
                    </span>
                  </div>
                  <p class="appointment-location">地址：{{ hospital.location || "暂未填写具体地址" }}</p>
                  <p class="appointment-copy">{{ hospital.shortIntro || "可先通过地址、医院等级和诊室配置判断是否适合就诊。" }}</p>
                  <p class="appointment-detail">{{ hospital.detailIntro || hospital.shortIntro || "该医院暂未补充更多介绍信息。" }}</p>

                  <div v-if="isHospitalPreviewExpanded(hospital.id)" class="appointment-resource-section">
                    <h5>医院所属诊室预览</h5>
                    <div v-if="getHospitalRooms(hospital.id).length" class="appointment-nested-list">
                      <article
                        v-for="room in getHospitalRooms(hospital.id)"
                        :key="room.id"
                        class="appointment-nested-card"
                      >
                        <div class="appointment-nested-top">
                          <strong>{{ room.name }}</strong>
                          <span>{{ room.floor || "楼层待补充" }}</span>
                        </div>
                        <p>{{ room.shortIntro || "该诊室已开放预约，可继续查看详情后进入下一步筛选。" }}</p>
                      </article>
                    </div>
                    <div v-else class="appointment-empty-state">
                      当前医院还没有可选诊室。
                    </div>
                  </div>

                  <div class="appointment-card-footer">
                    <div class="detail-line">先看详情，确认医院后再继续筛选诊室。</div>
                    <div class="appointment-card-actions">
                      <el-button plain @click="showHospitalDetails(hospital.id)">查看医院详情</el-button>
                      <el-button plain @click="toggleHospitalPreview(hospital.id)">
                        {{ isHospitalPreviewExpanded(hospital.id) ? "收起诊室" : "展开诊室" }}
                      </el-button>
                      <el-button type="primary" @click="selectAppointmentHospital(hospital)">
                        选择这家医院
                      </el-button>
                    </div>
                  </div>
                </article>
              </div>
              <div v-else class="appointment-empty-state">
                当前还没有可预约的医院资源。
              </div>
            </template>

            <template v-else-if="appointmentStep === 2">
              <div v-if="selectedAppointmentHospital" class="appointment-stage-focus">
                <p class="entity-tag">已选医院</p>
                <h4>{{ selectedAppointmentHospital.name }}</h4>
                <p>{{ selectedAppointmentHospital.level || "医院" }} · {{ selectedAppointmentHospital.location || "地址待补充" }}</p>
                <div class="detail-line">{{ selectedAppointmentHospital.shortIntro || "继续选择更合适的诊室。" }}</div>
              </div>

              <div v-if="selectedAppointmentHospitalRooms.length" class="appointment-stage-list appointment-room-list">
                <article
                  v-for="room in selectedAppointmentHospitalRooms"
                  :key="room.id"
                  class="appointment-resource-card"
                  :class="{ active: room.id === Number(appointmentForm.roomId) }"
                >
                  <div class="appointment-resource-top">
                    <div>
                      <p class="entity-tag">{{ room.floor || "诊室" }}</p>
                      <h4>{{ room.name }}</h4>
                    </div>
                    <span class="appointment-count-badge">
                      {{ getRoomDoctors(room.id).length }} 位医生
                    </span>
                  </div>
                  <p class="appointment-copy">{{ room.shortIntro || "可根据诊室方向、楼层位置和医生配置进一步筛选。" }}</p>
                  <p class="appointment-detail">{{ room.detailIntro || room.shortIntro || "该诊室暂未补充更多介绍信息。" }}</p>

                  <div v-if="isRoomDoctorPreviewExpanded(room.id)" class="appointment-resource-section">
                    <h5>诊室所属医生</h5>
                    <div v-if="getRoomDoctors(room.id).length" class="appointment-doctor-preview">
                      <article
                        v-for="doctor in getRoomDoctors(room.id)"
                        :key="doctor.id"
                        class="appointment-inline-doctor"
                      >
                        <strong>{{ doctor.name }}</strong>
                        <span>{{ doctor.title }} · {{ doctor.specialty }}</span>
                        <span>{{ doctor.workTimeSlot }}</span>
                      </article>
                    </div>
                    <div v-else class="appointment-empty-state">
                      当前诊室还没有医生排班。
                    </div>
                  </div>

                  <div class="appointment-card-footer">
                    <div class="appointment-card-actions">
                      <el-button plain @click="showRoomDetails(room.id)">查看诊室详情</el-button>
                      <el-button plain @click="toggleRoomDoctorPreview(room.id)">
                        {{ isRoomDoctorPreviewExpanded(room.id) ? "收起医生列表" : "展开医生列表" }}
                      </el-button>
                      <el-button type="primary" @click="selectAppointmentRoom(room)">
                        选择这个诊室
                      </el-button>
                    </div>
                  </div>
                </article>
              </div>
              <div v-else class="appointment-empty-state">
                当前医院暂无可选诊室，请返回上一步重新选择医院。
              </div>
            </template>

            <template v-else-if="appointmentStep === 3">
              <div v-if="selectedAppointmentHospital && selectedAppointmentRoom" class="appointment-stage-focus">
                <p class="entity-tag">当前路径</p>
                <h4>{{ selectedAppointmentHospital.name }} / {{ selectedAppointmentRoom.name }}</h4>
                <p>{{ selectedAppointmentRoom.floor || "楼层待补充" }}</p>
                <div class="detail-line">{{ selectedAppointmentRoom.shortIntro || "先选日期，再继续挑选医生。" }}</div>
              </div>

              <div class="appointment-date-toolbar">
                <div>
                  <p class="entity-tag">预约日期</p>
                  <p>仅展示今天起未来 {{ APPOINTMENT_DATE_FUTURE_DAYS }} 天的预约情况，直接点击下方日期卡片完成选择。</p>
                </div>
              </div>

              <div v-if="appointmentDateSummaries.length" class="appointment-date-grid">
                <button
                  v-for="summary in appointmentDateSummaries"
                  :key="summary.date"
                  type="button"
                  class="appointment-date-card"
                  :class="[
                    `appointment-date-card--${summary.status}`,
                    { active: summary.date === appointmentForm.appointmentDate, disabled: summary.status === 'full' },
                  ]"
                  :disabled="summary.status === 'full'"
                  @click="toggleAppointmentDate(summary.date)"
                >
                  <strong>{{ formatAppointmentCardDate(summary.date) }}</strong>
                  <span>{{ formatAppointmentCardWeekday(summary.date) }}</span>
                  <em>{{ summary.label }}</em>
                  <small>{{ getDateSummaryLine(summary.date) }}</small>
                </button>
              </div>

              <div v-if="isLoadingAppointmentCalendar" class="appointment-inline-note">
                正在加载今天起未来 {{ APPOINTMENT_DATE_FUTURE_DAYS }} 天号源，下方日期卡片会直接显示可约医生数和剩余号。
              </div>
              <div v-else-if="!appointmentDateSummaries.length" class="appointment-inline-note">
                当前诊室暂无可展示的日期号源信息。
              </div>
              <div v-if="!appointmentForm.appointmentDate" class="appointment-inline-note">
                还没有选择预约日期，系统暂时无法判断对应号源余量。
              </div>

              <div v-if="!appointmentForm.appointmentDate" class="appointment-empty-state">
                请先选择预约日期，选定后再查看医生介绍和可预约时段。
              </div>
              <div v-else-if="selectedAppointmentRoomDoctors.length" class="appointment-stage-list appointment-doctor-list">
                <article
                  v-for="doctor in selectedAppointmentRoomDoctors"
                  :key="doctor.id"
                  class="appointment-resource-card appointment-resource-card--doctor"
                  :class="{ active: doctor.id === Number(appointmentForm.doctorId) }"
                >
                  <div class="appointment-resource-top">
                    <div>
                      <p class="entity-tag">{{ doctor.title }}</p>
                      <h4>{{ doctor.name }}</h4>
                    </div>
                    <span class="appointment-count-badge">{{ doctor.workTimeSlot }}</span>
                  </div>
                  <div class="appointment-doctor-meta">
                    <span>擅长方向：{{ doctor.specialty }}</span>
                    <span>所属诊室：{{ doctor.roomName }}</span>
                    <span v-if="appointmentForm.appointmentDate && getDoctorQuotaForSelectedDate(doctor.id)">
                      余号：{{ getDoctorQuotaForSelectedDate(doctor.id).remainingCount }}/{{ getDoctorQuotaForSelectedDate(doctor.id).capacity }}
                    </span>
                  </div>
                  <p class="appointment-copy">{{ doctor.shortIntro || "可结合职称、擅长方向和接诊时段决定是否预约。" }}</p>
                  <p class="appointment-detail">{{ doctor.detailIntro || doctor.shortIntro || "该医生暂未补充更多个人介绍。" }}</p>
                  <div v-if="appointmentForm.appointmentDate" class="appointment-inline-note appointment-inline-note--compact">
                    <template v-if="getDoctorQuotaForSelectedDate(doctor.id)">
                      {{ appointmentForm.appointmentDate }} · {{ doctor.workTimeSlot }} ·
                      <span v-if="getDoctorQuotaForSelectedDate(doctor.id).remainingCount > 0">
                        还剩 {{ getDoctorQuotaForSelectedDate(doctor.id).remainingCount }} 个号
                      </span>
                      <span v-else>当前日期已满号</span>
                    </template>
                    <template v-else>
                      正在获取该医生在所选日期的剩余号源。
                    </template>
                  </div>

                  <div class="appointment-card-footer">
                    <div class="detail-line">选择后会进入最后一步，填写就诊人信息并提交预约。</div>
                    <el-button
                      type="primary"
                      plain
                      :disabled="getDoctorQuotaForSelectedDate(doctor.id)?.remainingCount === 0"
                      @click="selectAppointmentDoctor(doctor)"
                    >
                      {{
                        getDoctorQuotaForSelectedDate(doctor.id)?.remainingCount === 0
                          ? "当日已满"
                          : "选择这位医生"
                      }}
                    </el-button>
                  </div>
                </article>
              </div>
              <div v-else class="appointment-empty-state">
                当前诊室暂无可预约医生，请返回上一步重新选择诊室。
              </div>
            </template>

            <template v-else>
              <div v-if="selectedAppointmentDoctor" class="appointment-stage-focus">
                <p class="entity-tag">最终确认</p>
                <h4>{{ selectedAppointmentHospital?.name }} / {{ selectedAppointmentRoom?.name }} / {{ selectedAppointmentDoctor.name }}</h4>
                <p>{{ appointmentForm.appointmentDate || "未选日期" }} · {{ appointmentForm.timeSlot }}</p>
                <div class="detail-line">{{ selectedAppointmentDoctor.specialty }}</div>
              </div>

              <div class="appointment-review-grid">
                <article class="appointment-review-card">
                  <p class="entity-tag">医院</p>
                  <h4>{{ selectedAppointmentHospital?.name || "未选择医院" }}</h4>
                  <p>{{ selectedAppointmentHospital?.location || "请返回前一步选择医院" }}</p>
                </article>
                <article class="appointment-review-card">
                  <p class="entity-tag">诊室</p>
                  <h4>{{ selectedAppointmentRoom?.name || "未选择诊室" }}</h4>
                  <p>{{ selectedAppointmentRoom?.shortIntro || "请返回前一步选择诊室" }}</p>
                </article>
                <article class="appointment-review-card">
                  <p class="entity-tag">医生与时段</p>
                  <h4>{{ selectedAppointmentDoctor?.name || "未选择医生" }}</h4>
                  <p>{{ appointmentForm.appointmentDate || "未选日期" }} · {{ appointmentForm.timeSlot || "未选时段" }}</p>
                </article>
              </div>

              <el-form label-position="top" class="editor-form appointment-final-form">
                <div class="form-grid two-columns">
                  <el-form-item label="就诊人姓名">
                    <el-input v-model="appointmentForm.patientName" placeholder="请输入姓名" />
                  </el-form-item>
                  <el-form-item label="联系电话">
                    <el-input
                      v-model="appointmentForm.patientPhone"
                      :disabled="!isAdminUser"
                      :placeholder="isAdminUser ? '请输入联系电话' : '登录手机号'"
                    />
                  </el-form-item>
                </div>

                <el-form-item label="症状说明">
                  <el-input
                    v-model="appointmentForm.symptom"
                    type="textarea"
                    :rows="4"
                    maxlength="500"
                    show-word-limit
                    placeholder="可简单描述症状、病程或本次就诊诉求"
                  />
                </el-form-item>

                <div class="appointment-actions">
                  <el-button plain @click="openAppointmentStep(3)">修改医生与日期</el-button>
                  <el-button plain @click="loadAppointmentResources">刷新资源</el-button>
                  <el-button
                    type="primary"
                    :loading="isSubmittingAppointment"
                    :disabled="isAppointmentSlotFull || isCurrentSlotBooked"
                    @click="submitAppointment"
                  >
                    {{ isCurrentSlotBooked ? "已预约" : "提交预约" }}
                  </el-button>
                </div>
              </el-form>
            </template>
          </section>

          <aside class="appointment-summary appointment-flow-summary">
            <div v-if="appointmentFocusedHospital" class="appointment-summary-section">
              <p class="entity-tag">医院详情</p>
              <h3>{{ appointmentFocusedHospital.name }}</h3>
              <p>{{ appointmentFocusedHospital.level || "医院" }}</p>
              <p>{{ appointmentFocusedHospital.location || "地址待补充" }}</p>
              <div class="detail-line">{{ appointmentFocusedHospital.shortIntro || "请结合医院位置和资源配置决定是否继续预约。" }}</div>
              <div class="detail-line">
                下设 {{ appointmentFocusedHospitalRooms.length }} 个诊室，当前排班 {{ appointmentFocusedHospitalDoctors.length }} 位医生。
              </div>
            </div>

            <div v-if="appointmentFocusedRoom" class="appointment-summary-section">
              <p class="entity-tag">诊室详情</p>
              <h3>{{ appointmentFocusedRoom.name }}</h3>
              <p>{{ appointmentFocusedRoom.floor || "楼层待补充" }}</p>
              <div class="detail-line">{{ appointmentFocusedRoom.shortIntro || "当前诊室暂无简介。" }}</div>
              <div class="detail-line">该诊室共有 {{ appointmentFocusedRoomDoctors.length }} 位可选医生。</div>
            </div>

            <div v-if="selectedAppointmentDoctor" class="appointment-summary-section">
              <p class="entity-tag">医生详情</p>
              <h3>{{ selectedAppointmentDoctor.name }}</h3>
              <p>{{ selectedAppointmentDoctor.title }} · {{ selectedAppointmentDoctor.specialty }}</p>
              <div class="detail-line">{{ selectedAppointmentDoctor.shortIntro || "该医生暂未补充更多介绍。" }}</div>
              <div class="detail-line">接诊时段：{{ selectedAppointmentDoctor.workTimeSlot }}</div>
            </div>

            <div v-if="appointmentQuota" class="appointment-summary-section">
              <p class="entity-tag">号源状态</p>
              <div class="detail-line">单时段容量：{{ appointmentQuota.capacity }} 人</div>
              <div class="detail-line">已约 {{ appointmentQuota.reservedCount }} 人，剩余 {{ appointmentQuota.remainingCount }} 个名额</div>
            </div>

            <div v-if="isCurrentSlotBooked" class="appointment-summary-section">
              <p class="entity-tag">预约提醒</p>
              <div class="detail-line booked-line">你已预约该医生当前时间段，不能重复预约。</div>
            </div>
          </aside>
        </div>
      </section>
    </template>

    <template v-else>
      <section class="admin-shell">
        <aside class="admin-sidebar">
          <div class="sidebar-top">
            <div class="sidebar-brand">
              <div class="sidebar-brand-mark" aria-hidden="true">
                <span class="sidebar-brand-core"></span>
              </div>
              <div>
                <p class="sidebar-eyebrow">运营后台</p>
                <h2>机构资源管理</h2>
              </div>
            </div>
            <p class="sidebar-copy">
              统一维护医院、诊室与医生资料。列表展示简短介绍，点进详情后可查看完整说明。
            </p>
          </div>

          <div class="sidebar-nav">
            <button
              type="button"
              class="nav-item"
              :class="{ active: activeModule === 'hospital' }"
              @click="switchModule('hospital')"
            >
              医院管理
            </button>
            <button
              type="button"
              class="nav-item"
              :class="{ active: activeModule === 'room' }"
              @click="switchModule('room')"
            >
              诊室管理
            </button>
            <button
              type="button"
              class="nav-item"
              :class="{ active: activeModule === 'doctor' }"
              @click="switchModule('doctor')"
            >
              医生管理
            </button>
            <button
              type="button"
              class="nav-item"
              :class="{ active: activeModule === 'appointment' }"
              @click="switchModule('appointment')"
            >
              预约管理
            </button>
          </div>

          <el-button plain class="back-home-button" @click="goHome">返回首页</el-button>
        </aside>

        <main class="admin-main" v-loading="isLoadingCatalog">
          <header class="module-header">
            <div>
              <p class="module-eyebrow">后台管理</p>
              <h3>{{ currentTitle }}</h3>
              <p class="module-copy">{{ currentSubtitle }}</p>
            </div>

            <div class="module-actions">
              <el-button plain :disabled="isLoadingCatalog" @click="loadAdminCatalog">
                刷新
              </el-button>
              <el-button plain :disabled="isLoadingCatalog || !currentVisibleItems.length" @click="toggleSelectAllCurrentModule">
                {{ isAllSelected ? "取消全选" : "全选" }}
              </el-button>
              <el-button plain :disabled="isLoadingCatalog || !currentSelection.length" @click="clearCurrentSelection">
                清空选择
              </el-button>
              <el-button
                plain
                class="bulk-delete-button"
                :disabled="isLoadingCatalog || !currentSelection.length"
                @click="removeSelectedItems"
              >
                批量删除（{{ currentSelection.length }}）
              </el-button>
              <el-button
                v-if="activeModule !== 'appointment'"
                type="primary"
                size="large"
                :disabled="isLoadingCatalog"
                @click="openCreateDialog(activeModule)"
              >
                {{
                  activeModule === "hospital"
                    ? "新增医院"
                    : activeModule === "room"
                      ? "新增诊室"
                      : "新增医生"
                }}
              </el-button>
            </div>
          </header>

          <section v-if="activeModule !== 'appointment'" class="filter-panel">
            <el-input
              v-model="filters.keyword"
              clearable
              class="filter-keyword"
              :placeholder="
                activeModule === 'hospital'
                  ? '搜索医院名称、等级、位置'
                  : activeModule === 'room'
                    ? '搜索诊室名称、楼层、医院'
                    : '搜索医生姓名、职称、专长'
              "
            />

            <el-select
              v-if="activeModule === 'room' || activeModule === 'doctor'"
              v-model="filters.hospitalId"
              clearable
              placeholder="按医院筛选"
              @change="syncFilterRooms"
            >
              <el-option
                v-for="option in hospitalOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>

            <el-select
              v-if="activeModule === 'doctor'"
              v-model="filters.roomId"
              clearable
              placeholder="按诊室筛选"
            >
              <el-option
                v-for="option in filterRoomOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>

            <el-select
              v-if="activeModule === 'doctor'"
              v-model="filters.workTimeSlot"
              clearable
              placeholder="按工作时段筛选"
            >
              <el-option
                v-for="option in workTimeOptions"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>

            <el-button plain @click="resetFilters">重置筛选</el-button>
          </section>

          <el-empty
            v-if="!isLoadingCatalog && !currentVisibleItems.length"
            description="暂无数据"
          />

          <section v-if="activeModule === 'hospital' && currentVisibleItems.length" class="list-grid">
            <article
              v-for="hospital in visibleHospitals"
              :key="hospital.id"
              class="entity-card"
              :class="{ 'entity-card--selected': isSelected('hospital', hospital.id) }"
            >
              <label class="card-selector">
                <input
                  :checked="isSelected('hospital', hospital.id)"
                  type="checkbox"
                  @change="toggleSelection('hospital', hospital.id)"
                />
                <span>选择</span>
              </label>
              <div class="entity-card-top">
                <div>
                  <p class="entity-tag">{{ hospital.level }}</p>
                  <h4>{{ hospital.name }}</h4>
                </div>
                <span class="entity-meta">{{ hospital.location }}</span>
              </div>
              <p class="entity-intro">{{ hospital.shortIntro }}</p>
              <div class="entity-footer">
                <span>{{ rooms.filter((room) => room?.hospitalId === hospital.id).length }} 个诊室</span>
                <div class="entity-actions">
                  <el-button text @click="showDetail('hospital', hospital)">查看详情</el-button>
                  <el-button text @click="openEditDialog('hospital', hospital)">编辑</el-button>
                  <el-button text class="danger-text" @click="removeHospital(hospital)">删除</el-button>
                </div>
              </div>
            </article>
          </section>

          <section v-if="activeModule === 'room' && currentVisibleItems.length" class="list-grid">
            <article
              v-for="room in visibleRooms"
              :key="room.id"
              class="entity-card"
              :class="{ 'entity-card--selected': isSelected('room', room.id) }"
            >
              <label class="card-selector">
                <input
                  :checked="isSelected('room', room.id)"
                  type="checkbox"
                  @change="toggleSelection('room', room.id)"
                />
                <span>选择</span>
              </label>
              <div class="entity-card-top">
                <div>
                  <p class="entity-tag">{{ getHospitalName(room.hospitalId) }}</p>
                  <h4>{{ room.name }}</h4>
                </div>
                <span class="entity-meta">{{ room.floor }}</span>
              </div>
              <p class="entity-intro">{{ room.shortIntro }}</p>
              <div class="entity-footer">
                <span>{{ doctors.filter((doctor) => doctor?.roomId === room.id).length }} 位医生</span>
                <div class="entity-actions">
                  <el-button text @click="showDetail('room', room)">查看详情</el-button>
                  <el-button text @click="openEditDialog('room', room)">编辑</el-button>
                  <el-button text class="danger-text" @click="removeRoom(room)">删除</el-button>
                </div>
              </div>
            </article>
          </section>

          <section v-if="activeModule === 'doctor' && currentVisibleItems.length" class="list-grid doctor-grid">
            <article
              v-for="doctor in visibleDoctors"
              :key="doctor.id"
              class="entity-card"
              :class="{ 'entity-card--selected': isSelected('doctor', doctor.id) }"
            >
              <label class="card-selector">
                <input
                  :checked="isSelected('doctor', doctor.id)"
                  type="checkbox"
                  @change="toggleSelection('doctor', doctor.id)"
                />
                <span>选择</span>
              </label>
              <div class="entity-card-top">
                <div>
                  <p class="entity-tag">{{ doctor.title }}</p>
                  <h4>{{ doctor.name }}</h4>
                </div>
                <span class="entity-meta">{{ doctor.specialty }}</span>
              </div>
              <p class="entity-intro">{{ doctor.shortIntro }}</p>
              <div class="entity-context">
                {{ getHospitalName(doctor.hospitalId) }} / {{ getRoomName(doctor.roomId) }}
              </div>
              <div class="entity-context">上班时间：{{ doctor.workTimeSlot || "未排班" }}</div>
              <div class="entity-footer doctor-card-footer">
                <div class="entity-actions">
                  <el-button text @click="showDetail('doctor', doctor)">查看详情</el-button>
                  <el-button text @click="openEditDialog('doctor', doctor)">编辑</el-button>
                  <el-button text class="danger-text" @click="removeDoctor(doctor)">删除</el-button>
                </div>
              </div>
            </article>
          </section>

          <section
            v-if="activeModule !== 'appointment' && currentVisibleItems.length && currentAdminPagination"
            class="pagination-panel"
          >
            <el-pagination
              :current-page="currentAdminPagination.page"
              :page-size="currentAdminPagination.size"
              :page-sizes="[12, 24, 48]"
              :total="currentAdminPagination.total"
              background
              layout="total, sizes, prev, pager, next"
              @current-change="handleAdminPageChange"
              @size-change="handleAdminPageSizeChange"
            />
          </section>

          <section v-if="activeModule === 'appointment' && currentVisibleItems.length" class="list-grid appointment-grid">
            <article
              v-for="appointment in visibleAppointments"
              :key="appointment.id"
              class="entity-card"
              :class="{ 'entity-card--selected': isSelected('appointment', appointment.id) }"
            >
              <label class="card-selector">
                <input
                  :checked="isSelected('appointment', appointment.id)"
                  type="checkbox"
                  @change="toggleSelection('appointment', appointment.id)"
                />
                <span>选择</span>
              </label>
              <div class="entity-card-top">
                <div>
                  <p class="entity-tag">{{ appointment.status }}</p>
                  <h4>{{ appointment.patientName }}</h4>
                </div>
                <span class="entity-meta">{{ appointment.patientPhone }}</span>
              </div>
              <p class="entity-intro">
                {{ appointment.appointmentDate }} {{ appointment.timeSlot }}
              </p>
              <div class="entity-context">
                {{ appointment.hospitalName }} / {{ appointment.roomName }} / {{ appointment.doctorName }}
              </div>
              <p class="entity-intro">{{ appointment.symptom || "未填写症状说明" }}</p>
              <div class="entity-footer">
                <span>{{ appointment.doctorTitle }}</span>
                <div class="entity-actions">
                  <el-button
                    text
                    :disabled="appointment.status === '已取消'"
                    @click="cancelSelectedAppointment(appointment)"
                  >
                    取消预约
                  </el-button>
                  <el-button text class="danger-text" @click="removeAppointment(appointment)">删除</el-button>
                </div>
              </div>
            </article>
          </section>
        </main>
      </section>
    </template>

    <el-dialog
      v-model="detailDialog.visible"
      width="min(680px, calc(100vw - 24px))"
      :title="
        detailDialog.type === 'hospital'
          ? '医院详情'
          : detailDialog.type === 'room'
            ? '诊室详情'
            : '医生详情'
      "
    >
      <template v-if="detailDialog.item">
        <div class="detail-panel">
          <div class="detail-top">
            <div>
              <p class="detail-label">
                {{
                  detailDialog.type === "hospital"
                    ? detailDialog.item.level
                    : detailDialog.type === "room"
                      ? getHospitalName(detailDialog.item.hospitalId)
                      : detailDialog.item.title
                }}
              </p>
              <h4>{{ detailDialog.item.name }}</h4>
            </div>
            <span class="detail-side">
              {{
                detailDialog.type === "hospital"
                  ? detailDialog.item.location
                  : detailDialog.type === "room"
                    ? detailDialog.item.floor
                    : detailDialog.item.specialty
              }}
            </span>
          </div>

          <div v-if="detailDialog.type === 'doctor'" class="detail-line">
            所属机构：{{ getHospitalName(detailDialog.item.hospitalId) }} / {{ getRoomName(detailDialog.item.roomId) }}
          </div>
          <div v-if="detailDialog.type === 'doctor'" class="detail-line">
            工作时间：{{ detailDialog.item.workTimeSlot || "未排班" }}
          </div>
          <div v-if="detailDialog.type === 'room'" class="detail-line">
            所属医院：{{ getHospitalName(detailDialog.item.hospitalId) }}
          </div>

          <div v-if="detailDialog.type !== 'doctor'" class="detail-block">
            <p class="detail-block-label">简短介绍</p>
            <p>{{ detailDialog.item.shortIntro }}</p>
          </div>
          <div class="detail-block">
            <p class="detail-block-label">详情介绍</p>
            <p>{{ detailDialog.item.detailIntro }}</p>
          </div>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="editorDialog.visible"
      width="min(760px, calc(100vw - 24px))"
      :title="editorDialog.mode === 'create' ? `新增${currentTitle.slice(0, 2)}` : `编辑${currentTitle.slice(0, 2)}`"
    >
      <el-form
        v-if="editorDialog.type === 'hospital'"
        label-position="top"
        class="editor-form"
      >
        <el-form-item label="医院名称">
          <el-input v-model="hospitalForm.name" placeholder="请输入医院名称" />
        </el-form-item>
        <div class="form-grid two-columns">
          <el-form-item label="医院等级">
            <el-input v-model="hospitalForm.level" placeholder="如：三级甲等" />
          </el-form-item>
          <el-form-item label="位置">
            <el-input v-model="hospitalForm.location" placeholder="如：门诊楼 A 区" />
          </el-form-item>
        </div>
        <el-form-item label="简短介绍">
          <el-input
            v-model="hospitalForm.shortIntro"
            maxlength="48"
            show-word-limit
            placeholder="列表中展示的简短介绍"
          />
        </el-form-item>
        <el-form-item label="详情介绍">
          <el-input
            v-model="hospitalForm.detailIntro"
            type="textarea"
            :rows="5"
            placeholder="点击详情后展示的完整介绍"
          />
        </el-form-item>
      </el-form>

      <el-form v-else-if="editorDialog.type === 'room'" label-position="top" class="editor-form">
        <div class="form-grid two-columns">
          <el-form-item label="所属医院">
            <el-select v-model="roomForm.hospitalId" placeholder="请选择所属医院">
              <el-option
                v-for="option in hospitalOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="楼层/房间">
            <el-input v-model="roomForm.floor" placeholder="如：3F-06" />
          </el-form-item>
        </div>
        <el-form-item label="诊室名称">
          <el-input v-model="roomForm.name" placeholder="请输入诊室名称" />
        </el-form-item>
        <el-form-item label="简短介绍">
          <el-input
            v-model="roomForm.shortIntro"
            maxlength="48"
            show-word-limit
            placeholder="列表中展示的简短介绍"
          />
        </el-form-item>
        <el-form-item label="详情介绍">
          <el-input
            v-model="roomForm.detailIntro"
            type="textarea"
            :rows="5"
            placeholder="点击详情后展示的完整介绍"
          />
        </el-form-item>
      </el-form>

      <el-form v-else label-position="top" class="editor-form">
        <div class="form-grid three-columns">
          <el-form-item label="所属医院">
            <el-select
              v-model="doctorForm.hospitalId"
              placeholder="请选择所属医院"
              @change="syncDoctorRoomOptions"
            >
              <el-option
                v-for="option in hospitalOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="所属诊室">
            <el-select v-model="doctorForm.roomId" placeholder="请选择所属诊室">
              <el-option
                v-for="option in roomOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="职称">
            <el-input v-model="doctorForm.title" placeholder="如：主任医师" />
          </el-form-item>
        </div>
        <div class="form-grid two-columns">
          <el-form-item label="医生姓名">
            <el-input v-model="doctorForm.name" placeholder="请输入医生姓名" />
          </el-form-item>
          <el-form-item label="擅长方向">
            <el-input v-model="doctorForm.specialty" placeholder="如：冠心病、心律失常" />
          </el-form-item>
        </div>
        <el-form-item label="工作时间段">
          <el-select v-model="doctorForm.workTimeSlot" placeholder="请选择工作时间段">
            <el-option
              v-for="option in workTimeOptions"
              :key="option"
              :label="option"
              :value="option"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="简短介绍">
          <el-input
            v-model="doctorForm.shortIntro"
            maxlength="48"
            show-word-limit
            placeholder="列表中展示的简短介绍"
          />
        </el-form-item>
        <el-form-item label="详情介绍">
          <el-input
            v-model="doctorForm.detailIntro"
            type="textarea"
            :rows="5"
            placeholder="点击详情后展示的完整介绍"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editorDialog.visible = false">取消</el-button>
          <el-button type="primary" :loading="isSavingRecord" @click="saveCurrentRecord">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>
