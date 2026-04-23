package com.ihrs.backend.service;

import com.ihrs.backend.dto.AppointmentRequest;
import com.ihrs.backend.dto.AppointmentQuotaResponse;
import com.ihrs.backend.dto.AppointmentResponse;
import com.ihrs.backend.entity.Appointment;
import com.ihrs.backend.entity.ClinicRoom;
import com.ihrs.backend.entity.Doctor;
import com.ihrs.backend.entity.Hospital;
import com.ihrs.backend.exception.BadRequestException;
import com.ihrs.backend.exception.ResourceNotFoundException;
import com.ihrs.backend.repository.AppointmentRepository;
import com.ihrs.backend.repository.ClinicRoomRepository;
import com.ihrs.backend.repository.DoctorRepository;
import com.ihrs.backend.repository.HospitalRepository;
import com.ihrs.backend.security.AuthContext;
import java.util.Comparator;
import java.util.List;
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

    public AppointmentService(
        AppointmentRepository appointmentRepository,
        HospitalRepository hospitalRepository,
        ClinicRoomRepository clinicRoomRepository,
        DoctorRepository doctorRepository
    ) {
        this.appointmentRepository = appointmentRepository;
        this.hospitalRepository = hospitalRepository;
        this.clinicRoomRepository = clinicRoomRepository;
        this.doctorRepository = doctorRepository;
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
        String currentPhone = currentPatientPhone(patientPhone);
        return appointmentRepository.findByPatientPhoneOrderByAppointmentDateDescIdDesc(currentPhone).stream()
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
        String normalizedTimeSlot = request.timeSlot().trim();

        if (appointmentRepository.existsByPatientPhoneAndDoctorIdAndAppointmentDateAndTimeSlotAndStatus(
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

    private String currentPatientPhone(String fallbackPhone) {
        var currentUser = AuthContext.get();
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
        var currentUser = AuthContext.get();
        if (currentUser == null || AuthService.ROLE_ADMIN.equals(currentUser.role())) {
            return;
        }

        if (!appointment.getPatientPhone().equals(currentUser.phone())) {
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
}
