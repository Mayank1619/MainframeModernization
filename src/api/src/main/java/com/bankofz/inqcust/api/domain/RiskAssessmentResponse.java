package com.bankofz.inqcust.api.domain;

import java.util.List;

public record RiskAssessmentResponse(
        RiskRating riskRating,
        boolean reviewRequired,
        List<String> reasons
) {
}
