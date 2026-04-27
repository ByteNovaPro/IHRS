package com.ihrs.backend.config;

import com.ihrs.backend.entity.Appointment;
import com.ihrs.backend.entity.ClinicRoom;
import com.ihrs.backend.entity.Doctor;
import com.ihrs.backend.entity.Hospital;
import com.ihrs.backend.entity.UserAccount;
import com.ihrs.backend.repository.AppointmentRepository;
import com.ihrs.backend.repository.ClinicRoomRepository;
import com.ihrs.backend.repository.DoctorRepository;
import com.ihrs.backend.repository.HospitalRepository;
import com.ihrs.backend.repository.UserAccountRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class DemoDataInitializer implements ApplicationRunner {

    private static final int TARGET_HOSPITAL_COUNT = 1000;
    private static final List<String> BASE_HOSPITAL_NAMES = List.of(
        "上海市第一人民医院虹桥院区",
        "上海仁和国际医院",
        "上海静安康复医疗中心"
    );
    private static final List<String> DEFAULT_ROOM_NAMES = List.of(
        "心内诊室",
        "呼吸诊室",
        "消化诊室",
        "口腔专科"
    );
    private static final List<String> DEFAULT_ROOM_FLOORS = List.of(
        "2号楼 3 层",
        "2号楼 4 层",
        "3号楼 2 层",
        "门诊楼 5 层"
    );
    private static final List<String> DEFAULT_ROOM_SHORT_INTROS = List.of(
        "面向胸闷、心悸、高血压等心血管问题接诊。",
        "适合咳嗽、发热、气短和呼吸道疾病初诊复诊。",
        "面向胃痛、反酸、腹胀、便秘腹泻等消化症状。",
        "覆盖牙痛、牙龈炎、洁牙修复和基础口腔评估。"
    );
    private static final List<String> DEFAULT_ROOM_DETAIL_INTROS = List.of(
        "诊室提供心电图初筛、慢病随访、血压管理和心血管风险评估等门诊服务。",
        "诊室聚焦呼吸道感染、哮喘、慢阻肺和肺结节复诊，支持肺功能检查协同开单。",
        "诊室覆盖胃食管反流、慢性胃炎、肠易激和消化道筛查咨询等场景，可联动胃肠镜检查。",
        "门诊提供牙体牙髓、牙周基础治疗、口腔保健咨询和初步修复评估等服务。"
    );
    private static final List<String> DEFAULT_WORK_TIME_SLOTS = List.of(
        "上午 08:30-10:30",
        "上午 10:30-12:00",
        "下午 14:00-16:00"
    );
    private static final String ROLE_USER = "USER";
    private static final String STATUS_RESERVED = "已预约";
    private static final String STATUS_CANCELED = "已取消";

    private final HospitalRepository hospitalRepository;
    private final ClinicRoomRepository clinicRoomRepository;
    private final DoctorRepository doctorRepository;
    private final UserAccountRepository userAccountRepository;
    private final AppointmentRepository appointmentRepository;
    private final boolean enabled;

    public DemoDataInitializer(
        HospitalRepository hospitalRepository,
        ClinicRoomRepository clinicRoomRepository,
        DoctorRepository doctorRepository,
        UserAccountRepository userAccountRepository,
        AppointmentRepository appointmentRepository,
        @Value("${app.demo-data.enabled:true}") boolean enabled
    ) {
        this.hospitalRepository = hospitalRepository;
        this.clinicRoomRepository = clinicRoomRepository;
        this.doctorRepository = doctorRepository;
        this.userAccountRepository = userAccountRepository;
        this.appointmentRepository = appointmentRepository;
        this.enabled = enabled;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        if (!enabled) {
            return;
        }

        Map<String, Hospital> hospitalMap = seedHospitals();
        Map<String, ClinicRoom> roomMap = seedRooms(hospitalMap);
        Map<String, Doctor> doctorMap = seedDoctors(hospitalMap, roomMap);
        Map<String, UserAccount> userMap = seedUsers();
        seedAppointments(doctorMap, userMap);
    }

    private Map<String, Hospital> seedHospitals() {
        Map<String, Hospital> existing = new LinkedHashMap<>();
        for (Hospital hospital : hospitalRepository.findAll()) {
            existing.put(hospital.getName(), hospital);
        }

        List<HospitalSeed> seeds = buildHospitalSeeds();

        for (HospitalSeed seed : seeds) {
            Hospital hospital = existing.get(seed.name());
            if (hospital == null) {
                hospital = new Hospital();
            }
            hospital.setName(seed.name());
            hospital.setLevel(seed.level());
            hospital.setLocation(seed.location());
            hospital.setShortIntro(seed.shortIntro());
            hospital.setDetailIntro(seed.detailIntro());
            existing.put(seed.name(), hospitalRepository.save(hospital));
        }

        return existing;
    }

    private List<HospitalSeed> buildHospitalSeeds() {
        List<HospitalSeed> baseSeeds = List.of(
            new HospitalSeed(
                "上海市第一人民医院虹桥院区",
                "三级甲等",
                "上海市长宁区仙霞路1111号",
                "综合实力较强，覆盖心内、呼吸、消化等常见专科门诊。",
                "医院以心血管、呼吸系统和慢病管理为特色，门诊分区清晰，适合常见内科、复诊随访和影像检查联动就医。"
            ),
            new HospitalSeed(
                "上海仁和国际医院",
                "三级综合",
                "上海市浦东新区锦绣路88号",
                "面向家庭就诊场景，重视妇儿、消化和口腔专科协同。",
                "医院提供妇儿保健、消化专科、口腔诊疗和健康管理服务，适合家庭成员联合建档、复诊和检查预约。"
            ),
            new HospitalSeed(
                "上海静安康复医疗中心",
                "二级专科",
                "上海市静安区共和新路518号",
                "聚焦康复、中医调理与疼痛管理，适合术后恢复与慢病康复。",
                "中心面向颈肩腰腿痛、术后恢复、睡眠调理和亚健康干预等场景，强调康复评估、针灸理疗和运动干预结合。"
            )
        );

        List<String> cityNames = List.of(
            "上海", "北京", "广州", "深圳", "杭州", "南京", "苏州", "成都", "重庆", "武汉",
            "西安", "天津", "长沙", "郑州", "青岛", "合肥", "宁波", "厦门", "福州", "济南"
        );
        List<String> districtNames = List.of(
            "朝阳区", "浦东新区", "天河区", "南山区", "西湖区", "鼓楼区", "工业园区", "高新区", "渝北区", "武昌区",
            "雁塔区", "河西区", "岳麓区", "金水区", "市南区", "蜀山区", "鄞州区", "思明区", "台江区", "历下区"
        );
        List<String> levels = List.of("三级甲等", "三级综合", "二级甲等", "二级综合");
        List<String> featureTags = List.of(
            "综合内科", "妇儿协同", "康复医学", "口腔诊疗", "心血管评估",
            "消化门诊", "呼吸慢病", "健康管理", "中医调理", "老年医学"
        );
        List<String> shortTemplates = List.of(
            "以%s和门诊分诊协同为特色，适合常见疾病初诊复诊。",
            "覆盖%s等高频就诊方向，适合家庭与个人门诊预约。",
            "重视%s和检查联动，适合首诊分流与复诊管理。",
            "提供%s等多学科门诊支持，适合线上导诊后到院就诊。"
        );
        List<String> detailTemplates = List.of(
            "医院围绕%s、检查预约与慢病随访建立了较完整的门诊服务流程，适合常见专科初诊、复诊及健康评估。",
            "院区以%s为重点服务方向，兼顾常规门诊、影像检验协同和预约挂号体验，适合课程设计与系统演示场景。",
            "医院在%s、家庭就诊和门诊调度方面形成了稳定流程，可承接导诊、预约、复诊和基础健康管理需求。",
            "该院区强调%s与就诊动线优化，适合门诊首诊分流、专科复诊以及后续检查预约等典型场景。"
        );

        List<HospitalSeed> seeds = new java.util.ArrayList<>(TARGET_HOSPITAL_COUNT);
        seeds.addAll(baseSeeds);

        for (int index = 0; index < TARGET_HOSPITAL_COUNT - baseSeeds.size(); index++) {
            String city = cityNames.get(index % cityNames.size());
            String district = districtNames.get(index % districtNames.size());
            String feature = featureTags.get(index % featureTags.size());
            String level = levels.get(index % levels.size());
            String name = city + "示范医院" + String.format("%03d", index + 1) + "院区";
            String location = city + "市" + district + "健康大道" + (100 + index) + "号";
            String shortIntro = String.format(
                shortTemplates.get(index % shortTemplates.size()),
                feature
            );
            String detailIntro = String.format(
                detailTemplates.get(index % detailTemplates.size()),
                feature
            );
            seeds.add(new HospitalSeed(name, level, location, shortIntro, detailIntro));
        }

        return seeds;
    }

    private Map<String, ClinicRoom> seedRooms(Map<String, Hospital> hospitalMap) {
        Map<String, ClinicRoom> existing = new HashMap<>();
        for (ClinicRoom room : clinicRoomRepository.findAll()) {
            existing.put(buildRoomKey(room.getHospital().getName(), room.getName()), room);
        }

        List<RoomSeed> seeds = new java.util.ArrayList<>(List.of(
            new RoomSeed("上海市第一人民医院虹桥院区", "心内诊室", "2号楼 3 层", "面向胸闷、心悸、高血压等心血管问题接诊。", "诊室提供心电图初筛、慢病随访、血压管理和心血管风险评估等门诊服务。"),
            new RoomSeed("上海市第一人民医院虹桥院区", "呼吸诊室", "2号楼 4 层", "适合咳嗽、发热、气短和呼吸道疾病初诊复诊。", "诊室聚焦呼吸道感染、哮喘、慢阻肺和肺结节复诊，支持肺功能检查协同开单。"),
            new RoomSeed("上海市第一人民医院虹桥院区", "消化诊室", "3号楼 2 层", "面向胃痛、反酸、腹胀、便秘腹泻等消化症状。", "诊室覆盖胃食管反流、慢性胃炎、肠易激和消化道筛查咨询等场景，可联动胃肠镜检查。"),
            new RoomSeed("上海仁和国际医院", "儿科门诊", "A座 2 层", "提供儿童常见病、发热咳嗽、营养发育咨询服务。", "儿科面向儿童呼吸道感染、过敏、发育评估和常规复诊，接诊流程更适合家庭陪诊。"),
            new RoomSeed("上海仁和国际医院", "产科门诊", "A座 5 层", "面向孕检、胎动异常、孕期随访与围产咨询。", "产科提供产前建档、妊娠期常规检查、胎心监测和分娩前风险评估等服务。"),
            new RoomSeed("上海仁和国际医院", "口腔专科", "B座 3 层", "覆盖牙痛、牙龈炎、龋齿修复和正畸评估。", "口腔专科提供牙体牙髓、牙周基础治疗、儿童口腔保健和初步正畸咨询。"),
            new RoomSeed("上海静安康复医疗中心", "针灸康复科", "康复楼 2 层", "适合颈肩腰腿痛、扭伤、术后恢复和疼痛管理。", "门诊融合康复评定、针灸、理疗和运动训练建议，适合慢性疼痛与术后恢复阶段。"),
            new RoomSeed("上海静安康复医疗中心", "中医内科/治未病门诊", "康复楼 3 层", "适合失眠、乏力、体质调理和亚健康干预。", "门诊重视辨证调理、睡眠管理、季节性体质干预和慢病日常养护建议。")
        ));

        int generatedHospitalIndex = 0;
        for (String hospitalName : hospitalMap.keySet()) {
            if (BASE_HOSPITAL_NAMES.contains(hospitalName)) {
                continue;
            }

            for (int roomIndex = 0; roomIndex < DEFAULT_ROOM_NAMES.size(); roomIndex++) {
                String roomName = DEFAULT_ROOM_NAMES.get(roomIndex);
                String floor = DEFAULT_ROOM_FLOORS.get(roomIndex);
                String shortIntro = DEFAULT_ROOM_SHORT_INTROS.get(roomIndex);
                String detailIntro = DEFAULT_ROOM_DETAIL_INTROS.get(roomIndex)
                    + " 示范院区编号 " + String.format("%03d", generatedHospitalIndex + 1) + " 支持该专科基础预约场景。";
                seeds.add(new RoomSeed(hospitalName, roomName, floor, shortIntro, detailIntro));
            }

            generatedHospitalIndex++;
        }

        for (RoomSeed seed : seeds) {
            ClinicRoom room = existing.get(buildRoomKey(seed.hospitalName(), seed.name()));
            if (room == null) {
                room = new ClinicRoom();
            }
            room.setHospital(hospitalMap.get(seed.hospitalName()));
            room.setName(seed.name());
            room.setFloor(seed.floor());
            room.setShortIntro(seed.shortIntro());
            room.setDetailIntro(seed.detailIntro());
            existing.put(buildRoomKey(seed.hospitalName(), seed.name()), clinicRoomRepository.save(room));
        }

        return existing;
    }

    private Map<String, Doctor> seedDoctors(Map<String, Hospital> hospitalMap, Map<String, ClinicRoom> roomMap) {
        List<DoctorSeed> seeds = new java.util.ArrayList<>(List.of(
            new DoctorSeed("上海市第一人民医院虹桥院区", "心内诊室", "周明远", "主任医师", "高血压、冠心病、心律失常评估", "上午 08:30-10:30", "擅长常见心血管疾病门诊评估与长期随访。", "长期从事高血压、冠心病和心律失常门诊管理，重视检查结果解读与用药调整。"),
            new DoctorSeed("上海市第一人民医院虹桥院区", "心内诊室", "赵衡川", "副主任医师", "胸痛筛查、心衰随访、动脉硬化风险管理", "上午 10:30-12:00", "偏重胸痛初筛和慢病复诊管理。", "擅长胸痛分层评估、心功能异常复诊及心血管危险因素长期管理。"),
            new DoctorSeed("上海市第一人民医院虹桥院区", "心内诊室", "沈嘉宁", "副主任医师", "胸闷胸痛筛查、心电图异常复诊", "下午 14:00-16:00", "擅长胸闷、心悸等症状的初诊排查。", "关注门诊初筛效率，适合胸闷、心悸、运动后气短等常见主诉患者首诊。"),
            new DoctorSeed("上海市第一人民医院虹桥院区", "呼吸诊室", "顾晨曦", "主任医师", "慢性咳嗽、哮喘、慢阻肺", "上午 08:30-10:30", "擅长呼吸系统慢病管理与复诊随访。", "对慢性咳嗽、哮喘和慢阻肺诊疗经验丰富，注重吸入治疗和生活方式管理。"),
            new DoctorSeed("上海市第一人民医院虹桥院区", "呼吸诊室", "林致远", "副主任医师", "肺结节复诊、呼吸功能评估", "上午 10:30-12:00", "擅长肺部影像异常随访与门诊评估。", "长期参与肺结节、反复胸闷气短及肺功能下降患者的门诊随访。"),
            new DoctorSeed("上海市第一人民医院虹桥院区", "呼吸诊室", "陆安和", "主治医师", "发热咳嗽、急性上呼吸道感染", "下午 16:00-17:30", "适合近期发热、咳嗽、气短等急性症状就诊。", "门诊接诊节奏较快，适合急性呼吸道症状初诊、复查和药物调整。"),
            new DoctorSeed("上海市第一人民医院虹桥院区", "消化诊室", "何思远", "主任医师", "反酸烧心、胃炎、胃肠功能紊乱", "上午 08:30-10:30", "专注反流、胃痛、腹胀等常见消化问题。", "擅长胃食管反流、慢性胃炎和功能性胃肠病的门诊诊治，可对接内镜检查建议。"),
            new DoctorSeed("上海市第一人民医院虹桥院区", "消化诊室", "许砚秋", "副主任医师", "腹痛腹泻、肠道炎症、肠镜前评估", "上午 10:30-12:00", "适合腹泻、腹痛和肠道问题门诊评估。", "关注肠道炎症、反复腹痛腹泻和检查前评估，适合消化道症状较复杂的患者。"),
            new DoctorSeed("上海市第一人民医院虹桥院区", "消化诊室", "蒋书亦", "主治医师", "便秘、腹胀、饮食相关消化不适", "下午 14:00-16:00", "偏重常见消化不适与生活方式管理。", "擅长便秘、腹胀、饮食不耐受等常见问题的门诊评估和日常管理建议。"),
            new DoctorSeed("上海仁和国际医院", "儿科门诊", "林知夏", "副主任医师", "儿童发热、咳嗽、过敏性鼻炎", "上午 08:30-10:30", "适合儿童常见呼吸道疾病和过敏问题就诊。", "长期从事儿童常见病和过敏相关疾病诊疗，沟通风格偏细致，适合家长咨询。"),
            new DoctorSeed("上海仁和国际医院", "儿科门诊", "吴澄悦", "主治医师", "儿童腹泻、积食、营养发育咨询", "上午 10:30-12:00", "适合儿童消化和营养问题随访。", "擅长儿童轻中度消化不适、喂养问题和生长发育咨询，适合家长复诊沟通。"),
            new DoctorSeed("上海仁和国际医院", "儿科门诊", "陈之言", "主治医师", "儿童发热复诊、夜咳、支气管炎", "下午 14:00-16:00", "门诊节奏快，适合儿童急性症状复诊。", "重点接诊儿童发热、夜间咳嗽和支气管炎恢复期复查患者。"),
            new DoctorSeed("上海仁和国际医院", "产科门诊", "许清妍", "主任医师", "孕期建档、产检、妊娠期风险评估", "上午 08:30-10:30", "专注产检建档和孕中晚期随访。", "擅长围产管理和孕期常见问题解答，适合产检、胎动异常和复诊预约。"),
            new DoctorSeed("上海仁和国际医院", "产科门诊", "顾闻溪", "副主任医师", "孕期血糖管理、胎动异常评估", "上午 10:30-12:00", "擅长妊娠期常见并发症门诊管理。", "长期接诊妊娠期血糖异常、血压异常及胎动变化相关门诊患者。"),
            new DoctorSeed("上海仁和国际医院", "产科门诊", "程念真", "主治医师", "孕早期不适、孕检结果解读、复诊随访", "下午 14:00-16:00", "适合孕早期建档和检查结果咨询。", "门诊关注孕早期不适、产检单解读和中期复查安排，沟通细致。"),
            new DoctorSeed("上海仁和国际医院", "口腔专科", "唐以安", "主治医师", "牙痛、龋齿修复、牙龈炎基础治疗", "上午 08:30-10:30", "适合牙痛、牙龈出血和口腔基础治疗咨询。", "专注牙体牙髓和牙周基础治疗，适合常见口腔问题初诊。"),
            new DoctorSeed("上海仁和国际医院", "口腔专科", "叶舒白", "副主任医师", "阻生齿评估、牙周治疗、口腔炎症", "上午 10:30-12:00", "适合反复牙龈肿痛和牙周问题就诊。", "擅长牙周治疗、阻生齿初步评估和反复口腔炎症管理。"),
            new DoctorSeed("上海仁和国际医院", "口腔专科", "韩星洲", "主治医师", "儿童龋齿、洁牙、基础修复", "下午 16:00-17:30", "适合家庭口腔保健和儿童常见龋齿复诊。", "门诊偏向家庭口腔保健、儿童龋齿和常见修复治疗前咨询。"),
            new DoctorSeed("上海静安康复医疗中心", "针灸康复科", "陈沐川", "副主任医师", "颈肩腰腿痛、运动损伤康复", "上午 08:30-10:30", "适合久坐劳损、扭伤和术后康复阶段咨询。", "擅长肌骨疼痛、运动损伤和术后康复评估，强调运动训练与理疗结合。"),
            new DoctorSeed("上海静安康复医疗中心", "针灸康复科", "周至衡", "主任医师", "腰椎间盘突出、膝关节痛、康复方案设计", "下午 14:00-16:00", "适合慢性疼痛和康复计划制定。", "擅长慢性腰腿痛、膝关节退变和系统性康复方案制定，适合多次随访。"),
            new DoctorSeed("上海静安康复医疗中心", "针灸康复科", "苏清屿", "主治医师", "落枕、肩周炎、急性肌肉拉伤", "下午 16:00-17:30", "适合近期扭伤、拉伤和肩颈急性疼痛患者。", "门诊面向急性肌骨疼痛和肩颈劳损患者，强调早期干预和恢复训练建议。"),
            new DoctorSeed("上海静安康复医疗中心", "中医内科/治未病门诊", "梁舒宁", "主任中医师", "失眠、乏力、体质调理", "上午 08:30-10:30", "擅长亚健康、睡眠和慢性疲劳调理。", "以睡眠障碍、体质调理和慢病养护见长，适合希望进行中医调理的患者。"),
            new DoctorSeed("上海静安康复医疗中心", "中医内科/治未病门诊", "沈知微", "副主任中医师", "女性调理、脾胃虚弱、季节性体质管理", "上午 10:30-12:00", "适合慢性疲劳、食欲差和体质调养。", "长期关注脾胃虚弱、季节性体质变化和女性常见亚健康问题的中医调理。"),
            new DoctorSeed("上海静安康复医疗中心", "中医内科/治未病门诊", "季南乔", "主治中医师", "焦虑伴失眠、头痛、日常养生干预", "下午 14:00-16:00", "适合工作压力大、睡眠差和反复头痛患者。", "门诊关注情绪压力相关失眠、紧张性头痛和日常作息调理建议。")
        ));

        List<String> surnames = List.of("林", "周", "许", "顾", "沈", "陈", "蒋", "叶", "苏", "季", "唐", "韩", "程", "梁", "吴", "何");
        List<String> givenNames = List.of("知安", "明川", "书言", "闻溪", "清屿", "若衡", "星洲", "景然", "以宁", "思远", "砚秋", "安和", "舒宁", "知微", "南乔", "晨曦");

        int generatedHospitalIndex = 0;
        for (String hospitalName : hospitalMap.keySet()) {
            if (BASE_HOSPITAL_NAMES.contains(hospitalName)) {
                continue;
            }

            for (int roomIndex = 0; roomIndex < DEFAULT_ROOM_NAMES.size(); roomIndex++) {
                String roomName = DEFAULT_ROOM_NAMES.get(roomIndex);
                for (int slotIndex = 0; slotIndex < DEFAULT_WORK_TIME_SLOTS.size(); slotIndex++) {
                    String workTimeSlot = DEFAULT_WORK_TIME_SLOTS.get(slotIndex);
                    int doctorIndex = generatedHospitalIndex * DEFAULT_ROOM_NAMES.size() * DEFAULT_WORK_TIME_SLOTS.size()
                        + roomIndex * DEFAULT_WORK_TIME_SLOTS.size()
                        + slotIndex;
                    String name = surnames.get(doctorIndex % surnames.size()) + givenNames.get((doctorIndex / surnames.size()) % givenNames.size());
                    String title = switch (slotIndex) {
                        case 0 -> "主任医师";
                        case 1 -> "副主任医师";
                        default -> "主治医师";
                    };
                    String specialty = generatedSpecialtyForRoom(roomName, slotIndex);
                    String shortIntro = "擅长" + specialty + "相关问题的门诊评估与常规复诊。";
                    String detailIntro = "示范院区医生主要接诊" + specialty + "相关主诉，适合系统演示中的导诊、挂号和常见复诊预约场景。";
                    seeds.add(new DoctorSeed(hospitalName, roomName, name, title, specialty, workTimeSlot, shortIntro, detailIntro));
                }
            }

            generatedHospitalIndex++;
        }

        reconcileManagedDoctors(seeds);

        Map<String, Doctor> existing = new HashMap<>();
        for (Doctor doctor : doctorRepository.findAll()) {
            existing.put(buildDoctorKey(doctor.getHospital().getName(), doctor.getRoom().getName(), doctor.getWorkTimeSlot()), doctor);
        }

        for (DoctorSeed seed : seeds) {
            String roomKey = buildRoomKey(seed.hospitalName(), seed.roomName());
            Doctor doctor = existing.get(buildDoctorKey(seed.hospitalName(), seed.roomName(), seed.workTimeSlot()));
            if (doctor == null) {
                doctor = new Doctor();
            }
            doctor.setHospital(hospitalMap.get(seed.hospitalName()));
            doctor.setRoom(roomMap.get(roomKey));
            doctor.setName(seed.name());
            doctor.setTitle(seed.title());
            doctor.setSpecialty(seed.specialty());
            doctor.setWorkTimeSlot(seed.workTimeSlot());
            doctor.setShortIntro(seed.shortIntro());
            doctor.setDetailIntro(seed.detailIntro());
            existing.put(buildDoctorKey(seed.hospitalName(), seed.roomName(), seed.workTimeSlot()), doctorRepository.save(doctor));
        }

        return existing;
    }

    private String generatedSpecialtyForRoom(String roomName, int slotIndex) {
        return switch (roomName) {
            case "心内诊室" -> switch (slotIndex) {
                case 0 -> "高血压与冠心病评估";
                case 1 -> "胸闷心悸与心电图异常复诊";
                default -> "慢病随访与心血管风险管理";
            };
            case "呼吸诊室" -> switch (slotIndex) {
                case 0 -> "咳嗽发热与呼吸道感染评估";
                case 1 -> "哮喘慢阻肺与气短复诊";
                default -> "肺功能评估与慢性咳嗽管理";
            };
            case "消化诊室" -> switch (slotIndex) {
                case 0 -> "胃痛反酸与消化不适评估";
                case 1 -> "腹痛腹泻与肠道问题复诊";
                default -> "便秘腹胀与饮食相关消化管理";
            };
            case "口腔专科" -> switch (slotIndex) {
                case 0 -> "牙痛龋齿与牙龈问题评估";
                case 1 -> "牙周治疗与口腔炎症复诊";
                default -> "洁牙修复与基础口腔保健";
            };
            default -> "常见门诊问题评估";
        };
    }

    private void reconcileManagedDoctors(List<DoctorSeed> seeds) {
        Set<String> managedRoomKeys = seeds.stream()
            .map(seed -> buildRoomKey(seed.hospitalName(), seed.roomName()))
            .collect(Collectors.toSet());
        Set<String> desiredDoctorKeys = seeds.stream()
            .map(seed -> buildDoctorKey(seed.hospitalName(), seed.roomName(), seed.workTimeSlot()))
            .collect(Collectors.toSet());

        List<Doctor> obsoleteDoctors = doctorRepository.findAll().stream()
            .filter(doctor -> managedRoomKeys.contains(buildRoomKey(doctor.getHospital().getName(), doctor.getRoom().getName())))
            .filter(doctor -> !desiredDoctorKeys.contains(buildDoctorKey(
                doctor.getHospital().getName(),
                doctor.getRoom().getName(),
                doctor.getWorkTimeSlot()
            )))
            .toList();

        if (obsoleteDoctors.isEmpty()) {
            return;
        }

        Set<Long> obsoleteDoctorIds = obsoleteDoctors.stream()
            .map(Doctor::getId)
            .collect(Collectors.toSet());

        List<Appointment> obsoleteAppointments = appointmentRepository.findAll().stream()
            .filter(appointment -> obsoleteDoctorIds.contains(appointment.getDoctor().getId()))
            .toList();

        if (!obsoleteAppointments.isEmpty()) {
            appointmentRepository.deleteAll(obsoleteAppointments);
        }

        doctorRepository.deleteAll(obsoleteDoctors);
    }

    private Map<String, UserAccount> seedUsers() {
        Map<String, UserAccount> users = new HashMap<>();
        for (UserAccount user : userAccountRepository.findAll()) {
            users.put(user.getPhone(), user);
        }

        List<UserSeed> seeds = List.of(
            new UserSeed("13912345678", "测试用户", "test123456"),
            new UserSeed("13900001111", "李晓晨", "patient123"),
            new UserSeed("13788889999", "王若宁", "patient123")
        );

        for (UserSeed seed : seeds) {
            UserAccount user = users.get(seed.phone());
            if (user == null) {
                user = new UserAccount();
                user.setPhone(seed.phone());
                user.setRole(ROLE_USER);
            }
            user.setName(seed.name());
            user.setPasswordHash(hashPassword(seed.password()));
            users.put(seed.phone(), userAccountRepository.save(user));
        }

        return users;
    }

    private void seedAppointments(Map<String, Doctor> doctorMap, Map<String, UserAccount> userMap) {
        Map<String, Appointment> existing = new HashMap<>();
        for (Appointment appointment : appointmentRepository.findAll()) {
            existing.put(
                buildAppointmentKey(
                    appointment.getPatientPhone(),
                    appointment.getDoctor().getId(),
                    appointment.getAppointmentDate(),
                    appointment.getTimeSlot()
                ),
                appointment
            );
        }

        LocalDate today = LocalDate.now();
        List<AppointmentSeed> seeds = List.of(
            new AppointmentSeed("13912345678", "测试用户", "上海市第一人民医院虹桥院区", "心内诊室", "上午 08:30-10:30", today.plusDays(1), "胸闷心悸两天，活动后气短", STATUS_RESERVED, true),
            new AppointmentSeed("13900001111", "李晓晨", "上海市第一人民医院虹桥院区", "呼吸诊室", "上午 10:30-12:00", today.plusDays(2), "咳嗽三天，夜间加重", STATUS_RESERVED, true),
            new AppointmentSeed("13788889999", "王若宁", "上海仁和国际医院", "产科门诊", "下午 14:00-16:00", today.plusDays(3), "孕24周常规产检复诊", STATUS_RESERVED, true),
            new AppointmentSeed("13666668888", "赵梓涵", "上海静安康复医疗中心", "针灸康复科", "下午 14:00-16:00", today.plusDays(4), "久坐腰痛伴右腿酸胀", STATUS_RESERVED, false),
            new AppointmentSeed("13555557777", "陈可欣", "上海仁和国际医院", "口腔专科", "上午 10:30-12:00", today.plusDays(5), "右侧后牙疼痛两周", STATUS_RESERVED, false),
            new AppointmentSeed("13912345678", "测试用户", "上海市第一人民医院虹桥院区", "消化诊室", "上午 08:30-10:30", today.minusDays(2), "反酸烧心反复发作", STATUS_CANCELED, true)
        );

        for (AppointmentSeed seed : seeds) {
            Doctor doctor = doctorMap.get(buildDoctorKey(seed.hospitalName(), seed.roomName(), seed.timeSlot()));
            if (doctor == null) {
                continue;
            }

            String key = buildAppointmentKey(seed.patientPhone(), doctor.getId(), seed.appointmentDate(), seed.timeSlot());
            Appointment appointment = existing.get(key);
            if (appointment == null) {
                appointment = new Appointment();
            }

            appointment.setHospital(doctor.getHospital());
            appointment.setRoom(doctor.getRoom());
            appointment.setDoctor(doctor);
            appointment.setUser(seed.bindUser() ? userMap.get(seed.patientPhone()) : null);
            appointment.setPatientPhone(seed.patientPhone());
            appointment.setPatientName(seed.patientName());
            appointment.setAppointmentDate(seed.appointmentDate());
            appointment.setTimeSlot(seed.timeSlot());
            appointment.setSymptom(seed.symptom());
            appointment.setStatus(seed.status());
            existing.put(key, appointmentRepository.save(appointment));
        }
    }

    private String hashPassword(String password) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(password.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private String buildRoomKey(String hospitalName, String roomName) {
        return hospitalName + "|" + roomName;
    }

    private String buildDoctorKey(String hospitalName, String roomName, String workTimeSlot) {
        return hospitalName + "|" + roomName + "|" + workTimeSlot;
    }

    private String buildAppointmentKey(String patientPhone, Long doctorId, LocalDate appointmentDate, String timeSlot) {
        return patientPhone + "|" + doctorId + "|" + appointmentDate + "|" + timeSlot;
    }

    private record HospitalSeed(
        String name,
        String level,
        String location,
        String shortIntro,
        String detailIntro
    ) {
    }

    private record RoomSeed(
        String hospitalName,
        String name,
        String floor,
        String shortIntro,
        String detailIntro
    ) {
    }

    private record DoctorSeed(
        String hospitalName,
        String roomName,
        String name,
        String title,
        String specialty,
        String workTimeSlot,
        String shortIntro,
        String detailIntro
    ) {
    }

    private record UserSeed(String phone, String name, String password) {
    }

    private record AppointmentSeed(
        String patientPhone,
        String patientName,
        String hospitalName,
        String roomName,
        String timeSlot,
        LocalDate appointmentDate,
        String symptom,
        String status,
        boolean bindUser
    ) {
    }
}
