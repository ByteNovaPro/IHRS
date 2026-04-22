package com.ihrs.backend.repository;

import com.ihrs.backend.entity.ClinicRoom;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ClinicRoomRepository extends JpaRepository<ClinicRoom, Long> {

    List<ClinicRoom> findByHospitalId(Long hospitalId);
}
