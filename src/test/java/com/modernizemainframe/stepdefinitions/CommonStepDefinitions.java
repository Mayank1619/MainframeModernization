package com.modernizemainframe.stepdefinitions;

import static org.assertj.core.api.Assertions.assertThat;

import com.modernizemainframe.api.BaseClient;
import com.modernizemainframe.api.BaseClientImpl;

import io.cucumber.java.After;
import io.cucumber.java.Before;
import io.cucumber.java.en.Given;

public class CommonStepDefinitions {

    BaseClient apiClient = new BaseClientImpl();
    
    @Before
    public void setUp() {
        apiClient.configure();
    }

    @After
    public void tearDown() {
        apiClient = null;
    }

    @Given("the API is running at localhost:8080")
    public void theApiIsRunningAtLocalhost8080() { 
        // TODO: convert this function to accept a general endpoint that can be set in a config file.
        assertThat(apiClient.baseUri()).isEqualTo("http://localhost");
        assertThat(apiClient.port()).isEqualTo(8080);
    }
}
