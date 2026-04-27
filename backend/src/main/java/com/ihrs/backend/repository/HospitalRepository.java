package com.ihrs.backend.repository;

import com.ihrs.backend.entity.Hospital;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface HospitalRepository extends JpaRepository<Hospital, Long> {

    @Query("""
        select h from Hospital h
        where :keyword = ''
           or lower(h.name) like lower(concat('%', :keyword, '%'))
           or lower(h.level) like lower(concat('%', :keyword, '%'))
           or lower(h.location) like lower(concat('%', :keyword, '%'))
           or lower(h.shortIntro) like lower(concat('%', :keyword, '%'))
           or lower(h.detailIntro) like lower(concat('%', :keyword, '%'))
        """)
    Page<Hospital> search(@Param("keyword") String keyword, Pageable pageable);
}
