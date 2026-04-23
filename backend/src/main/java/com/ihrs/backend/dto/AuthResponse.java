package com.ihrs.backend.dto;

public record AuthResponse(
    String token,
    String phone,
    String name,
    String role
) {
}
