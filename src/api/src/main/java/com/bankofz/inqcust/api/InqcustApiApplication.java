package com.bankofz.inqcust.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)
public class InqcustApiApplication {

    public static void main(String[] args) {
        SpringApplication.run(InqcustApiApplication.class, args);
    }
}
