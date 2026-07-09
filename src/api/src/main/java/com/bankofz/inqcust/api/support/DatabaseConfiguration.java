package com.bankofz.inqcust.api.support;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.sql.DataSource;

@Configuration
public class DatabaseConfiguration {

    @Bean(destroyMethod = "close")
    @ConditionalOnProperty(name = "app.data.mode", havingValue = "db")
    public DataSource dataSource(
            @Value("${app.db.url:}") String dbUrl,
            @Value("${app.db.username:}") String dbUsername,
            @Value("${app.db.password:}") String dbPassword,
            @Value("${app.db.pool.max-size:10}") int maxPoolSize,
            @Value("${app.db.pool.min-idle:2}") int minIdle,
            @Value("${app.db.pool.connection-timeout-ms:30000}") long connectionTimeoutMs,
            @Value("${app.db.pool.idle-timeout-ms:600000}") long idleTimeoutMs,
            @Value("${app.db.pool.max-lifetime-ms:1800000}") long maxLifetimeMs
    ) {
        if (dbUrl == null || dbUrl.isBlank()) {
            throw new IllegalStateException("app.db.url is required when app.data.mode=db");
        }

        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(dbUrl);
        if (dbUsername != null && !dbUsername.isBlank()) {
            config.setUsername(dbUsername);
        }
        if (dbPassword != null && !dbPassword.isBlank()) {
            config.setPassword(dbPassword);
        }
        config.setMaximumPoolSize(maxPoolSize);
        config.setMinimumIdle(minIdle);
        config.setConnectionTimeout(connectionTimeoutMs);
        config.setIdleTimeout(idleTimeoutMs);
        config.setMaxLifetime(maxLifetimeMs);
        config.setPoolName("inqcust-db-pool");

        return new HikariDataSource(config);
    }
}