package com.modernizemainframe.api;

import io.restassured.response.Response;

public class CustomerInquiryClient implements BaseRequest {

    public Response getCustomer(String sortCode, String customerNumber) {
        return jsonRequest()
                .when()
                .get("/api/v1/customers/{sortCode}/{customerNumber}", sortCode, customerNumber);
    }

    public Response getCustomerCompatibility(String customerNumber) {
        return jsonRequest()
                .queryParam("customerNumber", customerNumber)
                .when()
                .get("/api/v1/customers");
    }

    public Response getCustomerCompatibility(String sortCode, String customerNumber) {
        return jsonRequest()
                .queryParam("sortCode", sortCode)
                .queryParam("customerNumber", customerNumber)
                .when()
                .get("/api/v1/customers");
    }
}
