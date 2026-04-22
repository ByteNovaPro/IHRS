package com.ihrs.backend.dto;

import java.time.LocalDateTime;

public record HospitalResponse(
    Long id,
    String name,
    String level,
    String location,
    String shortIntro,
    String detailIntro,
    long roomCount,
    long doctorCount,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {
}
