package com.bankofz.inqcust.api.domain;

public record CustomerRecord(
        String eyecatcher,
        String sortCode,
        String customerNumber,
        String title,
        String firstName,
        String lastName,
        Integer dateOfBirth,
        String phone,
        String addressLine1,
        String addressLine2,
        String city,
        String postcode,
        String country,
        String status,
        Integer createdDate,
        Integer creditScore,
        Integer creditScoreReviewDate
) {
}
