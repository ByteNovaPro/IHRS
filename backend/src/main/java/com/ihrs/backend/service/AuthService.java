package com.ihrs.backend.service;

import com.ihrs.backend.dto.AuthRequest;
import com.ihrs.backend.dto.AuthResponse;
import com.ihrs.backend.dto.RegisterRequest;
import com.ihrs.backend.dto.SessionUser;
import com.ihrs.backend.entity.UserAccount;
import com.ihrs.backend.exception.BadRequestException;
import com.ihrs.backend.repository.UserAccountRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.util.HexFormat;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {

    public static final String ROLE_ADMIN = "ADMIN";
    public static final String ROLE_USER = "USER";

    private static final String SESSION_PREFIX = "ihrs:session:";
    private static final Duration SESSION_TTL = Duration.ofHours(12);

    private final UserAccountRepository userAccountRepository;
    private final StringRedisTemplate redisTemplate;
    private final String adminPhone;
    private final String adminPasswordHash;

    public AuthService(
        UserAccountRepository userAccountRepository,
        StringRedisTemplate redisTemplate,
        @Value("${app.admin.phone:13800000000}") String adminPhone,
        @Value("${app.admin.password:admin123456}") String adminPassword
    ) {
        this.userAccountRepository = userAccountRepository;
        this.redisTemplate = redisTemplate;
        this.adminPhone = adminPhone;
        this.adminPasswordHash = hashPassword(adminPassword);
    }

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        String phone = request.phone().trim();

        if (phone.equals(adminPhone)) {
            throw new BadRequestException("该手机号为系统管理员账号，不能注册普通用户");
        }

        if (userAccountRepository.existsByPhone(phone)) {
            throw new BadRequestException("该手机号已注册");
        }

        UserAccount user = new UserAccount();
        user.setPhone(phone);
        user.setPasswordHash(hashPassword(request.password()));
        user.setName(request.name().trim());
        user.setRole(ROLE_USER);
        userAccountRepository.save(user);

        return createSession(new SessionUser(user.getPhone(), user.getName(), user.getRole()));
    }

    @Transactional(readOnly = true)
    public AuthResponse login(AuthRequest request) {
        String phone = request.phone().trim();
        String passwordHash = hashPassword(request.password());

        if (phone.equals(adminPhone)) {
            if (!adminPasswordHash.equals(passwordHash)) {
                throw new BadRequestException("手机号或密码错误");
            }

            return createSession(new SessionUser(adminPhone, "系统管理员", ROLE_ADMIN));
        }

        UserAccount user = userAccountRepository.findByPhone(phone)
            .orElseThrow(() -> new BadRequestException("手机号或密码错误"));

        if (!user.getPasswordHash().equals(passwordHash)) {
            throw new BadRequestException("手机号或密码错误");
        }

        return createSession(new SessionUser(user.getPhone(), user.getName(), user.getRole()));
    }

    public SessionUser getSessionUser(String token) {
        if (token == null || token.isBlank()) {
            return null;
        }

        String value = redisTemplate.opsForValue().get(SESSION_PREFIX + token.trim());
        if (value == null || value.isBlank()) {
            return null;
        }

        String[] parts = value.split("\\|", 3);
        if (parts.length != 3) {
            return null;
        }

        redisTemplate.expire(SESSION_PREFIX + token.trim(), SESSION_TTL);
        return new SessionUser(parts[0], parts[1], parts[2]);
    }

    public void logout(String token) {
        if (token != null && !token.isBlank()) {
            redisTemplate.delete(SESSION_PREFIX + token.trim());
        }
    }

    private AuthResponse createSession(SessionUser user) {
        String token = UUID.randomUUID().toString().replace("-", "");
        redisTemplate.opsForValue().set(
            SESSION_PREFIX + token,
            String.join("|", user.phone(), user.name(), user.role()),
            SESSION_TTL
        );
        return new AuthResponse(token, user.phone(), user.name(), user.role());
    }

    private String hashPassword(String password) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(password.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }
}
