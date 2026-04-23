package com.ihrs.backend.security;

import com.ihrs.backend.dto.SessionUser;

public final class AuthContext {

    private static final ThreadLocal<SessionUser> CURRENT_USER = new ThreadLocal<>();

    private AuthContext() {
    }

    public static void set(SessionUser user) {
        CURRENT_USER.set(user);
    }

    public static SessionUser get() {
        return CURRENT_USER.get();
    }

    public static void clear() {
        CURRENT_USER.remove();
    }
}
