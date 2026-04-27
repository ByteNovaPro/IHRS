package com.ihrs.backend.service;

import com.ihrs.backend.dto.ClinicRoomRequest;
import com.ihrs.backend.dto.ClinicRoomResponse;
import com.ihrs.backend.dto.DoctorRequest;
import com.ihrs.backend.dto.DoctorResponse;
import com.ihrs.backend.dto.HospitalRequest;
import com.ihrs.backend.dto.HospitalResponse;
import com.ihrs.backend.dto.PageResponse;
import com.ihrs.backend.entity.ClinicRoom;
import com.ihrs.backend.entity.Doctor;
import com.ihrs.backend.entity.Hospital;
import com.ihrs.backend.exception.BadRequestException;
import com.ihrs.backend.exception.ResourceNotFoundException;
import com.ihrs.backend.repository.ClinicRoomRepository;
import com.ihrs.backend.repository.DoctorRepository;
import com.ihrs.backend.repository.HospitalRepository;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
@Transactional
public class AdminCatalogService {

    private final HospitalRepository hospitalRepository;
    private final ClinicRoomRepository clinicRoomRepository;
    private final DoctorRepository doctorRepository;

    public AdminCatalogService(
        HospitalRepository hospitalRepository,
        ClinicRoomRepository clinicRoomRepository,
        DoctorRepository doctorRepository
    ) {
        this.hospitalRepository = hospitalRepository;
        this.clinicRoomRepository = clinicRoomRepository;
        this.doctorRepository = doctorRepository;
    }

    @Transactional(readOnly = true)
    public PageResponse<HospitalResponse> listHospitals(int page, int size, String keyword) {
        Pageable pageable = buildPageable(page, size);
        var hospitalPage = hospitalRepository.search(normalizeKeyword(keyword), pageable);
        return new PageResponse<>(
            hospitalPage.getContent().stream().map(this::toHospitalResponse).toList(),
            hospitalPage.getTotalElements(),
            hospitalPage.getTotalPages(),
            hospitalPage.getNumber(),
            hospitalPage.getSize()
        );
    }

    @Transactional(readOnly = true)
    public List<HospitalResponse> listHospitals() {
        return hospitalRepository.findAll(Sort.by(Sort.Direction.ASC, "id")).stream()
            .map(this::toHospitalResponse)
            .toList();
    }

    @Transactional(readOnly = true)
    public HospitalResponse getHospital(Long id) {
        return toHospitalResponse(requireHospital(id));
    }

    public HospitalResponse createHospital(HospitalRequest request) {
        Hospital hospital = new Hospital();
        applyHospital(hospital, request);
        return toHospitalResponse(hospitalRepository.save(hospital));
    }

    public HospitalResponse updateHospital(Long id, HospitalRequest request) {
        Hospital hospital = requireHospital(id);
        applyHospital(hospital, request);
        return toHospitalResponse(hospitalRepository.save(hospital));
    }

    public void deleteHospital(Long id) {
        hospitalRepository.delete(requireHospital(id));
    }

    @Transactional(readOnly = true)
    public PageResponse<ClinicRoomResponse> listRooms(Long hospitalId, int page, int size, String keyword) {
        Pageable pageable = buildPageable(page, size);
        var roomPage = clinicRoomRepository.search(hospitalId, normalizeKeyword(keyword), pageable);
        return new PageResponse<>(
            roomPage.getContent().stream().map(this::toClinicRoomResponse).toList(),
            roomPage.getTotalElements(),
            roomPage.getTotalPages(),
            roomPage.getNumber(),
            roomPage.getSize()
        );
    }

    @Transactional(readOnly = true)
    public List<ClinicRoomResponse> listRooms(Long hospitalId) {
        List<ClinicRoom> rooms = hospitalId == null
            ? clinicRoomRepository.findAll(Sort.by(Sort.Direction.ASC, "id"))
            : clinicRoomRepository.findByHospitalId(hospitalId);

        return rooms.stream()
            .map(this::toClinicRoomResponse)
            .toList();
    }

    @Transactional(readOnly = true)
    public ClinicRoomResponse getRoom(Long id) {
        return toClinicRoomResponse(requireRoom(id));
    }

    public ClinicRoomResponse createRoom(ClinicRoomRequest request) {
        ClinicRoom room = new ClinicRoom();
        applyRoom(room, request);
        return toClinicRoomResponse(clinicRoomRepository.save(room));
    }

    public ClinicRoomResponse updateRoom(Long id, ClinicRoomRequest request) {
        ClinicRoom room = requireRoom(id);
        applyRoom(room, request);
        return toClinicRoomResponse(clinicRoomRepository.save(room));
    }

    public void deleteRoom(Long id) {
        clinicRoomRepository.delete(requireRoom(id));
    }

    @Transactional(readOnly = true)
    public PageResponse<DoctorResponse> listDoctors(
        Long hospitalId,
        Long roomId,
        String workTimeSlot,
        int page,
        int size,
        String keyword
    ) {
        Pageable pageable = buildPageable(page, size);
        var doctorPage = doctorRepository.search(hospitalId, roomId, normalizeBlank(workTimeSlot), normalizeKeyword(keyword), pageable);
        return new PageResponse<>(
            doctorPage.getContent().stream().map(this::toDoctorResponse).toList(),
            doctorPage.getTotalElements(),
            doctorPage.getTotalPages(),
            doctorPage.getNumber(),
            doctorPage.getSize()
        );
    }

