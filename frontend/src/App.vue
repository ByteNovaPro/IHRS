<script setup>
import { computed, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

const VIEW_STORAGE_KEY = "ihrs-current-view";
const MODULE_STORAGE_KEY = "ihrs-active-module";

const savedView =
  typeof window !== "undefined" ? window.localStorage.getItem(VIEW_STORAGE_KEY) : null;
const savedModule =
  typeof window !== "undefined" ? window.localStorage.getItem(MODULE_STORAGE_KEY) : null;

const currentView = ref(savedView === "admin" ? "admin" : "home");
const activeModule = ref(["hospital", "room", "doctor"].includes(savedModule) ? savedModule : "hospital");

const hospitals = ref([
  {
    id: 1,
    name: "江城第一人民医院",
    level: "三级甲等",
    location: "门诊楼 A 区",
    shortIntro: "综合诊疗能力强，急诊与慢病管理协同高效。",
    detailIntro:
      "江城第一人民医院是区域综合医疗中心，覆盖急诊、住院、康复与多学科联合门诊，具备完善的智慧导诊与分时挂号能力。",
  },
  {
    id: 2,
    name: "锦和妇幼保健院",
    level: "三级专科",
    location: "健康路 88 号",
    shortIntro: "聚焦妇儿健康，孕产与新生儿服务体系成熟。",
    detailIntro:
      "锦和妇幼保健院长期服务孕产妇、儿童及家庭健康管理场景，设有高危妊娠门诊、儿童保健门诊和快速检验通道。",
  },
]);

const rooms = ref([
  {
    id: 1,
    hospitalId: 1,
    name: "心内诊室",
    floor: "3F-06",
    shortIntro: "负责胸闷、心悸、高血压等常见心血管问题初诊。",
    detailIntro:
      "心内诊室提供心电图评估、血压管理、慢病复诊及转入住院绿色通道，适合常见心血管症状的初步筛查和连续随访。",
  },
  {
    id: 2,
    hospitalId: 1,
    name: "呼吸诊室",
    floor: "2F-11",
    shortIntro: "重点处理咳嗽、哮喘、感染后呼吸不适等问题。",
    detailIntro:
      "呼吸诊室可开展肺功能预约、感染后康复指导和影像检查转诊，适用于发热后久咳、气短和慢性呼吸道疾病管理。",
  },
  {
    id: 3,
    hospitalId: 2,
    name: "儿童保健诊室",
    floor: "5F-02",
    shortIntro: "覆盖儿童发育评估、营养指导与常规随访。",
    detailIntro:
      "儿童保健诊室提供身高体重评估、喂养指导、发育筛查和早期干预建议，适合婴幼儿及学龄前儿童阶段性健康管理。",
  },
]);

const doctors = ref([
  {
    id: 1,
    hospitalId: 1,
    roomId: 1,
    name: "陈思远",
    title: "主任医师",
    specialty: "冠心病、心律失常",
    shortIntro: "擅长复杂心血管疾病诊断与长期随访方案制定。",
    detailIntro:
      "陈思远主任长期从事冠心病与心律失常诊疗，熟悉门诊分诊、住院评估与术后康复建议，适合中老年慢病患者复诊与初筛。",
  },
  {
    id: 2,
    hospitalId: 1,
    roomId: 2,
    name: "林知夏",
    title: "副主任医师",
    specialty: "慢阻肺、哮喘",
    shortIntro: "专注慢性气道疾病与感染后呼吸恢复管理。",
    detailIntro:
      "林知夏医生长期接诊哮喘、慢阻肺与呼吸道感染恢复期患者，能够结合影像、肺功能和病程史制定分层治疗建议。",
  },
  {
    id: 3,
    hospitalId: 2,
    roomId: 3,
    name: "周安宁",
    title: "主治医师",
    specialty: "儿童生长发育",
    shortIntro: "关注儿童营养、发育节律与家庭健康干预。",
    detailIntro:
      "周安宁医生主要负责儿童生长发育评估、营养管理及家庭随访，擅长将就诊建议转化为家长容易执行的日常方案。",
  },
]);

const hospitalIdSeed = ref(hospitals.value.length + 1);
const roomIdSeed = ref(rooms.value.length + 1);
const doctorIdSeed = ref(doctors.value.length + 1);

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
  shortIntro: "",
  detailIntro: "",
});

