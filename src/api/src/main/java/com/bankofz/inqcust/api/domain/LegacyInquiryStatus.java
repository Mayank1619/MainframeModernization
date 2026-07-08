package com.bankofz.inqcust.api.domain;

public record LegacyInquiryStatus(
        String inquirySuccess,
        String inquiryFailCode,
        String message
) {
}
