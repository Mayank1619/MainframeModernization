package com.bankofz.inqcust.api.service;

import com.bankofz.inqcust.api.domain.AddressResponse;
import com.bankofz.inqcust.api.domain.CustomerResponse;
import com.bankofz.inqcust.api.domain.CustomerStatus;
import com.bankofz.inqcust.api.domain.RiskAssessmentResponse;
import com.bankofz.inqcust.api.domain.RiskRating;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RiskAssessmentServiceTest {

    private final Clock fixedClock = Clock.fixed(Instant.parse("2026-07-08T00:00:00Z"), ZoneOffset.UTC);
    private final RiskAssessmentService service = new RiskAssessmentService(fixedClock);

    @Test
    void returnsLowRisk() {
        RiskAssessmentResponse response = service.assess(customer(CustomerStatus.ACTIVE, 742, LocalDate.of(2026, 1, 15)));
        assertEquals(RiskRating.LOW, response.riskRating());
    }

    @Test
    void returnsMediumRisk() {
        RiskAssessmentResponse response = service.assess(customer(CustomerStatus.ACTIVE, 650, LocalDate.of(2026, 1, 15)));
        assertEquals(RiskRating.MEDIUM, response.riskRating());
    }

    @Test
    void returnsHighRiskByStatus() {
        RiskAssessmentResponse response = service.assess(customer(CustomerStatus.SUSPENDED, 742, LocalDate.of(2026, 1, 15)));
        assertEquals(RiskRating.HIGH, response.riskRating());
    }

    @Test
    void returnsHighRiskByScore() {
        RiskAssessmentResponse response = service.assess(customer(CustomerStatus.ACTIVE, 580, LocalDate.of(2026, 1, 15)));
        assertEquals(RiskRating.HIGH, response.riskRating());
    }

    @Test
    void marksReviewRequiredWhenStale() {
        RiskAssessmentResponse response = service.assess(customer(CustomerStatus.ACTIVE, 742, LocalDate.of(2024, 1, 1)));
        assertTrue(response.reviewRequired());
        assertTrue(response.reasons().contains("STALE_CREDIT_REVIEW"));
    }

    private CustomerResponse customer(CustomerStatus status, int score, LocalDate reviewDate) {
        return new CustomerResponse(
                "CUST",
                "123456",
                "0000000001",
                "Mr",
                "John",
                "Smith",
                LocalDate.of(1975, 1, 1),
                "4165550101",
                new AddressResponse("line1", "line2", "city", "postcode", "country"),
                status,
                LocalDate.of(2010, 6, 15),
                score,
                reviewDate
        );
    }
}
