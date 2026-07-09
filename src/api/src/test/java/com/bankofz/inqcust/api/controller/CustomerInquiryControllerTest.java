package com.bankofz.inqcust.api.controller;

import com.bankofz.inqcust.api.domain.AddressResponse;
import com.bankofz.inqcust.api.domain.CustomerInquiryResponse;
import com.bankofz.inqcust.api.domain.CustomerResponse;
import com.bankofz.inqcust.api.domain.CustomerStatus;
import com.bankofz.inqcust.api.domain.LegacyInquiryStatus;
import com.bankofz.inqcust.api.domain.LookupMode;
import com.bankofz.inqcust.api.domain.RiskAssessmentResponse;
import com.bankofz.inqcust.api.domain.RiskRating;
import com.bankofz.inqcust.api.service.CustomerInquiryService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDate;
import java.util.List;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = CustomerInquiryController.class)
class CustomerInquiryControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private CustomerInquiryService customerInquiryService;

    @Test
    void validRequestReturnsHttp200() throws Exception {
        when(customerInquiryService.inquire("123456", "0000000001"))
                .thenReturn(successResponse("0000000001", LookupMode.SPECIFIC));

        mockMvc.perform(get("/api/v1/customers/123456/0000000001").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.legacyStatus.inquirySuccess").value("Y"));
    }

    @Test
    void invalidSortCodeReturnsHttp400() throws Exception {
        mockMvc.perform(get("/api/v1/customers/ABCDEF/0000000001").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("VALIDATION_ERROR"));
    }

    @Test
    void invalidCustomerNumberReturnsHttp400() throws Exception {
        mockMvc.perform(get("/api/v1/customers/123456/ABC").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("VALIDATION_ERROR"));
    }

    @Test
    void notFoundReturnsHttp404() throws Exception {
        when(customerInquiryService.inquire("123456", "0000009999"))
                .thenReturn(notFoundResponse(LookupMode.SPECIFIC, "1"));

        mockMvc.perform(get("/api/v1/customers/123456/0000009999").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.legacyStatus.inquiryFailCode").value("1"));
    }

    @Test
    void latestRequestReturnsHttp200() throws Exception {
        when(customerInquiryService.inquire("123456", "9999999999"))
                .thenReturn(successResponse("0000000005", LookupMode.LATEST));

        mockMvc.perform(get("/api/v1/customers/123456/9999999999").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lookupMode").value("LATEST"))
                .andExpect(jsonPath("$.customer.customerNumber").value("0000000005"));
    }

    @Test
    void randomRequestReturns200WhenServiceFindsCustomer() throws Exception {
        when(customerInquiryService.inquire(anyString(), anyString()))
                .thenReturn(successResponse("0000000002", LookupMode.RANDOM));

        mockMvc.perform(get("/api/v1/customers/123456/0000000000").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lookupMode").value("RANDOM"));
    }

    @Test
    void randomRequestReturns404WhenServiceCannotFindCustomer() throws Exception {
        when(customerInquiryService.inquire("123456", "0000000000"))
                .thenReturn(notFoundResponse(LookupMode.RANDOM, "1"));

        mockMvc.perform(get("/api/v1/customers/123456/0000000000").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.lookupMode").value("RANDOM"))
                .andExpect(jsonPath("$.legacyStatus.inquiryFailCode").value("1"));
    }

    @Test
    void suspendedCustomerReturnsHighRiskInApiResponse() throws Exception {
        when(customerInquiryService.inquire("123456", "0000000003"))
                .thenReturn(successResponse(
                        "0000000003",
                        LookupMode.SPECIFIC,
                        CustomerStatus.SUSPENDED,
                        742,
                        RiskRating.HIGH,
                        List.of("STATUS_SUSPENDED")
                ));

        mockMvc.perform(get("/api/v1/customers/123456/0000000003").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.riskAssessment.riskRating").value("HIGH"))
                .andExpect(jsonPath("$.riskAssessment.reasons[0]").value("STATUS_SUSPENDED"));
    }

    @Test
    void lowCreditScoreReturnsHighRiskInApiResponse() throws Exception {
        when(customerInquiryService.inquire("123456", "0000000004"))
                .thenReturn(successResponse(
                        "0000000004",
                        LookupMode.SPECIFIC,
                        CustomerStatus.ACTIVE,
                        580,
                        RiskRating.HIGH,
                        List.of("CREDIT_SCORE_LT_600")
                ));

        mockMvc.perform(get("/api/v1/customers/123456/0000000004").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.riskAssessment.riskRating").value("HIGH"))
                .andExpect(jsonPath("$.riskAssessment.reasons[0]").value("CREDIT_SCORE_LT_600"));
    }

    @Test
    void serviceExceptionReturnsHttp500() throws Exception {
        doThrow(new RuntimeException("boom"))
                .when(customerInquiryService)
                .inquire("123456", "0000000001");

        mockMvc.perform(get("/api/v1/customers/123456/0000000001").accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.errorCode").value("INTERNAL_ERROR"));
    }

    private static CustomerInquiryResponse successResponse(String customerNumber, LookupMode mode) {
        return successResponse(
                customerNumber,
                mode,
                CustomerStatus.ACTIVE,
                742,
                RiskRating.LOW,
                List.of("ACTIVE_SCORE_GE_700_REVIEW_CURRENT")
        );
    }

    private static CustomerInquiryResponse successResponse(
            String customerNumber,
            LookupMode mode,
            CustomerStatus customerStatus,
            int creditScore,
            RiskRating riskRating,
            List<String> reasons
    ) {
        return new CustomerInquiryResponse(
                new LegacyInquiryStatus("Y", "0", "Inquiry successful"),
                mode,
                new CustomerResponse(
                        "CUST",
                        "123456",
                        customerNumber,
                        "Mr",
                        "John",
                        "Smith",
                        LocalDate.of(1975, 1, 1),
                        "4165550101",
                        new AddressResponse("1 Main Street", "Suite 100", "Toronto", "M5H2N2", "Canada"),
                        customerStatus,
                        LocalDate.of(2010, 6, 15),
                        creditScore,
                        LocalDate.of(2026, 1, 15)
                ),
                new RiskAssessmentResponse(riskRating, false, reasons)
        );
    }

    private static CustomerInquiryResponse notFoundResponse(LookupMode mode, String failCode) {
        return new CustomerInquiryResponse(
                new LegacyInquiryStatus("N", failCode, "Customer not found"),
                mode,
                null,
                null
        );
    }
}
