package com.ihrs.backend.repository;

import com.ihrs.backend.entity.ClinicRoom;
import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ClinicRoomRepository extends JpaRepository<ClinicRoom, Long> {

    List<ClinicRoom> findByHospitalId(Long hospitalId);

    long countByHospitalId(Long hospitalId);

    @Query("""
        select r from ClinicRoom r
        where (:hospitalId is null or r.hospital.id = :hospitalId)
          and (
              :keyword = ''
              or lower(r.name) like lower(concat('%', :keyword, '%'))
              or lower(r.floor) like lower(concat('%', :keyword, '%'))
              or lower(r.shortIntro) like lower(concat('%', :keyword, '%'))
              or lower(r.detailIntro) like lower(concat('%', :keyword, '%'))
              or lower(r.hospital.name) like lower(concat('%', :keyword, '%'))
          )
        """)
    Page<ClinicRoom> search(
        @Param("hospitalId") Long hospitalId,
        @Param("keyword") String keyword,
        Pageable pageable
    );
}
