package com.ihrs.backend.service;

import com.ihrs.backend.dto.AppointmentRequest;
import com.ihrs.backend.dto.AppointmentQuotaCalendarResponse;
import com.ihrs.backend.dto.AppointmentQuotaResponse;
import com.ihrs.backend.dto.AppointmentResponse;
import com.ihrs.backend.entity.Appointment;
import com.ihrs.backend.entity.ClinicRoom;
import com.ihrs.backend.entity.Doctor;
import com.ihrs.backend.entity.Hospital;
import com.ihrs.backend.entity.UserAccount;
import com.ihrs.backend.exception.BadRequestException;
import com.ihrs.backend.exception.ResourceNotFoundException;
import com.ihrs.backend.repository.AppointmentRepository;
import com.ihrs.backend.repository.ClinicRoomRepository;
import com.ihrs.backend.repository.DoctorRepository;
import com.ihrs.backend.repository.HospitalRepository;
import com.ihrs.backend.repository.UserAccountRepository;
import com.ihrs.backend.security.AuthContext;
import com.ihrs.backend.dto.SessionUser;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class AppointmentService {

    private static final String STATUS_RESERVED = "已预约";
    private static final String STATUS_CANCELED = "已取消";
    private static final long SLOT_CAPACITY = 10;

    private final AppointmentRepository appointmentRepository;
    private final HospitalRepository hospitalRepository;
    private final ClinicRoomRepository clinicRoomRepository;
    private final DoctorRepository doctorRepository;
    private final UserAccountRepository userAccountRepository;

    public AppointmentService(
        AppointmentRepository appointmentRepository,
        HospitalRepository hospitalRepository,
        ClinicRoomRepository clinicRoomRepository,
        DoctorRepository doctorRepository,
        UserAccountRepository userAccountRepository
    ) {
        this.appointmentRepository = appointmentRepository;
        this.hospitalRepository = hospitalRepository;
        this.clinicRoomRepository = clinicRoomRepository;
        this.doctorRepository = doctorRepository;
        this.userAccountRepository = userAccountRepository;
    }

    @Transactional(readOnly = true)
    public List<AppointmentResponse> listAppointments() {
        return appointmentRepository.findAll().stream()
            .sorted(
                Comparator.comparing(Appointment::getAppointmentDate).reversed()
                    .thenComparing(Appointment::getId, Comparator.reverseOrder())
            )
            .map(this::toResponse)
            .toList();
    }

    @Transactional(readOnly = true)
    public List<AppointmentResponse> listAppointmentsByPhone(String patientPhone) {
        SessionUser currentUser = AuthContext.get();
        String currentPhone = currentPatientPhone(patientPhone);
        Long currentUserId = currentUserId(currentUser);

        Stream<Appointment> appointments =
            currentUserId != null
                ? Stream.concat(
                    appointmentRepository.findByUserIdOrderByAppointmentDateDescIdDesc(currentUserId).stream(),
                    appointmentRepository.findByUserIsNullAndPatientPhoneOrderByAppointmentDateDescIdDesc(currentPhone).stream()
                )
                : appointmentRepository.findByPatientPhoneOrderByAppointmentDateDescIdDesc(currentPhone).stream();

        return appointments
            .sorted(
                Comparator.comparing(Appointment::getAppointmentDate).reversed()
                    .thenComparing(Appointment::getId, Comparator.reverseOrder())
            )
            .map(this::toResponse)
            .toList();
    }

    public AppointmentResponse createAppointment(AppointmentRequest request) {
        Hospital hospital = requireHospital(request.hospitalId());
        ClinicRoom room = requireRoom(request.roomId());
        Doctor doctor = requireDoctor(request.doctorId());

        if (!room.getHospital().getId().equals(hospital.getId())) {
            throw new BadRequestException("诊室与医院不匹配");
        }

        if (!doctor.getHospital().getId().equals(hospital.getId()) || !doctor.getRoom().getId().equals(room.getId())) {
            throw new BadRequestException("医生与所选医院/诊室不匹配");
        }

        if (doctor.getWorkTimeSlot() == null || !doctor.getWorkTimeSlot().equals(request.timeSlot().trim())) {
            throw new BadRequestException("医生不在所选预约时段上班");
        }

        String patientPhone = currentPatientPhone(request.patientPhone());
        UserAccount currentUser = currentUserAccount();
        Long currentUserId = currentUser == null ? null : currentUser.getId();
        String normalizedTimeSlot = request.timeSlot().trim();

        if (appointmentRepository.existsReservedConflictForUser(
            currentUserId,
            patientPhone,
            doctor.getId(),
            request.appointmentDate(),
            normalizedTimeSlot,
            STATUS_RESERVED
        )) {
            throw new BadRequestException("你已预约该医生当前时间段，不能重复预约");
        }

        long reservedCount = countReservedAppointments(doctor.getId(), request.appointmentDate(), normalizedTimeSlot);
        if (reservedCount >= SLOT_CAPACITY) {
            throw new BadRequestException("该医生当前时间段预约已满");
        }

        Appointment appointment = new Appointment();
        appointment.setHospital(hospital);
        appointment.setRoom(room);
        appointment.setDoctor(doctor);
        appointment.setUser(currentUser);
        appointment.setPatientName(request.patientName().trim());
        appointment.setPatientPhone(patientPhone);
        appointment.setAppointmentDate(request.appointmentDate());
        appointment.setTimeSlot(normalizedTimeSlot);
        appointment.setSymptom(request.symptom() == null ? "" : request.symptom().trim());
        appointment.setStatus(STATUS_RESERVED);
        return toResponse(appointmentRepository.save(appointment));
    }

    @Transactional(readOnly = true)
    public AppointmentQuotaResponse getQuota(Long doctorId, java.time.LocalDate appointmentDate, String timeSlot) {
        requireDoctor(doctorId);
        String normalizedTimeSlot = timeSlot.trim();
        long reservedCount = countReservedAppointments(doctorId, appointmentDate, normalizedTimeSlot);
        return new AppointmentQuotaResponse(
            doctorId,
            appointmentDate,
            normalizedTimeSlot,
            reservedCount,
            Math.max(SLOT_CAPACITY - reservedCount, 0),
            SLOT_CAPACITY
        );
    }

    @Transactional(readOnly = true)
    public AppointmentQuotaCalendarResponse getQuotaCalendar(
        List<Long> doctorIds,
        java.time.LocalDate startDate,
        java.time.LocalDate endDate
    ) {
        if (doctorIds == null || doctorIds.isEmpty()) {
            throw new BadRequestException("请至少选择一位医生");
        }

        if (startDate == null || endDate == null || endDate.isBefore(startDate)) {
            throw new BadRequestException("日期范围不合法");
        }

        List<Doctor> doctorList = doctorRepository.findAllById(doctorIds);
        if (doctorList.size() != doctorIds.stream().distinct().count()) {
            throw new ResourceNotFoundException("部分医生不存在");
        }

        Map<String, Long> reservedCountMap = new HashMap<>();
        for (Object[] row : appointmentRepository.countReservedAppointmentsByDoctorsAndDateRange(
            doctorIds,
            startDate,
            endDate,
            STATUS_RESERVED
        )) {
            Long doctorId = ((Number) row[0]).longValue();
            java.time.LocalDate appointmentDate = (java.time.LocalDate) row[1];
            String timeSlot = (String) row[2];
            long reservedCount = ((Number) row[3]).longValue();
            reservedCountMap.put(buildQuotaKey(doctorId, appointmentDate, timeSlot), reservedCount);
        }

        List<AppointmentQuotaResponse> quotas = doctorList.stream()
            .flatMap(doctor -> startDate.datesUntil(endDate.plusDays(1))
                .map(date -> {
                    String timeSlot = doctor.getWorkTimeSlot() == null ? "" : doctor.getWorkTimeSlot().trim();
                    long reservedCount = reservedCountMap.getOrDefault(buildQuotaKey(doctor.getId(), date, timeSlot), 0L);
                    return new AppointmentQuotaResponse(
                        doctor.getId(),
                        date,
                        timeSlot,
                        reservedCount,
                        Math.max(SLOT_CAPACITY - reservedCount, 0),
                        SLOT_CAPACITY
                    );
                }))
            .sorted(
                Comparator.comparing(AppointmentQuotaResponse::appointmentDate)
                    .thenComparing(AppointmentQuotaResponse::doctorId)
            )
            .toList();

        return new AppointmentQuotaCalendarResponse(startDate, endDate, quotas);
    }

    public AppointmentResponse cancelAppointment(Long id) {
        Appointment appointment = requireAppointment(id);
        ensureCanOperateAppointment(appointment);
        appointment.setStatus(STATUS_CANCELED);
        return toResponse(appointmentRepository.save(appointment));
    }

    public void deleteAppointment(Long id) {
        Appointment appointment = requireAppointment(id);
        ensureAdmin();
        appointmentRepository.delete(appointment);
    }

    private Hospital requireHospital(Long id) {
        return hospitalRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("医院不存在，id=" + id));
    }

    private ClinicRoom requireRoom(Long id) {
        return clinicRoomRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("诊室不存在，id=" + id));
    }

    private Doctor requireDoctor(Long id) {
        return doctorRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("医生不存在，id=" + id));
    }

    private Appointment requireAppointment(Long id) {
        return appointmentRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("预约不存在，id=" + id));
    }

    private long countReservedAppointments(Long doctorId, java.time.LocalDate appointmentDate, String timeSlot) {
        return appointmentRepository.countByDoctorIdAndAppointmentDateAndTimeSlotAndStatus(
            doctorId,
            appointmentDate,
            timeSlot,
            STATUS_RESERVED
        );
    }

    private String buildQuotaKey(Long doctorId, java.time.LocalDate appointmentDate, String timeSlot) {
        return doctorId + "|" + appointmentDate + "|" + timeSlot;
    }

    private String currentPatientPhone(String fallbackPhone) {
        SessionUser currentUser = AuthContext.get();
        String normalizedFallback = fallbackPhone == null ? "" : fallbackPhone.trim();
        if (currentUser == null) {
            return normalizedFallback;
        }

        if (AuthService.ROLE_ADMIN.equals(currentUser.role())) {
            return normalizedFallback;
        }

        return currentUser.phone();
    }

    private void ensureCanOperateAppointment(Appointment appointment) {
        SessionUser currentUser = AuthContext.get();
        if (currentUser == null || AuthService.ROLE_ADMIN.equals(currentUser.role())) {
            return;
        }

        Long currentUserId = currentUserId(currentUser);
        boolean canOperate =
            (currentUserId != null && appointment.getUser() != null && currentUserId.equals(appointment.getUser().getId()))
                || (appointment.getUser() == null && appointment.getPatientPhone().equals(currentUser.phone()));

        if (!canOperate) {
            throw new BadRequestException("只能操作自己的预约记录");
        }
    }

    private void ensureAdmin() {
        var currentUser = AuthContext.get();
        if (currentUser == null || !AuthService.ROLE_ADMIN.equals(currentUser.role())) {
            throw new BadRequestException("只有管理员可以删除预约记录");
        }
    }

    private AppointmentResponse toResponse(Appointment appointment) {
        return new AppointmentResponse(
            appointment.getId(),
            appointment.getUser() == null ? null : appointment.getUser().getId(),
            appointment.getHospital().getId(),
            appointment.getHospital().getName(),
            appointment.getRoom().getId(),
            appointment.getRoom().getName(),
            appointment.getDoctor().getId(),
            appointment.getDoctor().getName(),
            appointment.getDoctor().getTitle(),
            appointment.getPatientName(),
            appointment.getPatientPhone(),
            appointment.getAppointmentDate(),
            appointment.getTimeSlot(),
            appointment.getStatus(),
            appointment.getSymptom(),
            appointment.getCreatedAt(),
            appointment.getUpdatedAt()
        );
    }

    private Long currentUserId(SessionUser currentUser) {
        if (currentUser == null || AuthService.ROLE_ADMIN.equals(currentUser.role())) {
            return null;
        }
        return currentUser.id();
    }

    private UserAccount currentUserAccount() {
        SessionUser currentUser = AuthContext.get();
        Long currentUserId = currentUserId(currentUser);
        if (currentUserId != null) {
            return userAccountRepository.findById(currentUserId).orElse(null);
        }

        if (currentUser == null || AuthService.ROLE_ADMIN.equals(currentUser.role())) {
            return null;
        }

        return userAccountRepository.findByPhone(currentUser.phone()).orElse(null);
    }
}
