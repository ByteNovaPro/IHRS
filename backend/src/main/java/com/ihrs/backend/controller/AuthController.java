package com.ihrs.backend.controller;

import com.ihrs.backend.dto.AuthRequest;
import com.ihrs.backend.dto.AuthResponse;
import com.ihrs.backend.dto.RegisterRequest;
import com.ihrs.backend.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/api/auth/register")
    @ResponseStatus(HttpStatus.CREATED)
    public AuthResponse register(@Valid @RequestBody RegisterRequest request) {
        return authService.register(request);
    }

    @PostMapping("/api/auth/login")
    public AuthResponse login(@Valid @RequestBody AuthRequest request) {
        return authService.login(request);
    }

    @PostMapping("/api/auth/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void logout(HttpServletRequest request) {
        authService.logout(resolveToken(request));
    }

    @GetMapping("/api/auth/me")
    public AuthResponse me(HttpServletRequest request) {
        var user = authService.getSessionUser(resolveToken(request));
        if (user == null) {
            return null;
        }
        return new AuthResponse(resolveToken(request), user.phone(), user.name(), user.role());
    }

    private String resolveToken(HttpServletRequest request) {
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            return header.substring(7);
        }
        return request.getHeader("X-Auth-Token");
    }
}
