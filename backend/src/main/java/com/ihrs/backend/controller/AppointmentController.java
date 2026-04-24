package com.ihrs.backend.controller;

import com.ihrs.backend.dto.AppointmentRequest;
import com.ihrs.backend.dto.AppointmentQuotaCalendarResponse;
import com.ihrs.backend.dto.AppointmentQuotaResponse;
import com.ihrs.backend.dto.AppointmentResponse;
import com.ihrs.backend.service.AppointmentService;
import jakarta.validation.Valid;
import java.time.LocalDate;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AppointmentController {

    private final AppointmentService appointmentService;

    public AppointmentController(AppointmentService appointmentService) {
        this.appointmentService = appointmentService;
    }

    @PostMapping("/api/appointments")
    @ResponseStatus(HttpStatus.CREATED)
    public AppointmentResponse createAppointment(@Valid @RequestBody AppointmentRequest request) {
        return appointmentService.createAppointment(request);
    }

    @GetMapping("/api/appointments")
    public List<AppointmentResponse> listMyAppointments(@RequestParam(required = false) String patientPhone) {
        return appointmentService.listAppointmentsByPhone(patientPhone);
    }

    @PutMapping("/api/appointments/{id}/cancel")
    public AppointmentResponse cancelAppointment(@PathVariable Long id) {
        return appointmentService.cancelAppointment(id);
    }

    @GetMapping("/api/appointments/quota")
    public AppointmentQuotaResponse getAppointmentQuota(
        @RequestParam Long doctorId,
        @RequestParam LocalDate appointmentDate,
        @RequestParam String timeSlot
    ) {
        return appointmentService.getQuota(doctorId, appointmentDate, timeSlot);
    }

    @GetMapping("/api/appointments/quota-calendar")
    public AppointmentQuotaCalendarResponse getAppointmentQuotaCalendar(
        @RequestParam List<Long> doctorIds,
        @RequestParam LocalDate startDate,
        @RequestParam LocalDate endDate
    ) {
        return appointmentService.getQuotaCalendar(doctorIds, startDate, endDate);
    }

    @GetMapping("/api/admin/appointments")
    public List<AppointmentResponse> listAppointments() {
        return appointmentService.listAppointments();
    }

    @PutMapping("/api/admin/appointments/{id}/cancel")
    public AppointmentResponse cancelAdminAppointment(@PathVariable Long id) {
        return appointmentService.cancelAppointment(id);
    }

    @DeleteMapping("/api/admin/appointments/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteAppointment(@PathVariable Long id) {
        appointmentService.deleteAppointment(id);
    }
}
