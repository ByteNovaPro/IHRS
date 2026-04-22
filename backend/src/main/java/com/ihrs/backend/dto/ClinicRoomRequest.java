package com.ihrs.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record ClinicRoomRequest(
    @NotNull Long hospitalId,
    @NotBlank @Size(max = 100) String name,
    @NotBlank @Size(max = 50) String floor,
    @NotBlank @Size(max = 255) String shortIntro,
    @NotBlank @Size(max = 2000) String detailIntro
) {
}
