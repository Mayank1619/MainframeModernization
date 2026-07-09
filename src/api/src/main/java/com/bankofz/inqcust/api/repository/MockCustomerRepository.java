package com.bankofz.inqcust.api.repository;

import com.bankofz.inqcust.api.domain.CustomerRecord;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Repository;

import javax.sql.DataSource;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;

@Repository
public class MockCustomerRepository implements CustomerRepository {

    private static final String MODE_DB = "db";
    // Allow only unquoted SQL identifiers with optional schema prefix (e.g., CUSTOMER or BANK.CUSTOMER).
    private static final Pattern SAFE_TABLE_NAME_PATTERN =
            Pattern.compile("^[A-Za-z_][A-Za-z0-9_$]*(\\.[A-Za-z_][A-Za-z0-9_$]*){0,2}$");
    private final List<CustomerRecord> customers;
    private final String dataMode;
    private final String dbTableName;
    private final DataSource dataSource;

    public MockCustomerRepository(
            @Value("${app.data.mode:mock}") String dataMode,
            @Value("${app.mock-data.path:mock-data/customer-records.json}") String mockDataPath,
            @Value("${app.db.table-name:CUSTOMER}") String dbTableName,
            ObjectMapper objectMapper,
            ObjectProvider<DataSource> dataSourceProvider
    ) {
        this(
                dataMode,
                mockDataPath,
                dbTableName,
                objectMapper,
                dataSourceProvider.getIfAvailable()
        );
    }

    MockCustomerRepository(
            String dataMode,
            String mockDataPath,
            String dbTableName,
            ObjectMapper objectMapper,
            DataSource dataSource
    ) {
        this.dataMode = dataMode == null ? "mock" : dataMode.trim().toLowerCase();
        this.dbTableName = dbTableName == null ? null : dbTableName.trim();
        this.dataSource = dataSource;

        if (isDbMode()) {
            validateDbConfiguration();
            this.customers = List.of();
            return;
        }

        this.customers = loadCustomers(mockDataPath, objectMapper);
    }

    @Override
    public Optional<CustomerRecord> findBySortCodeAndCustomerNumber(String sortCode, String customerNumber) {
        if (isDbMode()) {
            return findBySortCodeAndCustomerNumberFromDb(sortCode, customerNumber);
        }

        return customers.stream()
                .filter(customer -> sortCode.equals(customer.sortCode())
                        && customerNumber.equals(customer.customerNumber()))
                .findFirst();
    }

    @Override
    public List<CustomerRecord> findBySortCode(String sortCode) {
        if (isDbMode()) {
            return findBySortCodeFromDb(sortCode);
        }

        return customers.stream()
                .filter(customer -> sortCode.equals(customer.sortCode()))
                .toList();
    }

    @Override
    public Optional<CustomerRecord> findLatestBySortCode(String sortCode) {
        if (isDbMode()) {
            return findLatestBySortCodeFromDb(sortCode);
        }

        return customers.stream()
                .filter(customer -> sortCode.equals(customer.sortCode()))
                // Customer numbers are fixed-width 10-digit strings; lexicographic order matches numeric order.
                .max((left, right) -> left.customerNumber().compareTo(right.customerNumber()));
    }

