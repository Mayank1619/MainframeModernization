package com.modernizemainframe.stepdefinitions;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Arrays;
import java.util.List;
import java.util.Objects;

import com.modernizemainframe.api.AccountInquiryClient;

import io.cucumber.java.en.And;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import io.restassured.response.Response;
import org.opentest4j.TestAbortedException;

public class AccountInquiryStepDefinitions {

	private static final String VALID_TOKEN = "valid-inqacc-inquirer-token";
	private static final String MALFORMED_TOKEN = "not-a-jwt";
	private static final String EXPIRED_TOKEN = "expired-token";
	private static final String FORBIDDEN_TOKEN = "forbidden-token";

	private final AccountInquiryClient apiClient = new AccountInquiryClient();
	private Response response;
	private String requestCorrelationId;

	@Given("blocked precondition {string}")
	public void blockedPrecondition(String reason) {
		throw new TestAbortedException("Blocked by precondition: " + reason);
	}

	@Given("optional precondition {string} is enabled")
	public void optionalPreconditionIsEnabled(String propertyName) {
		boolean enabled = Boolean.getBoolean(propertyName);
		if (!enabled) {
			throw new TestAbortedException("Enable JVM property to run this scenario: -D" + propertyName + "=true");
		}
	}

	@When("I request the account with sort code {string} and account number {string}")
	public void iRequestTheAccountWithSortCodeAndAccountNumber(String sortCode, String accountNumber) {
		requestCorrelationId = null;
		response = apiClient.getAccountWithBearerToken(sortCode, accountNumber, VALID_TOKEN);
	}

	@When("I request the account with sort code {string} and account number {string} with bearer token {string}")
	public void iRequestTheAccountWithSortCodeAndAccountNumberWithBearerToken(
			String sortCode,
			String accountNumber,
			String bearerToken
	) {
		requestCorrelationId = null;
		response = apiClient.getAccountWithBearerToken(sortCode, accountNumber, bearerToken);
	}

	@When("I request the account with sort code {string} and account number {string} without authorization")
	public void iRequestTheAccountWithSortCodeAndAccountNumberWithoutAuthorization(
			String sortCode,
			String accountNumber
	) {
		requestCorrelationId = null;
		response = apiClient.getAccountWithoutAuthorization(sortCode, accountNumber);
	}

	@When("I request the account with sort code {string} and account number {string} with correlation id {string}")
	public void iRequestTheAccountWithSortCodeAndAccountNumberWithBearerTokenAndCorrelationId(
			String sortCode,
			String accountNumber,
			String correlationId
	) {
		requestCorrelationId = correlationId;
		response = apiClient.getAccountWithBearerTokenAndCorrelationId(sortCode, accountNumber, VALID_TOKEN, correlationId);
	}

	@When("I request the account with sort code {string} and account number {string} using auth mode {string}")
	public void iRequestTheAccountWithSortCodeAndAccountNumberUsingAuthMode(
			String sortCode,
			String accountNumber,
			String authMode
	) {
		requestCorrelationId = null;
		switch (authMode) {
			case "valid":
				response = apiClient.getAccountWithBearerToken(sortCode, accountNumber, VALID_TOKEN);
				break;
			case "missing":
				response = apiClient.getAccountWithoutAuthorization(sortCode, accountNumber);
				break;
			case "malformed":
				response = apiClient.getAccountWithBearerToken(sortCode, accountNumber, MALFORMED_TOKEN);
				break;
			case "expired":
				response = apiClient.getAccountWithBearerToken(sortCode, accountNumber, EXPIRED_TOKEN);
				break;
			case "forbidden":
				response = apiClient.getAccountWithBearerToken(sortCode, accountNumber, FORBIDDEN_TOKEN);
				break;
			default:
				throw new IllegalArgumentException("Unsupported auth mode: " + authMode);
		}
	}

	@Then("the account inquiry response status code is {int}")
	public void theAccountInquiryResponseStatusCodeIs(int expectedStatusCode) {
		assertThat(response.getStatusCode())
				.as("Expected HTTP status code %d but got %d", expectedStatusCode, response.getStatusCode())
				.isEqualTo(expectedStatusCode);
	}

	@Then("the account inquiry response status code is one of {string}")
	public void theAccountInquiryResponseStatusCodeIsOneOf(String commaSeparatedCodes) {
		int actualStatusCode = response.getStatusCode();
		List<Integer> expectedCodes = Arrays.stream(commaSeparatedCodes.split(","))
				.map(String::trim)
				.map(Integer::parseInt)
				.toList();
		assertThat(expectedCodes)
				.as("Expected HTTP status code one of %s but got %d", expectedCodes, actualStatusCode)
				.contains(actualStatusCode);
	}

	@And("the account response contains all required account fields")
	public void theAccountResponseContainsAllRequiredAccountFields() {
		assertPresentAtAnyPath("eyecatcher", "account.eyecatcher");
		assertPresentAtAnyPath("customerNumber", "account.customerNumber");
		assertPresentAtAnyPath("sortcode", "account.sortcode");
		assertPresentAtAnyPath("accountNumber", "account.accountNumber");
		assertPresentAtAnyPath("accountType", "account.accountType");
		assertPresentAtAnyPath("interestRate", "account.interestRate");
		assertPresentAtAnyPath("accountOpened", "account.accountOpened");
		assertPresentAtAnyPath("overdraftLimit", "account.overdraftLimit");
		assertPresentAtAnyPath("lastStatementDate", "account.lastStatementDate");
		assertPresentAtAnyPath("nextStatementDate", "account.nextStatementDate");
		assertPresentAtAnyPath("availableBalance", "account.availableBalance");
		assertPresentAtAnyPath("actualBalance", "account.actualBalance");
	}

