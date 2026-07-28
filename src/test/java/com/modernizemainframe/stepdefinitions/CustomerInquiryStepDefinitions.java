package com.modernizemainframe.stepdefinitions;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Arrays;
import java.util.List;

import com.modernizemainframe.api.CustomerInquiryClient;

import io.cucumber.java.en.And;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import io.restassured.response.Response;

public class CustomerInquiryStepDefinitions {

    private final CustomerInquiryClient apiClient = new CustomerInquiryClient();
    private Response response;

    @When("I request the customer with sort code {string} and customer number {string}")
    public void iRequestTheCustomerWithSortCodeAndCustomerNumber(String sortCode, String customerNumber) {
        this.response = apiClient.getCustomer(sortCode, customerNumber);
    }

    @When("I request the compatibility customer endpoint with customer number {string}")
    public void iRequestTheCompatibilityCustomerEndpointWithCustomerNumber(String customerNumber) {
        this.response = apiClient.getCustomerCompatibility(customerNumber);
    }

    @When("I request the compatibility customer endpoint with sort code {string} and customer number {string}")
    public void iRequestTheCompatibilityCustomerEndpointWithSortCodeAndCustomerNumber(String sortCode,
                                                                                       String customerNumber) {
        this.response = apiClient.getCustomerCompatibility(sortCode, customerNumber);
    }

    @Then("the response status code is {int}")
    public void theResponseStatusCodeIs(int expectedStatusCode) {
        assertThat(response.getStatusCode())
                .as("Expected HTTP status code %d but got %d", expectedStatusCode, response.getStatusCode())
                .isEqualTo(expectedStatusCode);
    }

    @Then("the response status code is {int} or {int}")
    public void theResponseStatusCodeIsOr(int expectedStatusCode1, int expectedStatusCode2) {
        int actualStatusCode = response.getStatusCode();
        List<Integer> expectedCodes = List.of(expectedStatusCode1, expectedStatusCode2);
        assertThat(expectedCodes)
                .as("Expected HTTP status code %s but got %d", expectedCodes, actualStatusCode)
                .contains(actualStatusCode);
    }

    @And("the response body legacyStatus.inquirySuccess is {string}")
    public void theResponseBodyLegacyStatusInquirySuccessIs(String expectedValue) {
        String actualValue = response.jsonPath().getString("legacyStatus.inquirySuccess");
        assertThat(actualValue)
                .as("Expected legacyStatus.inquirySuccess to be '%s' but got '%s'", expectedValue, actualValue)
                .isEqualTo(expectedValue);
    }

    @And("the response body legacyStatus.inquiryFailCode is {string}")
    public void theResponseBodyLegacyStatusInquiryFailCodeIs(String expectedValue) {
        Object rawValue = response.jsonPath().get("legacyStatus.inquiryFailCode");
        String actualValue = rawValue != null ? String.valueOf(rawValue) : null;
        assertThat(actualValue)
                .as("Expected legacyStatus.inquiryFailCode to be '%s' but got '%s'", expectedValue, actualValue)
                .isEqualTo(expectedValue);
    }

    @And("the response body lookupMode is {string}")
    public void theResponseBodyLookupModeIs(String expectedValue) {
        String actualValue = response.jsonPath().getString("lookupMode");
        assertThat(actualValue)
                .as("Expected lookupMode to be '%s' but got '%s'", expectedValue, actualValue)
                .isEqualTo(expectedValue);
    }

    @And("the response body {string} is {string}")
    public void theResponseBodyPathIs(String path, String expectedValue) {
        Object rawValue = response.jsonPath().get(path);
        String actualValue = rawValue != null ? String.valueOf(rawValue) : null;
        assertThat(actualValue)
                .as("Expected response body path '%s' to be '%s' but got '%s'", path, expectedValue, actualValue)
                .isEqualTo(expectedValue);
    }

    @And("the response body {string} is not {string}")
    public void theResponseBodyPathIsNot(String path, String unexpectedValue) {
        Object rawValue = response.jsonPath().get(path);
        String actualValue = rawValue != null ? String.valueOf(rawValue) : null;
        assertThat(actualValue)
                .as("Expected response body path '%s' to not be '%s'", path, unexpectedValue)
                .isNotEqualTo(unexpectedValue);
    }

    @And("the response body {string} is null")
    public void theResponseBodyPathIsNull(String path) {
        Object value = response.jsonPath().get(path);
        assertThat(value)
                .as("Expected response body path '%s' to be null", path)
                .isNull();
    }

    @And("the response body {string} is not null")
    public void theResponseBodyPathIsNotNull(String path) {
        Object value = response.jsonPath().get(path);
        assertThat(value)
                .as("Expected response body path '%s' to be present", path)
                .isNotNull();
    }

    @And("the response status code is one of {string}")
    public void theResponseStatusCodeIsOneOf(String commaSeparatedCodes) {
        int actualStatusCode = response.getStatusCode();
        List<Integer> expectedCodes = Arrays.stream(commaSeparatedCodes.split(","))
                .map(String::trim)
                .map(Integer::parseInt)
                .toList();
        assertThat(expectedCodes)
                .as("Expected HTTP status code one of %s but got %d", expectedCodes, actualStatusCode)
                .contains(actualStatusCode);
    }
}
