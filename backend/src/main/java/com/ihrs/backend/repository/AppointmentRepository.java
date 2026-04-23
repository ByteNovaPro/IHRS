package com.ihrs.backend.repository;

import com.ihrs.backend.entity.Appointment;
import java.time.LocalDate;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AppointmentRepository extends JpaRepository<Appointment, Long> {

    List<Appointment> findByPatientPhoneOrderByAppointmentDateDescIdDesc(String patientPhone);

    long countByDoctorIdAndAppointmentDateAndTimeSlotAndStatus(
        Long doctorId,
        LocalDate appointmentDate,
        String timeSlot,
        String status
    );

    boolean existsByPatientPhoneAndDoctorIdAndAppointmentDateAndTimeSlotAndStatus(
        String patientPhone,
        Long doctorId,
        LocalDate appointmentDate,
        String timeSlot,
        String status
    );
}
