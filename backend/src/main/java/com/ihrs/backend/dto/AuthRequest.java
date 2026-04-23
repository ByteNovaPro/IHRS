package com.ihrs.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record AuthRequest(
    @NotBlank @Pattern(regexp = "^1[3-9]\\d{9}$", message = "请输入 11 位手机号") String phone,
    @NotBlank @Size(min = 6, max = 32, message = "密码长度需为 6-32 位") String password
) {
}
