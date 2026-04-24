package com.ihrs.backend.security;

import com.ihrs.backend.dto.SessionUser;
import com.ihrs.backend.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class AuthInterceptor implements HandlerInterceptor {

    private final AuthService authService;

    public AuthInterceptor(AuthService authService) {
        this.authService = authService;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String path = request.getRequestURI();

        if (path.startsWith("/api/auth/") || path.startsWith("/api/catalog/") || path.equals("/api/health")) {
            return true;
        }

        if (path.equals("/api/appointments/quota") || path.equals("/api/appointments/quota-calendar")) {
            return requireLogin(request, response, false);
        }

        if (path.startsWith("/api/admin/")) {
            return requireLogin(request, response, true);
        }

        if (path.startsWith("/api/appointments")) {
            return requireLogin(request, response, false);
        }

        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        AuthContext.clear();
    }

    private boolean requireLogin(HttpServletRequest request, HttpServletResponse response, boolean adminRequired) throws Exception {
        SessionUser user = authService.getSessionUser(resolveToken(request));
        if (user == null) {
            writeError(response, HttpServletResponse.SC_UNAUTHORIZED, "请先登录");
            return false;
        }

        if (adminRequired && !AuthService.ROLE_ADMIN.equals(user.role())) {
            writeError(response, HttpServletResponse.SC_FORBIDDEN, "只有管理员可以访问后台管理功能");
            return false;
        }

        AuthContext.set(user);
        return true;
    }

    private String resolveToken(HttpServletRequest request) {
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            return header.substring(7);
        }
        return request.getHeader("X-Auth-Token");
    }

    private void writeError(HttpServletResponse response, int status, String message) throws Exception {
        response.setStatus(status);
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"status\":" + status + ",\"message\":\"" + message + "\"}");
    }
}