const currentTitle = computed(() => moduleMeta[activeModule.value].title);
const currentSubtitle = computed(() => moduleMeta[activeModule.value].subtitle);
const visibleHospitals = computed(() => hospitals.value.filter(Boolean));
const visibleRooms = computed(() => rooms.value.filter(Boolean));
const visibleDoctors = computed(() => doctors.value.filter(Boolean));
const selectedHospitalIds = ref([]);
const selectedRoomIds = ref([]);
const selectedDoctorIds = ref([]);

const currentSelection = computed(() => {
  if (activeModule.value === "hospital") {
    return selectedHospitalIds.value;
  }

  if (activeModule.value === "room") {
    return selectedRoomIds.value;
  }

  return selectedDoctorIds.value;
});

const currentVisibleItems = computed(() => {
  if (activeModule.value === "hospital") {
    return visibleHospitals.value;
  }

  if (activeModule.value === "room") {
    return visibleRooms.value;
  }

  return visibleDoctors.value;
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

function getHospitalName(hospitalId) {
  return hospitals.value.find((hospital) => hospital?.id === hospitalId)?.name ?? "未关联医院";
}

function getRoomName(roomId) {
  return rooms.value.find((room) => room?.id === roomId)?.name ?? "未关联诊室";
}

function goToAdmin() {
  currentView.value = "admin";
}

function goHome() {
  currentView.value = "home";
}

function switchModule(moduleKey) {
  activeModule.value = moduleKey;
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

function getSelectionRef(type) {
  if (type === "hospital") {
    return selectedHospitalIds;
  }

  if (type === "room") {
    return selectedRoomIds;
  }

  return selectedDoctorIds;
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

function saveCurrentRecord() {
  if (editorDialog.type === "hospital") {
    saveHospital();
    return;
  }

  if (editorDialog.type === "room") {
    saveRoom();
    return;
  }

  saveDoctor();
}

function saveHospital() {
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
    id: hospitalForm.id ?? hospitalIdSeed.value++,
    name: hospitalForm.name.trim(),
    level: hospitalForm.level.trim(),
    location: hospitalForm.location.trim(),
    shortIntro: hospitalForm.shortIntro.trim(),
    detailIntro: hospitalForm.detailIntro.trim(),
  };

  upsertCollection(hospitals.value, payload);
  editorDialog.visible = false;
  ElMessage.success(editorDialog.mode === "create" ? "医院已添加" : "医院信息已更新");
}

function saveRoom() {
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
    id: roomForm.id ?? roomIdSeed.value++,
    hospitalId: Number(roomForm.hospitalId),
    name: roomForm.name.trim(),
    floor: roomForm.floor.trim(),
    shortIntro: roomForm.shortIntro.trim(),
    detailIntro: roomForm.detailIntro.trim(),
  };

  upsertCollection(rooms.value, payload);
  editorDialog.visible = false;
  ElMessage.success(editorDialog.mode === "create" ? "诊室已添加" : "诊室信息已更新");
}

function saveDoctor() {
  if (
    !doctorForm.hospitalId ||
    !doctorForm.roomId ||
    !doctorForm.name.trim() ||
    !doctorForm.title.trim() ||
    !doctorForm.specialty.trim() ||
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
    id: doctorForm.id ?? doctorIdSeed.value++,
    hospitalId: Number(doctorForm.hospitalId),
    roomId: Number(doctorForm.roomId),
    name: doctorForm.name.trim(),
    title: doctorForm.title.trim(),
    specialty: doctorForm.specialty.trim(),
    shortIntro: doctorForm.shortIntro.trim(),
    detailIntro: doctorForm.detailIntro.trim(),
  };

  upsertCollection(doctors.value, payload);
  editorDialog.visible = false;
  ElMessage.success(editorDialog.mode === "create" ? "医生已添加" : "医生信息已更新");
}

function upsertCollection(collection, payload) {
  const index = collection.findIndex((item) => item?.id === payload.id);

  if (index === -1) {
    const emptyIndex = collection.findIndex((item) => item === null);

    if (emptyIndex !== -1) {
      collection.splice(emptyIndex, 1, payload);
      return;
    }

    collection.push(payload);
    return;
  }

  collection.splice(index, 1, payload);
}

async function removeHospital(item) {
  const roomCount = rooms.value.filter((room) => room?.hospitalId === item.id).length;
  const doctorCount = doctors.value.filter((doctor) => doctor?.hospitalId === item.id).length;

  await ElMessageBox.confirm(
    `删除后将一并移除 ${roomCount} 个诊室和 ${doctorCount} 位医生，确认继续吗？`,
    `删除医院：${item.name}`,
    {
      type: "warning",
      confirmButtonText: "确认删除",
      cancelButtonText: "取消",
    },
  );

  markCollectionItemAsEmpty(hospitals.value, item.id);
  markLinkedCollectionItemsAsEmpty(rooms.value, (room) => room.hospitalId === item.id);
  markLinkedCollectionItemsAsEmpty(doctors.value, (doctor) => doctor.hospitalId === item.id);
  selectedHospitalIds.value = selectedHospitalIds.value.filter((id) => id !== item.id);
  selectedRoomIds.value = selectedRoomIds.value.filter(
    (id) => rooms.value.some((room) => room.id === id),
  );
  selectedDoctorIds.value = selectedDoctorIds.value.filter(
    (id) => doctors.value.some((doctor) => doctor.id === id),
  );
  ElMessage.success("医院及关联数据已删除");
}

async function removeRoom(item) {
  const doctorCount = doctors.value.filter((doctor) => doctor?.roomId === item.id).length;

  await ElMessageBox.confirm(
    `删除后将一并移除 ${doctorCount} 位医生，确认继续吗？`,
    `删除诊室：${item.name}`,
    {
      type: "warning",
      confirmButtonText: "确认删除",
      cancelButtonText: "取消",
    },
  );

  markCollectionItemAsEmpty(rooms.value, item.id);
  markLinkedCollectionItemsAsEmpty(doctors.value, (doctor) => doctor.roomId === item.id);
  selectedRoomIds.value = selectedRoomIds.value.filter((id) => id !== item.id);
  selectedDoctorIds.value = selectedDoctorIds.value.filter(
    (id) => doctors.value.some((doctor) => doctor.id === id),
  );
  ElMessage.success("诊室及关联医生已删除");
}

async function removeDoctor(item) {
  await ElMessageBox.confirm(`确认删除医生“${item.name}”吗？`, "删除医生", {
    type: "warning",
    confirmButtonText: "确认删除",
    cancelButtonText: "取消",
  });

  markCollectionItemAsEmpty(doctors.value, item.id);
  selectedDoctorIds.value = selectedDoctorIds.value.filter((id) => id !== item.id);
  ElMessage.success("医生已删除");
}

async function removeSelectedItems() {
  const ids = [...currentSelection.value];

  if (!ids.length) {
    ElMessage.warning("请先选择要删除的数据");
    return;
  }

  if (activeModule.value === "hospital") {
    const selectedHospitals = visibleHospitals.value.filter((item) => ids.includes(item.id));
    const roomCount = rooms.value.filter((room) => ids.includes(room.hospitalId)).length;
    const doctorCount = doctors.value.filter((doctor) => ids.includes(doctor.hospitalId)).length;

    await ElMessageBox.confirm(
      `确认删除 ${selectedHospitals.length} 家医院吗？这会同时删除 ${roomCount} 个诊室和 ${doctorCount} 位医生。`,
      "批量删除医院",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );

    hospitals.value = hospitals.value.filter((item) => !ids.includes(item.id));
    rooms.value = rooms.value.filter((item) => !ids.includes(item.hospitalId));
    doctors.value = doctors.value.filter((item) => !ids.includes(item.hospitalId));
    selectedHospitalIds.value = [];
    selectedRoomIds.value = selectedRoomIds.value.filter((id) =>
      rooms.value.some((room) => room.id === id),
    );
    selectedDoctorIds.value = selectedDoctorIds.value.filter((id) =>
      doctors.value.some((doctor) => doctor.id === id),
    );
    ElMessage.success("已批量删除医院及关联数据");
    return;
  }

  if (activeModule.value === "room") {
    const selectedRooms = visibleRooms.value.filter((item) => ids.includes(item.id));
    const doctorCount = doctors.value.filter((doctor) => ids.includes(doctor.roomId)).length;

    await ElMessageBox.confirm(
      `确认删除 ${selectedRooms.length} 个诊室吗？这会同时删除 ${doctorCount} 位医生。`,
      "批量删除诊室",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );

    rooms.value = rooms.value.filter((item) => !ids.includes(item.id));
    doctors.value = doctors.value.filter((item) => !ids.includes(item.roomId));
    selectedRoomIds.value = [];
    selectedDoctorIds.value = selectedDoctorIds.value.filter((id) =>
      doctors.value.some((doctor) => doctor.id === id),
    );
    ElMessage.success("已批量删除诊室及关联医生");
    return;
  }

  await ElMessageBox.confirm(`确认删除 ${ids.length} 位医生吗？`, "批量删除医生", {
    type: "warning",
    confirmButtonText: "确认删除",
    cancelButtonText: "取消",
  });

  doctors.value = doctors.value.filter((item) => !ids.includes(item.id));
  selectedDoctorIds.value = [];
  ElMessage.success("已批量删除医生");
}

function markCollectionItemAsEmpty(collection, id) {
  const index = collection.findIndex((item) => item?.id === id);

  if (index !== -1) {
    collection.splice(index, 1);
  }
}

function markLinkedCollectionItemsAsEmpty(collection, matcher) {
  for (let index = collection.length - 1; index >= 0; index -= 1) {
    const item = collection[index];

    if (item && matcher(item)) {
      collection.splice(index, 1);
    }
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

        <div class="action-list">
          <el-button type="primary" size="large" class="home-button">
            <span class="button-label">AI 问诊</span>
          </el-button>
          <el-button size="large" plain class="home-button">
            <span class="button-label">挂号预约</span>
          </el-button>
          <el-button size="large" class="home-button admin-button" @click="goToAdmin">
            <span class="button-label">后台管理</span>
          </el-button>
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
          </div>

          <el-button plain class="back-home-button" @click="goHome">返回首页</el-button>
        </aside>

        <main class="admin-main">
          <header class="module-header">
            <div>
              <p class="module-eyebrow">后台管理</p>
              <h3>{{ currentTitle }}</h3>
              <p class="module-copy">{{ currentSubtitle }}</p>
            </div>

            <div class="module-actions">
              <el-button plain @click="toggleSelectAllCurrentModule">
                {{ isAllSelected ? "取消全选" : "全选" }}
              </el-button>
              <el-button plain :disabled="!currentSelection.length" @click="clearCurrentSelection">
                清空选择
              </el-button>
              <el-button
                plain
                class="bulk-delete-button"
                :disabled="!currentSelection.length"
                @click="removeSelectedItems"
              >
                批量删除（{{ currentSelection.length }}）
              </el-button>
              <el-button type="primary" size="large" @click="openCreateDialog(activeModule)">
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

          <section v-if="activeModule === 'hospital'" class="list-grid">
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

          <section v-if="activeModule === 'room'" class="list-grid">
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

          <section v-if="activeModule === 'doctor'" class="list-grid">
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
              <div class="entity-footer">
                <span>所属门诊资源</span>
                <div class="entity-actions">
                  <el-button text @click="showDetail('doctor', doctor)">查看详情</el-button>
                  <el-button text @click="openEditDialog('doctor', doctor)">编辑</el-button>
                  <el-button text class="danger-text" @click="removeDoctor(doctor)">删除</el-button>
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
          <div v-if="detailDialog.type === 'room'" class="detail-line">
            所属医院：{{ getHospitalName(detailDialog.item.hospitalId) }}
          </div>

          <div class="detail-block">
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
          <el-button type="primary" @click="saveCurrentRecord">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>
