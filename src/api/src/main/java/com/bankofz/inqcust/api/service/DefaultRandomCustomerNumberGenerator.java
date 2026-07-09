package com.bankofz.inqcust.api.service;

import org.springframework.stereotype.Component;

import java.util.random.RandomGenerator;

@Component
public class DefaultRandomCustomerNumberGenerator implements RandomCustomerNumberGenerator {

    private final RandomGenerator randomGenerator;

    public DefaultRandomCustomerNumberGenerator() {
        this.randomGenerator = RandomGenerator.getDefault();
    }

    @Override
    public String nextCustomerNumber(long highestCustomerNumber) {
        long value = randomGenerator.nextLong(1, highestCustomerNumber + 1);
        return String.format("%010d", value);
    }
}
