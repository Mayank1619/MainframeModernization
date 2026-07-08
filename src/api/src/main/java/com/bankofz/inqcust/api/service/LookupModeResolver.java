package com.bankofz.inqcust.api.service;

import com.bankofz.inqcust.api.domain.LookupMode;
import org.springframework.stereotype.Component;

@Component
public class LookupModeResolver {

    public static final String RANDOM_CUSTOMER_NUMBER = "0000000000";
    public static final String LATEST_CUSTOMER_NUMBER = "9999999999";

    public LookupMode resolve(String customerNumber) {
        if (RANDOM_CUSTOMER_NUMBER.equals(customerNumber)) {
            return LookupMode.RANDOM;
        }
        if (LATEST_CUSTOMER_NUMBER.equals(customerNumber)) {
            return LookupMode.LATEST;
        }
        return LookupMode.SPECIFIC;
    }
}