	@And("the account date fields are ISO formatted")
	public void theAccountDateFieldsAreIsoFormatted() {
		assertMatchesRegexAtAnyPath("\\d{4}-\\d{2}-\\d{2}", "accountOpened", "account.accountOpened");
		assertMatchesRegexAtAnyPath("\\d{4}-\\d{2}-\\d{2}", "lastStatementDate", "account.lastStatementDate");
		assertMatchesRegexAtAnyPath("\\d{4}-\\d{2}-\\d{2}", "nextStatementDate", "account.nextStatementDate");
	}

	@And("the account numeric fields are numeric")
	public void theAccountNumericFieldsAreNumeric() {
		assertNumericAtAnyPath("interestRate", "account.interestRate");
		assertNumericAtAnyPath("overdraftLimit", "account.overdraftLimit");
		assertNumericAtAnyPath("availableBalance", "account.availableBalance");
		assertNumericAtAnyPath("actualBalance", "account.actualBalance");
	}

	@And("the account string fields are trimmed")
	public void theAccountStringFieldsAreTrimmed() {
		assertTrimmedAtAnyPath("eyecatcher", "account.eyecatcher");
		assertTrimmedAtAnyPath("customerNumber", "account.customerNumber");
		assertTrimmedAtAnyPath("sortcode", "account.sortcode");
		assertTrimmedAtAnyPath("accountNumber", "account.accountNumber");
		assertTrimmedAtAnyPath("accountType", "account.accountType");
	}

	@And("the error response has standardized fields")
	public void theErrorResponseHasStandardizedFields() {
		assertPresentAtPath("error.code");
		assertPresentAtPath("error.message");
		assertPresentAtPath("error.timestamp");
		assertPresentAtPath("error.correlationId");
	}

	@And("the correlation id is echoed in response")
	public void theCorrelationIdIsEchoedInResponse() {
		String headerCorrelationId = response.getHeader("X-Correlation-Id");
		String bodyCorrelationId = stringValue(response.jsonPath().get("error.correlationId"));

		boolean echoedInHeader = Objects.equals(requestCorrelationId, headerCorrelationId);
		boolean echoedInBody = Objects.equals(requestCorrelationId, bodyCorrelationId);

		assertThat(echoedInHeader || echoedInBody)
				.as("Expected correlation id '%s' to be echoed in response header or payload", requestCorrelationId)
				.isTrue();
	}

	@And("the response contains a generated correlation id")
	public void theResponseContainsAGeneratedCorrelationId() {
		String headerCorrelationId = response.getHeader("X-Correlation-Id");
		String bodyCorrelationId = stringValue(response.jsonPath().get("error.correlationId"));

		boolean present = (headerCorrelationId != null && !headerCorrelationId.isBlank())
				|| (bodyCorrelationId != null && !bodyCorrelationId.isBlank());

		assertThat(present)
				.as("Expected generated correlation id in header or payload")
				.isTrue();
	}

	private void assertPresentAtPath(String path) {
		Object value = response.jsonPath().get(path);
		assertThat(value)
				.as("Expected response path '%s' to be present", path)
				.isNotNull();
		if (value instanceof String stringValue) {
			assertThat(stringValue)
					.as("Expected response path '%s' to be non-blank", path)
					.isNotBlank();
		}
	}

	private void assertPresentAtAnyPath(String firstPath, String secondPath) {
		Object value = valueAtAnyPath(firstPath, secondPath);
		assertThat(value)
				.as("Expected response path '%s' or '%s' to be present", firstPath, secondPath)
				.isNotNull();
	}

	private void assertMatchesRegexAtAnyPath(String regex, String firstPath, String secondPath) {
		Object rawValue = valueAtAnyPath(firstPath, secondPath);
		String value = stringValue(rawValue);
		assertThat(value)
				.as("Expected response path '%s' or '%s' to match regex '%s'", firstPath, secondPath, regex)
				.matches(regex);
	}

	private void assertNumericAtAnyPath(String firstPath, String secondPath) {
		Object rawValue = valueAtAnyPath(firstPath, secondPath);
		assertThat(rawValue)
				.as("Expected response path '%s' or '%s' to be numeric", firstPath, secondPath)
				.isInstanceOfAny(Number.class, Integer.class, Long.class, Float.class, Double.class);
	}

	private void assertTrimmedAtAnyPath(String firstPath, String secondPath) {
		Object rawValue = valueAtAnyPath(firstPath, secondPath);
		String value = stringValue(rawValue);
		assertThat(value)
				.as("Expected response path '%s' or '%s' to be trimmed", firstPath, secondPath)
				.isEqualTo(value.trim());
	}

	private Object valueAtAnyPath(String firstPath, String secondPath) {
		Object firstValue = response.jsonPath().get(firstPath);
		if (firstValue != null) {
			return firstValue;
		}
		return response.jsonPath().get(secondPath);
	}

	private String stringValue(Object rawValue) {
		return rawValue == null ? null : String.valueOf(rawValue);
	}
}
