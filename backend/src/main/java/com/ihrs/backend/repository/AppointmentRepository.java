package com.ihrs.backend.repository;

import com.ihrs.backend.entity.Appointment;
import java.time.LocalDate;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AppointmentRepository extends JpaRepository<Appointment, Long> {

    List<Appointment> findByPatientPhoneOrderByAppointmentDateDescIdDesc(String patientPhone);

    List<Appointment> findByUserIdOrderByAppointmentDateDescIdDesc(Long userId);

    List<Appointment> findByUserIsNullAndPatientPhoneOrderByAppointmentDateDescIdDesc(String patientPhone);

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

    List<Appointment> findByUserIsNull();

    @Query("""
        select count(a) > 0
        from Appointment a
        where a.doctor.id = :doctorId
          and a.appointmentDate = :appointmentDate
          and a.timeSlot = :timeSlot
          and a.status = :status
          and (
            (:userId is not null and a.user.id = :userId)
            or (a.user is null and a.patientPhone = :patientPhone)
          )
    """)
    boolean existsReservedConflictForUser(
        @Param("userId") Long userId,
        @Param("patientPhone") String patientPhone,
        @Param("doctorId") Long doctorId,
        @Param("appointmentDate") LocalDate appointmentDate,
        @Param("timeSlot") String timeSlot,
        @Param("status") String status
    );

    @Query("""
        select a.doctor.id, a.appointmentDate, a.timeSlot, count(a)
        from Appointment a
        where a.doctor.id in :doctorIds
          and a.appointmentDate between :startDate and :endDate
          and a.status = :status
        group by a.doctor.id, a.appointmentDate, a.timeSlot
    """)
    List<Object[]> countReservedAppointmentsByDoctorsAndDateRange(
        @Param("doctorIds") List<Long> doctorIds,
        @Param("startDate") LocalDate startDate,
        @Param("endDate") LocalDate endDate,
        @Param("status") String status
    );
}
