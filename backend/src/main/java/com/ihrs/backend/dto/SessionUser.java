package com.ihrs.backend.dto;

public record SessionUser(
    String phone,
    String name,
    String role
) {
}
