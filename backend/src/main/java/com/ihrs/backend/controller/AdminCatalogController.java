package com.ihrs.backend.controller;

import com.ihrs.backend.dto.ClinicRoomRequest;
import com.ihrs.backend.dto.ClinicRoomResponse;
import com.ihrs.backend.dto.DoctorRequest;
import com.ihrs.backend.dto.DoctorResponse;
import com.ihrs.backend.dto.HospitalRequest;
import com.ihrs.backend.dto.HospitalResponse;
import com.ihrs.backend.dto.PageResponse;
import com.ihrs.backend.service.AdminCatalogService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin")
public class AdminCatalogController {

    private final AdminCatalogService adminCatalogService;

    public AdminCatalogController(AdminCatalogService adminCatalogService) {
        this.adminCatalogService = adminCatalogService;
    }

    @GetMapping("/hospitals")
    public PageResponse<HospitalResponse> listHospitals(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "12") int size,
        @RequestParam(defaultValue = "") String keyword
    ) {
        return adminCatalogService.listHospitals(page, size, keyword);
    }

    @GetMapping("/hospitals/{id}")
    public HospitalResponse getHospital(@PathVariable Long id) {
        return adminCatalogService.getHospital(id);
    }

    @PostMapping("/hospitals")
    @ResponseStatus(HttpStatus.CREATED)
    public HospitalResponse createHospital(@Valid @RequestBody HospitalRequest request) {
        return adminCatalogService.createHospital(request);
    }

    @PutMapping("/hospitals/{id}")
    public HospitalResponse updateHospital(@PathVariable Long id, @Valid @RequestBody HospitalRequest request) {
        return adminCatalogService.updateHospital(id, request);
    }

    @DeleteMapping("/hospitals/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteHospital(@PathVariable Long id) {
        adminCatalogService.deleteHospital(id);
    }

    @GetMapping("/rooms")
    public PageResponse<ClinicRoomResponse> listRooms(
        @RequestParam(required = false) Long hospitalId,
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "12") int size,
        @RequestParam(defaultValue = "") String keyword
    ) {
        return adminCatalogService.listRooms(hospitalId, page, size, keyword);
    }

    @GetMapping("/rooms/{id}")
    public ClinicRoomResponse getRoom(@PathVariable Long id) {
        return adminCatalogService.getRoom(id);
    }

    @PostMapping("/rooms")
    @ResponseStatus(HttpStatus.CREATED)
    public ClinicRoomResponse createRoom(@Valid @RequestBody ClinicRoomRequest request) {
        return adminCatalogService.createRoom(request);
    }

    @PutMapping("/rooms/{id}")
    public ClinicRoomResponse updateRoom(@PathVariable Long id, @Valid @RequestBody ClinicRoomRequest request) {
        return adminCatalogService.updateRoom(id, request);
    }

    @DeleteMapping("/rooms/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteRoom(@PathVariable Long id) {
        adminCatalogService.deleteRoom(id);
    }

    @GetMapping("/doctors")
    public PageResponse<DoctorResponse> listDoctors(
        @RequestParam(required = false) Long hospitalId,
        @RequestParam(required = false) Long roomId,
        @RequestParam(required = false) String workTimeSlot,
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "12") int size,
        @RequestParam(defaultValue = "") String keyword
    ) {
        return adminCatalogService.listDoctors(hospitalId, roomId, workTimeSlot, page, size, keyword);
    }

    @GetMapping("/doctors/{id}")
    public DoctorResponse getDoctor(@PathVariable Long id) {
        return adminCatalogService.getDoctor(id);
    }

    @PostMapping("/doctors")
    @ResponseStatus(HttpStatus.CREATED)
    public DoctorResponse createDoctor(@Valid @RequestBody DoctorRequest request) {
        return adminCatalogService.createDoctor(request);
    }

    @PutMapping("/doctors/{id}")
    public DoctorResponse updateDoctor(@PathVariable Long id, @Valid @RequestBody DoctorRequest request) {
        return adminCatalogService.updateDoctor(id, request);
    }

    @DeleteMapping("/doctors/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteDoctor(@PathVariable Long id) {
        adminCatalogService.deleteDoctor(id);
    }
}