    private Optional<CustomerRecord> findBySortCodeAndCustomerNumberFromDb(String sortCode, String customerNumber) {
        String sql = """
                SELECT
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
                FROM %s
                WHERE CUSTOMER_SORTCODE = ? AND CUSTOMER_NUMBER = ?
                """.formatted(dbTableName);

        try (Connection connection = openConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, sortCode);
            statement.setString(2, customerNumber);

            try (ResultSet resultSet = statement.executeQuery()) {
                if (resultSet.next()) {
                    return Optional.of(toCustomerRecord(resultSet));
                }
                return Optional.empty();
            }
        } catch (SQLException exception) {
            throw new IllegalStateException("Failed DB lookup for specific customer", exception);
        }
    }

    private List<CustomerRecord> findBySortCodeFromDb(String sortCode) {
        String sql = """
                SELECT
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
                FROM %s
                WHERE CUSTOMER_SORTCODE = ?
                """.formatted(dbTableName);

        try (Connection connection = openConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, sortCode);

            try (ResultSet resultSet = statement.executeQuery()) {
                java.util.ArrayList<CustomerRecord> results = new java.util.ArrayList<>();
                while (resultSet.next()) {
                    results.add(toCustomerRecord(resultSet));
                }
                return results;
            }
        } catch (SQLException exception) {
            throw new IllegalStateException("Failed DB lookup for sort code", exception);
        }
    }

    private Optional<CustomerRecord> findLatestBySortCodeFromDb(String sortCode) {
        String sql = """
                SELECT
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
                FROM %s
                WHERE CUSTOMER_SORTCODE = ?
                ORDER BY CUSTOMER_NUMBER DESC
                FETCH FIRST 1 ROW ONLY
                """.formatted(dbTableName);

        try (Connection connection = openConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, sortCode);

            try (ResultSet resultSet = statement.executeQuery()) {
                if (resultSet.next()) {
                    return Optional.of(toCustomerRecord(resultSet));
                }
                return Optional.empty();
            }
        } catch (SQLException exception) {
            throw new IllegalStateException("Failed DB lookup for latest customer", exception);
        }
    }

    private Connection openConnection() throws SQLException {
        if (dataSource == null) {
            throw new IllegalStateException("DataSource is not configured while app.data.mode=db");
        }
        return dataSource.getConnection();
    }

    private CustomerRecord toCustomerRecord(ResultSet resultSet) throws SQLException {
        return new CustomerRecord(
                resultSet.getString("CUSTOMER_EYECATCHER"),
                resultSet.getString("CUSTOMER_SORTCODE"),
                resultSet.getString("CUSTOMER_NUMBER"),
                resultSet.getString("CUSTOMER_TITLE"),
                resultSet.getString("CUSTOMER_FIRST_NAME"),
                resultSet.getString("CUSTOMER_LAST_NAME"),
                getNullableInteger(resultSet, "CUSTOMER_DATE_OF_BIRTH"),
                resultSet.getString("CUSTOMER_PHONE"),
                resultSet.getString("CUSTOMER_ADDR_LINE1"),
                resultSet.getString("CUSTOMER_ADDR_LINE2"),
                resultSet.getString("CUSTOMER_CITY"),
                resultSet.getString("CUSTOMER_POSTCODE"),
                resultSet.getString("CUSTOMER_COUNTRY"),
                resultSet.getString("CUSTOMER_STATUS"),
                getNullableInteger(resultSet, "CUSTOMER_CREATED_DATE"),
                getNullableInteger(resultSet, "CUSTOMER_CREDIT_SCORE"),
                getNullableInteger(resultSet, "CUSTOMER_CS_REVIEW_DATE")
        );
    }

    private Integer getNullableInteger(ResultSet resultSet, String columnName) throws SQLException {
        int value = resultSet.getInt(columnName);
        return resultSet.wasNull() ? null : value;
    }

    private boolean isDbMode() {
        return MODE_DB.equals(dataMode);
    }

    private void validateDbConfiguration() {
        if (dataSource == null) {
            throw new IllegalStateException("DataSource is required when app.data.mode=db");
        }
        if (dbTableName == null || dbTableName.isBlank()) {
            throw new IllegalStateException("app.db.table-name must not be empty when app.data.mode=db");
        }
        if (!SAFE_TABLE_NAME_PATTERN.matcher(dbTableName).matches()) {
            throw new IllegalStateException(
                    "app.db.table-name contains unsupported characters; use unquoted identifiers like CUSTOMER or SCHEMA.CUSTOMER"
            );
        }
    }

    private List<CustomerRecord> loadCustomers(String mockDataPath, ObjectMapper objectMapper) {
        try (InputStream inputStream = openInputStream(mockDataPath)) {
            MockDataFile dataFile = objectMapper.readValue(inputStream, MockDataFile.class);
            if (dataFile == null || dataFile.customers() == null) {
                return Collections.emptyList();
            }
            return dataFile.customers();
        } catch (IOException exception) {
            throw new IllegalStateException("Failed to load mock customer data", exception);
        }
    }

    private InputStream openInputStream(String mockDataPath) throws IOException {
        String resolvedPath = mockDataPath == null ? "" : mockDataPath;

        Path directPath = Path.of(resolvedPath);
        if (Files.exists(directPath)) {
            return Files.newInputStream(directPath);
        }

        Path repoRelativePath = Path.of("..", "..", resolvedPath);
        if (Files.exists(repoRelativePath)) {
            return Files.newInputStream(repoRelativePath);
        }

        ClassPathResource resource = new ClassPathResource(resolvedPath);
        if (resource.exists()) {
            return resource.getInputStream();
        }

        throw new IOException("Mock data file not found: " + resolvedPath);
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record MockDataFile(List<CustomerRecord> customers) {
    }
}
