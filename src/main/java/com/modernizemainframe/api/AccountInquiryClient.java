package com.modernizemainframe.api;

import io.restassured.response.Response;

public class AccountInquiryClient implements BaseRequest {

    private static final String ACCOUNTS_ENDPOINT = "/v1/accounts/{sortCode}/{accountNumber}";

    public Response getAccountWithBearerToken(String sortCode, String accountNumber, String bearerToken) {
        return jsonRequest()
                .header("Authorization", "Bearer " + bearerToken)
                .when()
                .get(ACCOUNTS_ENDPOINT, sortCode, accountNumber);
    }

    public Response getAccountWithoutAuthorization(String sortCode, String accountNumber) {
        return jsonRequest()
                .when()
                .get(ACCOUNTS_ENDPOINT, sortCode, accountNumber);
    }

    public Response getAccountWithBearerTokenAndCorrelationId(
            String sortCode,
            String accountNumber,
            String bearerToken,
            String correlationId
    ) {
        return jsonRequest()
                .header("Authorization", "Bearer " + bearerToken)
                .header("X-Correlation-Id", correlationId)
                .when()
                .get(ACCOUNTS_ENDPOINT, sortCode, accountNumber);
    }

    public Response getAccountWithCorrelationId(String sortCode, String accountNumber, String correlationId) {
        return jsonRequest()
                .header("X-Correlation-Id", correlationId)
                .when()
                .get(ACCOUNTS_ENDPOINT, sortCode, accountNumber);
    }
}
