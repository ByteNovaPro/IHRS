package com.ihrs.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record DoctorRequest(
    @NotNull Long hospitalId,
    @NotNull Long roomId,
    @NotBlank @Size(max = 50) String name,
    @NotBlank @Size(max = 50) String title,
    @NotBlank @Size(max = 100) String specialty,
    @NotBlank @Size(max = 255) String shortIntro,
    @NotBlank @Size(max = 2000) String detailIntro
) {
}
