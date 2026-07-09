package com.bankofz.inqcust.api.repository;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.h2.jdbcx.JdbcDataSource;
import org.junit.jupiter.api.Test;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MockCustomerRepositoryTest {

    private static final String DB_URL = "jdbc:h2:mem:inqcust_repo_test;MODE=DB2;DB_CLOSE_DELAY=-1";
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void rejectsUnsafeDbTableNameInDbMode() {
        IllegalStateException exception = assertThrows(
                IllegalStateException.class,
                () -> new MockCustomerRepository(
                        "db",
                        "mock-data/customer-records.json",
                        "CUSTOMER; DROP TABLE CUSTOMER",
                    objectMapper,
                    createDataSource(DB_URL)
                )
        );

        assertTrue(exception.getMessage().contains("app.db.table-name"));
    }

    @Test
    void acceptsSchemaQualifiedDbTableNameInDbMode() {
        assertDoesNotThrow(() -> new MockCustomerRepository(
                "db",
                "mock-data/customer-records.json",
                "BANK_OF_Z.CUSTOMER",
                objectMapper,
                createDataSource(DB_URL)
        ));
    }

    @Test
    void mockModeStillLoadsDataAndFindsKnownCustomer() {
        MockCustomerRepository repository = new MockCustomerRepository(
                "mock",
                "mock-data/customer-records.json",
                "CUSTOMER",
            objectMapper,
            (DataSource) null
        );

        assertTrue(repository.findBySortCodeAndCustomerNumber("123456", "0000000001").isPresent());
    }

    @Test
    void dbModeFindsSpecificCustomerFromDatabase() throws Exception {
        seedDatabase();

        MockCustomerRepository repository = new MockCustomerRepository(
                "db",
                "mock-data/customer-records.json",
                "CUSTOMER",
            objectMapper,
            createDataSource(DB_URL)
        );

        Optional<com.bankofz.inqcust.api.domain.CustomerRecord> customer =
                repository.findBySortCodeAndCustomerNumber("123456", "2147483648");

        assertTrue(customer.isPresent());
        assertEquals("2147483648", customer.get().customerNumber());
    }

    @Test
    void dbModeFindsLatestCustomerFromDatabase() throws Exception {
        seedDatabase();

        MockCustomerRepository repository = new MockCustomerRepository(
                "db",
                "mock-data/customer-records.json",
                "CUSTOMER",
            objectMapper,
            createDataSource(DB_URL)
        );

        Optional<com.bankofz.inqcust.api.domain.CustomerRecord> latest =
                repository.findLatestBySortCode("123456");

        assertTrue(latest.isPresent());
        assertNotNull(latest.get().customerNumber());
        assertEquals("3000000000", latest.get().customerNumber());
    }

    @Test
    void dbModeRequiresDataSourceConfiguration() {
        IllegalStateException exception = assertThrows(
                IllegalStateException.class,
                () -> new MockCustomerRepository(
                        "db",
                        "mock-data/customer-records.json",
                        "CUSTOMER",
                        objectMapper,
                    (DataSource) null
                )
        );

        assertTrue(exception.getMessage().contains("DataSource"));
    }

    private static void seedDatabase() throws SQLException {
        try (Connection connection = DriverManager.getConnection(DB_URL);
             Statement statement = connection.createStatement()) {
            statement.execute("DROP TABLE IF EXISTS CUSTOMER");
            statement.execute("""
                    CREATE TABLE CUSTOMER (
                        CUSTOMER_EYECATCHER VARCHAR(4),
                        CUSTOMER_SORTCODE CHAR(6),
                        CUSTOMER_NUMBER CHAR(10),
                        CUSTOMER_TITLE VARCHAR(10),
                        CUSTOMER_FIRST_NAME VARCHAR(50),
                        CUSTOMER_LAST_NAME VARCHAR(50),
                        CUSTOMER_DATE_OF_BIRTH INTEGER,
                        CUSTOMER_PHONE VARCHAR(20),
                        CUSTOMER_ADDR_LINE1 VARCHAR(50),
                        CUSTOMER_ADDR_LINE2 VARCHAR(50),
                        CUSTOMER_CITY VARCHAR(50),
                        CUSTOMER_POSTCODE VARCHAR(10),
                        CUSTOMER_COUNTRY VARCHAR(50),
                        CUSTOMER_STATUS VARCHAR(10),
                        CUSTOMER_CREATED_DATE INTEGER,
                        CUSTOMER_CREDIT_SCORE INTEGER,
                        CUSTOMER_CS_REVIEW_DATE INTEGER
                    )
                    """);
        }

        insertCustomer("123456", "2147483648", "Asha");
        insertCustomer("123456", "3000000000", "Mina");
        insertCustomer("123456", "0000000005", "John");
    }

    private static void insertCustomer(String sortCode, String customerNumber, String firstName) throws SQLException {
        String sql = """
                INSERT INTO CUSTOMER (
                    CUSTOMER_EYECATCHER,
                    CUSTOMER_SORTCODE,
                    CUSTOMER_NUMBER,
                    CUSTOMER_TITLE,
                    CUSTOMER_FIRST_NAME,
                    CUSTOMER_LAST_NAME,
                    CUSTOMER_DATE_OF_BIRTH,
                    CUSTOMER_PHONE,
                    CUSTOMER_ADDR_LINE1,
                    CUSTOMER_ADDR_LINE2,
                    CUSTOMER_CITY,
                    CUSTOMER_POSTCODE,
                    CUSTOMER_COUNTRY,
                    CUSTOMER_STATUS,
                    CUSTOMER_CREATED_DATE,
                    CUSTOMER_CREDIT_SCORE,
                    CUSTOMER_CS_REVIEW_DATE
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """;

        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, "CUST");
            statement.setString(2, sortCode);
            statement.setString(3, customerNumber);
            statement.setString(4, "Ms");
            statement.setString(5, firstName);
            statement.setString(6, "Smith");
            statement.setInt(7, 19880322);
            statement.setString(8, "4165550102");
            statement.setString(9, "2 King Street");
            statement.setString(10, "Suite 100");
            statement.setString(11, "Toronto");
            statement.setString(12, "M5V1A1");
            statement.setString(13, "Canada");
            statement.setString(14, "ACTIVE");
            statement.setInt(15, 20190510);
            statement.setInt(16, 650);
            statement.setInt(17, 20250510);
            statement.executeUpdate();
        }
    }

    private static DataSource createDataSource(String dbUrl) {
        JdbcDataSource dataSource = new JdbcDataSource();
        dataSource.setURL(dbUrl);
        return dataSource;
    }
}