    @Transactional(readOnly = true)
    public List<DoctorResponse> listDoctors(Long hospitalId, Long roomId) {
        List<Doctor> doctors;
        if (roomId != null) {
            doctors = doctorRepository.findByRoomId(roomId);
        } else if (hospitalId != null) {
            doctors = doctorRepository.findByHospitalId(hospitalId);
        } else {
            doctors = doctorRepository.findAll(Sort.by(Sort.Direction.ASC, "id"));
        }

        return doctors.stream()
            .map(this::toDoctorResponse)
            .toList();
    }

    @Transactional(readOnly = true)
    public DoctorResponse getDoctor(Long id) {
        return toDoctorResponse(requireDoctor(id));
    }

    public DoctorResponse createDoctor(DoctorRequest request) {
        Doctor doctor = new Doctor();
        applyDoctor(doctor, request);
        return toDoctorResponse(doctorRepository.save(doctor));
    }

    public DoctorResponse updateDoctor(Long id, DoctorRequest request) {
        Doctor doctor = requireDoctor(id);
        applyDoctor(doctor, request);
        return toDoctorResponse(doctorRepository.save(doctor));
    }

    public void deleteDoctor(Long id) {
        doctorRepository.delete(requireDoctor(id));
    }

    private void applyHospital(Hospital hospital, HospitalRequest request) {
        hospital.setName(request.name().trim());
        hospital.setLevel(request.level().trim());
        hospital.setLocation(request.location().trim());
        hospital.setShortIntro(request.shortIntro().trim());
        hospital.setDetailIntro(request.detailIntro().trim());
    }

    private void applyRoom(ClinicRoom room, ClinicRoomRequest request) {
        Hospital hospital = requireHospital(request.hospitalId());
        room.setHospital(hospital);
        room.setName(request.name().trim());
        room.setFloor(request.floor().trim());
        room.setShortIntro(request.shortIntro().trim());
        room.setDetailIntro(request.detailIntro().trim());
    }

    private void applyDoctor(Doctor doctor, DoctorRequest request) {
        Hospital hospital = requireHospital(request.hospitalId());
        ClinicRoom room = requireRoom(request.roomId());

        if (!room.getHospital().getId().equals(hospital.getId())) {
            throw new BadRequestException("医生所属诊室与医院不匹配");
        }

        String workTimeSlot = request.workTimeSlot().trim();
        boolean hasConflict = doctor.getId() == null
            ? doctorRepository.existsByRoomIdAndWorkTimeSlot(room.getId(), workTimeSlot)
            : doctorRepository.existsByRoomIdAndWorkTimeSlotAndIdNot(room.getId(), workTimeSlot, doctor.getId());

        if (hasConflict) {
            throw new BadRequestException("同一诊室同一时间段不能安排两位医生上班");
        }

        doctor.setHospital(hospital);
        doctor.setRoom(room);
        doctor.setName(request.name().trim());
        doctor.setTitle(request.title().trim());
        doctor.setSpecialty(request.specialty().trim());
        doctor.setWorkTimeSlot(workTimeSlot);
        doctor.setShortIntro(request.shortIntro().trim());
        doctor.setDetailIntro(request.detailIntro().trim());
    }

    private Hospital requireHospital(Long id) {
        return hospitalRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("医院不存在，id=" + id));
    }

    private ClinicRoom requireRoom(Long id) {
        return clinicRoomRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("诊室不存在，id=" + id));
    }

    private Doctor requireDoctor(Long id) {
        return doctorRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("医生不存在，id=" + id));
    }

    private HospitalResponse toHospitalResponse(Hospital hospital) {
        long roomCount = clinicRoomRepository.countByHospitalId(hospital.getId());
        long doctorCount = doctorRepository.countByHospitalId(hospital.getId());

        return new HospitalResponse(
            hospital.getId(),
            hospital.getName(),
            hospital.getLevel(),
            hospital.getLocation(),
            hospital.getShortIntro(),
            hospital.getDetailIntro(),
            roomCount,
            doctorCount,
            hospital.getCreatedAt(),
            hospital.getUpdatedAt()
        );
    }

    private ClinicRoomResponse toClinicRoomResponse(ClinicRoom room) {
        long doctorCount = doctorRepository.countByRoomId(room.getId());

        return new ClinicRoomResponse(
            room.getId(),
            room.getHospital().getId(),
            room.getHospital().getName(),
            room.getName(),
            room.getFloor(),
            room.getShortIntro(),
            room.getDetailIntro(),
            doctorCount,
            room.getCreatedAt(),
            room.getUpdatedAt()
        );
    }

    private DoctorResponse toDoctorResponse(Doctor doctor) {
        return new DoctorResponse(
            doctor.getId(),
            doctor.getHospital().getId(),
            doctor.getHospital().getName(),
            doctor.getRoom().getId(),
            doctor.getRoom().getName(),
            doctor.getName(),
            doctor.getTitle(),
            doctor.getSpecialty(),
            doctor.getWorkTimeSlot(),
            doctor.getShortIntro(),
            doctor.getDetailIntro(),
            doctor.getCreatedAt(),
            doctor.getUpdatedAt()
        );
    }

    private Pageable buildPageable(int page, int size) {
        int normalizedPage = Math.max(page, 0);
        int normalizedSize = Math.min(Math.max(size, 1), 100);
        return PageRequest.of(normalizedPage, normalizedSize, Sort.by(Sort.Direction.ASC, "id"));
    }

    private String normalizeKeyword(String keyword) {
        return keyword == null ? "" : keyword.trim();
    }

    private String normalizeBlank(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }
}
