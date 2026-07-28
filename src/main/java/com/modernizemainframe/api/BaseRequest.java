package com.modernizemainframe.api;

import io.restassured.RestAssured;
import io.restassured.specification.RequestSpecification;

public interface BaseRequest {
    default RequestSpecification jsonRequest() {
        return RestAssured
                .given()
                .accept("application/json");
    }
}
