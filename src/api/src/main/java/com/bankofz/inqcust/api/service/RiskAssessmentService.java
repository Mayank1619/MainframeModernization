package com.bankofz.inqcust.api.service;

import com.bankofz.inqcust.api.domain.CustomerResponse;
import com.bankofz.inqcust.api.domain.CustomerStatus;
import com.bankofz.inqcust.api.domain.RiskAssessmentResponse;
import com.bankofz.inqcust.api.domain.RiskRating;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Service
public class RiskAssessmentService {

    private final Clock clock;

    public RiskAssessmentService(Clock clock) {
        this.clock = clock;
    }

    public RiskAssessmentResponse assess(CustomerResponse customer) {
        List<String> reasons = new ArrayList<>();

        boolean reviewRequired = isReviewRequired(customer.creditScoreReviewDate());
        if (reviewRequired) {
            reasons.add("STALE_CREDIT_REVIEW");
        }

        if (customer.status() == CustomerStatus.SUSPENDED) {
            reasons.add("STATUS_SUSPENDED");
            return new RiskAssessmentResponse(RiskRating.HIGH, reviewRequired, reasons);
        }

        if (customer.creditScore() != null && customer.creditScore() < 600) {
            reasons.add("CREDIT_SCORE_LT_600");
            return new RiskAssessmentResponse(RiskRating.HIGH, reviewRequired, reasons);
        }

        if (customer.creditScore() != null && customer.creditScore() >= 600 && customer.creditScore() <= 699) {
            reasons.add("CREDIT_SCORE_600_TO_699");
            return new RiskAssessmentResponse(RiskRating.MEDIUM, reviewRequired, reasons);
        }

        if (customer.status() == CustomerStatus.ACTIVE
                && customer.creditScore() != null
                && customer.creditScore() >= 700
                && !reviewRequired) {
            reasons.add("ACTIVE_SCORE_GE_700_REVIEW_CURRENT");
            return new RiskAssessmentResponse(RiskRating.LOW, false, reasons);
        }

        reasons.add("DEFAULT_MEDIUM");
        return new RiskAssessmentResponse(RiskRating.MEDIUM, reviewRequired, reasons);
    }

    private boolean isReviewRequired(LocalDate creditScoreReviewDate) {
        if (creditScoreReviewDate == null) {
            return true;
        }
        LocalDate staleBoundary = LocalDate.now(clock).minusMonths(12);
        return creditScoreReviewDate.isBefore(staleBoundary);
    }
}
