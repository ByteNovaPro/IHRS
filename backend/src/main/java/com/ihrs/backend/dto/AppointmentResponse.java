package com.ihrs.backend.dto;

import java.time.LocalDate;
import java.time.LocalDateTime;

public record AppointmentResponse(
    Long id,
    Long hospitalId,
    String hospitalName,
    Long roomId,
    String roomName,
    Long doctorId,
    String doctorName,
    String doctorTitle,
    String patientName,
    String patientPhone,
    LocalDate appointmentDate,
    String timeSlot,
    String status,
    String symptom,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {
}
