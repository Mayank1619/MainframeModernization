package com.bankofz.inqcust.api.domain;

public record CustomerInquiryResponse(
        LegacyInquiryStatus legacyStatus,
        LookupMode lookupMode,
        CustomerResponse customer,
        RiskAssessmentResponse riskAssessment
) {
}
