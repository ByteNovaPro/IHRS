package com.ihrs.backend.dto;

public record AuthResponse(
    String token,
    Long id,
    String phone,
    String name,
    String role
) {
}
