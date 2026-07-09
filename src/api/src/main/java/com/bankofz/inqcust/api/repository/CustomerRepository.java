package com.bankofz.inqcust.api.repository;

import com.bankofz.inqcust.api.domain.CustomerRecord;

import java.util.List;
import java.util.Optional;

public interface CustomerRepository {

    Optional<CustomerRecord> findBySortCodeAndCustomerNumber(String sortCode, String customerNumber);

    List<CustomerRecord> findBySortCode(String sortCode);

    default Optional<CustomerRecord> findLatestBySortCode(String sortCode) {
        return findBySortCode(sortCode).stream()
            // Customer numbers are fixed-width 10-digit strings; lexicographic order matches numeric order.
            .max((left, right) -> left.customerNumber().compareTo(right.customerNumber()));
    }
}
