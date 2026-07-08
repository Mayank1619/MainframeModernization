package com.bankofz.inqcust.api.service;

import org.springframework.stereotype.Component;

import java.time.DateTimeException;
import java.time.LocalDate;

@Component
public class LegacyDateConverter {

    public LocalDate toLocalDate(Integer legacyDate) {
        if (legacyDate == null) {
            return null;
        }

        String value = String.format("%08d", legacyDate);
        int year = Integer.parseInt(value.substring(0, 4));
        int month = Integer.parseInt(value.substring(4, 6));
        int day = Integer.parseInt(value.substring(6, 8));

        try {
            return LocalDate.of(year, month, day);
        } catch (DateTimeException exception) {
            throw new LegacyDateConversionException("Invalid legacy date: " + legacyDate, exception);
        }
    }
}
