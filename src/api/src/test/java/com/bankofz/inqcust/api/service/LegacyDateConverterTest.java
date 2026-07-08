package com.bankofz.inqcust.api.service;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class LegacyDateConverterTest {

    private final LegacyDateConverter converter = new LegacyDateConverter();

    @Test
    void convertsLegacyDateSuccessfully() {
        LocalDate result = converter.toLocalDate(19750101);
        assertEquals(LocalDate.of(1975, 1, 1), result);
    }

    @Test
    void throwsControlledExceptionOnInvalidLegacyDate() {
        assertThrows(LegacyDateConversionException.class, () -> converter.toLocalDate(19751301));
    }
}
