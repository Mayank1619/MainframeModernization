package com.bankofz.inqcust.api.repository;

import com.bankofz.inqcust.api.domain.CustomerRecord;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Repository;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

@Repository
public class MockCustomerRepository implements CustomerRepository {

    private final List<CustomerRecord> customers;

    public MockCustomerRepository(
            @Value("${app.mock-data.path:mock-data/customer-records.json}") String mockDataPath,
            ObjectMapper objectMapper
    ) {
        this.customers = loadCustomers(mockDataPath, objectMapper);
    }

    @Override
    public Optional<CustomerRecord> findBySortCodeAndCustomerNumber(String sortCode, String customerNumber) {
        return customers.stream()
                .filter(customer -> sortCode.equals(customer.sortCode())
                        && customerNumber.equals(customer.customerNumber()))
                .findFirst();
    }

    @Override
    public List<CustomerRecord> findBySortCode(String sortCode) {
        return customers.stream()
                .filter(customer -> sortCode.equals(customer.sortCode()))
                .toList();
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
        Path directPath = Path.of(mockDataPath);
        if (Files.exists(directPath)) {
            return Files.newInputStream(directPath);
        }

        Path repoRelativePath = Path.of("..", "..", mockDataPath);
        if (Files.exists(repoRelativePath)) {
            return Files.newInputStream(repoRelativePath);
        }

        ClassPathResource resource = new ClassPathResource(mockDataPath);
        if (resource.exists()) {
            return resource.getInputStream();
        }

        throw new IOException("Mock data file not found: " + mockDataPath);
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record MockDataFile(List<CustomerRecord> customers) {
    }
}
