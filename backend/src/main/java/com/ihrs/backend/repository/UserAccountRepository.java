package com.ihrs.backend.repository;

import com.ihrs.backend.entity.UserAccount;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserAccountRepository extends JpaRepository<UserAccount, Long> {

    boolean existsByPhone(String phone);

    Optional<UserAccount> findByPhone(String phone);
}
