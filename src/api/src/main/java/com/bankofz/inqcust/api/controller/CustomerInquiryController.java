package com.bankofz.inqcust.api.controller;

import com.bankofz.inqcust.api.domain.CustomerInquiryResponse;
import com.bankofz.inqcust.api.service.CustomerInquiryService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Validated
@RestController
@RequestMapping("/api/v1/customers")
public class CustomerInquiryController {

    private final CustomerInquiryService customerInquiryService;

    public CustomerInquiryController(CustomerInquiryService customerInquiryService) {
        this.customerInquiryService = customerInquiryService;
    }

    @Operation(summary = "Retrieve customer inquiry response")
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Customer inquiry completed successfully"),
            @ApiResponse(responseCode = "400", description = "Validation error"),
            @ApiResponse(responseCode = "404", description = "Customer not found or special lookup failed"),
            @ApiResponse(responseCode = "500", description = "System error")
    })
    @GetMapping("/{sortCode}/{customerNumber}")
    public ResponseEntity<CustomerInquiryResponse> getCustomerInquiry(
            @PathVariable
            @Pattern(regexp = "^[0-9]{6}$", message = "sortCode must match ^[0-9]{6}$")
            String sortCode,
            @PathVariable
            @Pattern(regexp = "^[0-9]{10}$", message = "customerNumber must match ^[0-9]{10}$")
            String customerNumber
    ) {
        CustomerInquiryResponse response = customerInquiryService.inquire(sortCode, customerNumber);
        if ("Y".equals(response.legacyStatus().inquirySuccess())) {
            return ResponseEntity.ok(response);
        }
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
    }
}
