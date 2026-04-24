package com.ihrs.backend.dto;

public record SessionUser(
    Long id,
    String phone,
    String name,
    String role
) {
}
