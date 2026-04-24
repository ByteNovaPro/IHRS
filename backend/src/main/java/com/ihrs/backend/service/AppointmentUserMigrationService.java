package com.ihrs.backend.service;

import com.ihrs.backend.entity.Appointment;
import com.ihrs.backend.repository.AppointmentRepository;
import com.ihrs.backend.repository.UserAccountRepository;
import java.util.List;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AppointmentUserMigrationService {

    private final AppointmentRepository appointmentRepository;
    private final UserAccountRepository userAccountRepository;

    public AppointmentUserMigrationService(
        AppointmentRepository appointmentRepository,
        UserAccountRepository userAccountRepository
    ) {
        this.appointmentRepository = appointmentRepository;
        this.userAccountRepository = userAccountRepository;
    }

    @EventListener(ApplicationReadyEvent.class)
    @Transactional
    public void backfillAppointmentUsers() {
        List<Appointment> legacyAppointments = appointmentRepository.findByUserIsNull();
        for (Appointment appointment : legacyAppointments) {
            String patientPhone = appointment.getPatientPhone();
            if (patientPhone == null || patientPhone.isBlank()) {
                continue;
            }

            userAccountRepository.findByPhone(patientPhone.trim()).ifPresent(appointment::setUser);
        }
    }
}
