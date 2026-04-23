package com.ihrs.backend.controller;

import com.ihrs.backend.dto.ClinicRoomResponse;
import com.ihrs.backend.dto.DoctorResponse;
import com.ihrs.backend.dto.HospitalResponse;
import com.ihrs.backend.service.AdminCatalogService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/catalog")
public class CatalogController {

    private final AdminCatalogService adminCatalogService;

    public CatalogController(AdminCatalogService adminCatalogService) {
        this.adminCatalogService = adminCatalogService;
    }

    @GetMapping("/hospitals")
    public List<HospitalResponse> listHospitals() {
        return adminCatalogService.listHospitals();
    }

    @GetMapping("/rooms")
    public List<ClinicRoomResponse> listRooms(@RequestParam(required = false) Long hospitalId) {
        return adminCatalogService.listRooms(hospitalId);
    }

    @GetMapping("/doctors")
    public List<DoctorResponse> listDoctors(
        @RequestParam(required = false) Long hospitalId,
        @RequestParam(required = false) Long roomId
    ) {
        return adminCatalogService.listDoctors(hospitalId, roomId);
    }
}
