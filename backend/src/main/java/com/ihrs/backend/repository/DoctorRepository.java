package com.ihrs.backend.repository;

import com.ihrs.backend.entity.Doctor;
import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface DoctorRepository extends JpaRepository<Doctor, Long> {

    List<Doctor> findByHospitalId(Long hospitalId);

    List<Doctor> findByRoomId(Long roomId);

    long countByHospitalId(Long hospitalId);

    long countByRoomId(Long roomId);

    boolean existsByRoomIdAndWorkTimeSlot(Long roomId, String workTimeSlot);

    boolean existsByRoomIdAndWorkTimeSlotAndIdNot(Long roomId, String workTimeSlot, Long id);

    @Query("""
        select d from Doctor d
        where (:hospitalId is null or d.hospital.id = :hospitalId)
          and (:roomId is null or d.room.id = :roomId)
          and (:workTimeSlot is null or d.workTimeSlot = :workTimeSlot)
          and (
              :keyword = ''
              or lower(d.name) like lower(concat('%', :keyword, '%'))
              or lower(d.title) like lower(concat('%', :keyword, '%'))
              or lower(d.specialty) like lower(concat('%', :keyword, '%'))
              or lower(d.workTimeSlot) like lower(concat('%', :keyword, '%'))
              or lower(d.shortIntro) like lower(concat('%', :keyword, '%'))
              or lower(d.detailIntro) like lower(concat('%', :keyword, '%'))
              or lower(d.hospital.name) like lower(concat('%', :keyword, '%'))
              or lower(d.room.name) like lower(concat('%', :keyword, '%'))
          )
        """)
    Page<Doctor> search(
        @Param("hospitalId") Long hospitalId,
        @Param("roomId") Long roomId,
        @Param("workTimeSlot") String workTimeSlot,
        @Param("keyword") String keyword,
        Pageable pageable
    );
}
