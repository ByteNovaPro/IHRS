package com.ihrs.backend.dto;

import jakarta.validation.constraints.FutureOrPresent;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.LocalDate;

public record AppointmentRequest(
    @NotNull Long hospitalId,
    @NotNull Long roomId,
    @NotNull Long doctorId,
    @NotBlank @Size(max = 50) String patientName,
    @NotBlank @Size(max = 30) @Pattern(regexp = "^[0-9+\\-\\s]{6,30}$", message = "联系电话格式不正确") String patientPhone,
    @NotNull @FutureOrPresent LocalDate appointmentDate,
    @NotBlank @Size(max = 50) String timeSlot,
    @Size(max = 500) String symptom
) {
}
