package com.ihrs.backend.dto;

import java.time.LocalDate;

public record AppointmentQuotaResponse(
    Long doctorId,
    LocalDate appointmentDate,
    String timeSlot,
    long reservedCount,
    long remainingCount,
    long capacity
) {
}
