package com.bankofz.inqcust.api.repository;

import com.bankofz.inqcust.api.domain.CustomerRecord;

import java.util.List;
import java.util.Optional;

public interface CustomerRepository {

    Optional<CustomerRecord> findBySortCodeAndCustomerNumber(String sortCode, String customerNumber);

    List<CustomerRecord> findBySortCode(String sortCode);

    default Optional<CustomerRecord> findLatestBySortCode(String sortCode) {
        return findBySortCode(sortCode).stream()
                .max((left, right) -> Integer.compare(
                        Integer.parseInt(left.customerNumber()),
                        Integer.parseInt(right.customerNumber())
                ));
    }
}
