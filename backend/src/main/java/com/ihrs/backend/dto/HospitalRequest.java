package com.ihrs.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record HospitalRequest(
    @NotBlank @Size(max = 100) String name,
    @NotBlank @Size(max = 50) String level,
    @NotBlank @Size(max = 100) String location,
    @NotBlank @Size(max = 255) String shortIntro,
    @NotBlank @Size(max = 2000) String detailIntro
) {
}
