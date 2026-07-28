package com.modernizemainframe.api;

import io.restassured.RestAssured;

public interface BaseClient {
    public default void configure() {
        final String DEFAULT_HOST = "localhost";
        final int DEFAULT_PORT = 8080;

        String host = System.getProperty("api.host", DEFAULT_HOST);
        int port = Integer.getInteger("api.port", DEFAULT_PORT);
        RestAssured.baseURI = "http://" + host;
        RestAssured.port = port;
    }

    public default String baseUri() {
        return RestAssured.baseURI;
    }

    public default int port() {
        return RestAssured.port;
    }
}
