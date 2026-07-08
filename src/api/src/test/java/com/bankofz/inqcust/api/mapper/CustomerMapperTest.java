package com.bankofz.inqcust.api.mapper;

import com.bankofz.inqcust.api.domain.CustomerRecord;
import com.bankofz.inqcust.api.domain.CustomerResponse;
import com.bankofz.inqcust.api.domain.CustomerStatus;
import com.bankofz.inqcust.api.service.LegacyDateConverter;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertEquals;

class CustomerMapperTest {

    private final CustomerMapper mapper = new CustomerMapper(new LegacyDateConverter());

    @Test
    void mapsAndTrimsLegacyFieldsAndConvertsDates() {
        CustomerRecord record = new CustomerRecord(
                "CUST",
                "123456",
                "0000000001",
                "Mr        ",
                "John                                              ",
                "Smith                                             ",
                19750101,
                "4165550101          ",
                "1 Main Street                                     ",
                "Suite 100                                         ",
                "Toronto                                           ",
                "M5H2N2    ",
                "Canada                                            ",
                "ACTIVE    ",
                20100615,
                742,
                20260115
        );

        CustomerResponse response = mapper.map(record);

        assertEquals("Mr", response.title());
        assertEquals("John", response.firstName());
        assertEquals("Smith", response.lastName());
        assertEquals("4165550101", response.phone());
        assertEquals("1 Main Street", response.address().line1());
        assertEquals("Suite 100", response.address().line2());
        assertEquals("Toronto", response.address().city());
        assertEquals("M5H2N2", response.address().postcode());
        assertEquals("Canada", response.address().country());
        assertEquals(CustomerStatus.ACTIVE, response.status());
        assertEquals(LocalDate.of(1975, 1, 1), response.dateOfBirth());
        assertEquals(LocalDate.of(2010, 6, 15), response.createdDate());
        assertEquals(LocalDate.of(2026, 1, 15), response.creditScoreReviewDate());
    }
}
