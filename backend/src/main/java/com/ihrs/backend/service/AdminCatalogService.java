package com.ihrs.backend.service;

import com.ihrs.backend.dto.ClinicRoomRequest;
import com.ihrs.backend.dto.ClinicRoomResponse;
import com.ihrs.backend.dto.DoctorRequest;
import com.ihrs.backend.dto.DoctorResponse;
import com.ihrs.backend.dto.HospitalRequest;
import com.ihrs.backend.dto.HospitalResponse;
import com.ihrs.backend.entity.ClinicRoom;
import com.ihrs.backend.entity.Doctor;
import com.ihrs.backend.entity.Hospital;
import com.ihrs.backend.exception.BadRequestException;
import com.ihrs.backend.exception.ResourceNotFoundException;
import com.ihrs.backend.repository.ClinicRoomRepository;
import com.ihrs.backend.repository.DoctorRepository;
import com.ihrs.backend.repository.HospitalRepository;
import java.util.Comparator;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

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
    public List<HospitalResponse> listHospitals() {
        return hospitalRepository.findAll().stream()
            .sorted(Comparator.comparing(Hospital::getId))
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
    public List<ClinicRoomResponse> listRooms(Long hospitalId) {
        List<ClinicRoom> rooms = hospitalId == null
            ? clinicRoomRepository.findAll()
            : clinicRoomRepository.findByHospitalId(hospitalId);

        return rooms.stream()
            .sorted(Comparator.comparing(ClinicRoom::getId))
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
    public List<DoctorResponse> listDoctors(Long hospitalId, Long roomId) {
        List<Doctor> doctors;
        if (roomId != null) {
            doctors = doctorRepository.findByRoomId(roomId);
        } else if (hospitalId != null) {
            doctors = doctorRepository.findByHospitalId(hospitalId);
        } else {
            doctors = doctorRepository.findAll();
        }

        return doctors.stream()
            .sorted(Comparator.comparing(Doctor::getId))
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

        doctor.setHospital(hospital);
        doctor.setRoom(room);
        doctor.setName(request.name().trim());
        doctor.setTitle(request.title().trim());
        doctor.setSpecialty(request.specialty().trim());
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
        long roomCount = clinicRoomRepository.findByHospitalId(hospital.getId()).size();
        long doctorCount = doctorRepository.findByHospitalId(hospital.getId()).size();

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
        long doctorCount = doctorRepository.findByRoomId(room.getId()).size();

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
            doctor.getShortIntro(),
            doctor.getDetailIntro(),
            doctor.getCreatedAt(),
            doctor.getUpdatedAt()
        );
    }
}
