package com.bankofz.inqcust.api.service;

import com.bankofz.inqcust.api.domain.CustomerInquiryResponse;
import com.bankofz.inqcust.api.domain.CustomerRecord;
import com.bankofz.inqcust.api.domain.CustomerResponse;
import com.bankofz.inqcust.api.domain.LegacyInquiryStatus;
import com.bankofz.inqcust.api.domain.LookupMode;
import com.bankofz.inqcust.api.mapper.CustomerMapper;
import com.bankofz.inqcust.api.repository.CustomerRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
public class CustomerInquiryService {

    private final LookupModeResolver lookupModeResolver;
    private final CustomerRepository customerRepository;
    private final CustomerMapper customerMapper;
    private final RiskAssessmentService riskAssessmentService;
    private final LegacyStatusFactory legacyStatusFactory;
    private final RandomCustomerNumberGenerator randomCustomerNumberGenerator;
    private final int randomRetryLimit;

    public CustomerInquiryService(
            LookupModeResolver lookupModeResolver,
            CustomerRepository customerRepository,
            CustomerMapper customerMapper,
            RiskAssessmentService riskAssessmentService,
            LegacyStatusFactory legacyStatusFactory,
            RandomCustomerNumberGenerator randomCustomerNumberGenerator,
            @Value("${app.lookup.random-retry-limit:1000}") int randomRetryLimit
    ) {
        this.lookupModeResolver = lookupModeResolver;
        this.customerRepository = customerRepository;
        this.customerMapper = customerMapper;
        this.riskAssessmentService = riskAssessmentService;
        this.legacyStatusFactory = legacyStatusFactory;
        this.randomCustomerNumberGenerator = randomCustomerNumberGenerator;
        this.randomRetryLimit = randomRetryLimit;
    }

    public CustomerInquiryResponse inquire(String sortCode, String customerNumber) {
        LookupMode lookupMode = lookupModeResolver.resolve(customerNumber);
        return switch (lookupMode) {
            case SPECIFIC -> specificLookup(sortCode, customerNumber);
            case LATEST -> latestLookup(sortCode);
            case RANDOM -> randomLookup(sortCode);
        };
    }

    private CustomerInquiryResponse specificLookup(String sortCode, String customerNumber) {
        return buildResponse(
                LookupMode.SPECIFIC,
                customerRepository.findBySortCodeAndCustomerNumber(sortCode, customerNumber),
                legacyStatusFactory.specificNotFound()
        );
    }

    private CustomerInquiryResponse latestLookup(String sortCode) {
        return buildResponse(
                LookupMode.LATEST,
                customerRepository.findLatestBySortCode(sortCode),
                legacyStatusFactory.latestNotFound()
        );
    }

    private CustomerInquiryResponse randomLookup(String sortCode) {
        Optional<CustomerRecord> latestCustomer = customerRepository.findLatestBySortCode(sortCode);
        if (latestCustomer.isEmpty()) {
            return new CustomerInquiryResponse(
                    legacyStatusFactory.randomNotFound(),
                    LookupMode.RANDOM,
                    null,
                    null
            );
        }

        long highestCustomerNumber = Long.parseLong(latestCustomer.get().customerNumber());
        for (int attempt = 0; attempt < randomRetryLimit; attempt++) {
            String generatedCustomerNumber = randomCustomerNumberGenerator.nextCustomerNumber(highestCustomerNumber);
            Optional<CustomerRecord> found = customerRepository.findBySortCodeAndCustomerNumber(sortCode, generatedCustomerNumber);
            if (found.isPresent()) {
                return toSuccessResponse(LookupMode.RANDOM, found.get());
            }
        }

        return new CustomerInquiryResponse(
                legacyStatusFactory.randomNotFound(),
                LookupMode.RANDOM,
                null,
                null
        );
    }

    private CustomerInquiryResponse buildResponse(
            LookupMode lookupMode,
            Optional<CustomerRecord> customerRecord,
            LegacyInquiryStatus notFoundStatus
    ) {
        if (customerRecord.isPresent()) {
            return toSuccessResponse(lookupMode, customerRecord.get());
        }

        return new CustomerInquiryResponse(notFoundStatus, lookupMode, null, null);
    }

    private CustomerInquiryResponse toSuccessResponse(LookupMode lookupMode, CustomerRecord customerRecord) {
        CustomerResponse customerResponse = customerMapper.map(customerRecord);
        return new CustomerInquiryResponse(
                legacyStatusFactory.success(),
                lookupMode,
                customerResponse,
                riskAssessmentService.assess(customerResponse)
        );
    }
}
