package com.ihrs.backend.dto;

import java.time.LocalDateTime;

public record ClinicRoomResponse(
    Long id,
    Long hospitalId,
    String hospitalName,
    String name,
    String floor,
    String shortIntro,
    String detailIntro,
    long doctorCount,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {
}
