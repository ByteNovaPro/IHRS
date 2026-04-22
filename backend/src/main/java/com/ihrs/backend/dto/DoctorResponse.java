package com.ihrs.backend.dto;

import java.time.LocalDateTime;

public record DoctorResponse(
    Long id,
    Long hospitalId,
    String hospitalName,
    Long roomId,
    String roomName,
    String name,
    String title,
    String specialty,
    String shortIntro,
    String detailIntro,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {
}
