package com.ihrs.backend.dto;

import java.time.LocalDate;
import java.util.List;

public record AppointmentQuotaCalendarResponse(
    LocalDate startDate,
    LocalDate endDate,
    List<AppointmentQuotaResponse> quotas
) {
}
