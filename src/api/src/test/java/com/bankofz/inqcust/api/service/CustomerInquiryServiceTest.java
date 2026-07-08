package com.bankofz.inqcust.api.service;

import com.bankofz.inqcust.api.domain.CustomerInquiryResponse;
import com.bankofz.inqcust.api.domain.CustomerRecord;
import com.bankofz.inqcust.api.domain.LookupMode;
import com.bankofz.inqcust.api.mapper.CustomerMapper;
import com.bankofz.inqcust.api.repository.CustomerRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

class CustomerInquiryServiceTest {

    private CustomerInquiryService service;

    @BeforeEach
    void setUp() {
        CustomerRepository repository = new InMemoryCustomerRepository(List.of(
                record("123456", "0000000001", "ACTIVE", 742, 20260115),
                record("123456", "0000000002", "ACTIVE", 650, 20250510),
                record("123456", "0000000003", "SUSPENDED", 580, 20240101),
                record("123456", "0000000005", "INACTIVE", 720, 20260201)
        ));

        LookupModeResolver lookupModeResolver = new LookupModeResolver();
        LegacyDateConverter legacyDateConverter = new LegacyDateConverter();
        CustomerMapper customerMapper = new CustomerMapper(legacyDateConverter);
        Clock clock = Clock.fixed(Instant.parse("2026-07-08T00:00:00Z"), ZoneOffset.UTC);
        RiskAssessmentService riskAssessmentService = new RiskAssessmentService(clock);
        LegacyStatusFactory legacyStatusFactory = new LegacyStatusFactory();

        service = new CustomerInquiryService(
                lookupModeResolver,
                repository,
                customerMapper,
                riskAssessmentService,
                legacyStatusFactory,
                highest -> "0000000002",
                3
        );
    }

    @Test
    void specificCustomerFound() {
        CustomerInquiryResponse response = service.inquire("123456", "0000000001");

        assertEquals(LookupMode.SPECIFIC, response.lookupMode());
        assertEquals("Y", response.legacyStatus().inquirySuccess());
        assertEquals("0", response.legacyStatus().inquiryFailCode());
        assertEquals("0000000001", response.customer().customerNumber());
        assertNotNull(response.riskAssessment());
    }

    @Test
    void specificCustomerNotFound() {
        CustomerInquiryResponse response = service.inquire("123456", "0000009999");

        assertEquals(LookupMode.SPECIFIC, response.lookupMode());
        assertEquals("N", response.legacyStatus().inquirySuccess());
        assertEquals("1", response.legacyStatus().inquiryFailCode());
        assertNull(response.customer());
        assertNull(response.riskAssessment());
    }

    @Test
    void latestCustomerFound() {
        CustomerInquiryResponse response = service.inquire("123456", "9999999999");

        assertEquals(LookupMode.LATEST, response.lookupMode());
        assertEquals("0000000005", response.customer().customerNumber());
        assertEquals("Y", response.legacyStatus().inquirySuccess());
    }

    @Test
    void latestCustomerNotFound() {
        CustomerInquiryResponse response = service.inquire("999999", "9999999999");

        assertEquals(LookupMode.LATEST, response.lookupMode());
        assertEquals("N", response.legacyStatus().inquirySuccess());
        assertEquals("9", response.legacyStatus().inquiryFailCode());
        assertNull(response.customer());
    }

    @Test
    void randomCustomerFound() {
        CustomerInquiryResponse response = service.inquire("123456", "0000000000");

        assertEquals(LookupMode.RANDOM, response.lookupMode());
        assertEquals("Y", response.legacyStatus().inquirySuccess());
        assertEquals("0000000002", response.customer().customerNumber());
    }

    @Test
    void randomCustomerRetryFailure() {
        CustomerRepository repository = new InMemoryCustomerRepository(List.of(
                record("123456", "0000000001", "ACTIVE", 742, 20260115),
                record("123456", "0000000005", "INACTIVE", 720, 20260201)
        ));

        service = new CustomerInquiryService(
                new LookupModeResolver(),
                repository,
                new CustomerMapper(new LegacyDateConverter()),
                new RiskAssessmentService(Clock.fixed(Instant.parse("2026-07-08T00:00:00Z"), ZoneOffset.UTC)),
                new LegacyStatusFactory(),
                highest -> "0000000002",
                2
        );

        CustomerInquiryResponse response = service.inquire("123456", "0000000000");

        assertEquals(LookupMode.RANDOM, response.lookupMode());
        assertEquals("N", response.legacyStatus().inquirySuccess());
        assertEquals("1", response.legacyStatus().inquiryFailCode());
        assertNull(response.customer());
    }

    @Test
    void randomLookupRespectsConfiguredRetryLimit() {
        AtomicInteger attempts = new AtomicInteger(0);
        CustomerRepository repository = new InMemoryCustomerRepository(List.of(
                record("123456", "0000000001", "ACTIVE", 742, 20260115),
                record("123456", "0000000005", "INACTIVE", 720, 20260201)
        ));

        service = new CustomerInquiryService(
                new LookupModeResolver(),
                repository,
                new CustomerMapper(new LegacyDateConverter()),
                new RiskAssessmentService(Clock.fixed(Instant.parse("2026-07-08T00:00:00Z"), ZoneOffset.UTC)),
                new LegacyStatusFactory(),
                highest -> {
                    attempts.incrementAndGet();
                    return "0000000002";
                },
                4
        );

        CustomerInquiryResponse response = service.inquire("123456", "0000000000");

        assertEquals("N", response.legacyStatus().inquirySuccess());
        assertEquals(4, attempts.get());
    }

    private static CustomerRecord record(String sortCode, String number, String status, int score, int reviewDate) {
        return new CustomerRecord(
                "CUST",
                sortCode,
                number,
                "Mr",
                "John",
                "Smith",
                19750101,
                "4165550101",
                "1 Main Street",
                "Suite 100",
                "Toronto",
                "M5H2N2",
                "Canada",
                status,
                20100615,
                score,
                reviewDate
        );
    }

    private static class InMemoryCustomerRepository implements CustomerRepository {

        private final List<CustomerRecord> customers;

        private InMemoryCustomerRepository(List<CustomerRecord> customers) {
            this.customers = customers;
        }

        @Override
        public Optional<CustomerRecord> findBySortCodeAndCustomerNumber(String sortCode, String customerNumber) {
            return customers.stream()
                    .filter(customer -> sortCode.equals(customer.sortCode()) && customerNumber.equals(customer.customerNumber()))
                    .findFirst();
        }

        @Override
        public List<CustomerRecord> findBySortCode(String sortCode) {
            return customers.stream().filter(customer -> sortCode.equals(customer.sortCode())).toList();
        }
    }
}
