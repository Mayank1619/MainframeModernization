# INQCUST API Module

This module is the Spring Boot implementation of the INQCUST customer inquiry service.

This README reflects the current implementation.

## Runtime API

- Endpoint: `GET /api/v1/customers/{sortCode}/{customerNumber}`
- Controller mapping:
	- Base path: `/api/v1/customers`
	- Method path: `/{sortCode}/{customerNumber}`
- Validation:
	- `sortCode` must be 6 digits
	- `customerNumber` must be 10 digits

### Special Customer Numbers

- `0000000000` = RANDOM lookup mode
- `9999999999` = LATEST lookup mode
- Any other 10-digit number = SPECIFIC lookup mode

## Data Source Modes

Switching mode is configuration-only via `app.data.mode` in `src/main/resources/application.properties`.

- Default mode: `mock`
	- Uses `mock-data/customer-records.json`
- Optional mode: `db`
	- Uses repository-backed DB queries when DB properties are provided

Important: a production database is not configured in this project by default.

## Repository Architecture

- `CustomerRepository` is the data access abstraction used by services.
- `MockCustomerRepository` currently provides:
	- mock JSON-backed behavior for local/default execution
	- DB-mode query paths for future integration
- Recent repository refactoring keeps service and controller behavior unchanged while supporting DB-mode latest lookup directly in SQL.

## OpenAPI And Traceability

- Active runtime OpenAPI file: `src/main/resources/openapi.yaml`
- Contract/spec artifact: `specs/001-inqcust-customer-inquiry-modernization/contracts/openapi.yaml`
- Build/runtime behavior should be aligned to these files, not legacy/generated artifacts.

## Build, Test, And Run

From `src/api`:

- Run tests: `mvn test`
- Run the service: `mvn spring-boot:run`

Use the Spring Boot Maven commands above for local build and run.

## Source Layout

- `src/main/java/com/bankofz/inqcust/api/controller`
	- REST endpoints and exception handling
- `src/main/java/com/bankofz/inqcust/api/service`
	- Lookup orchestration and business rules
- `src/main/java/com/bankofz/inqcust/api/repository`
	- Data access abstractions and implementations
- `src/main/java/com/bankofz/inqcust/api/domain`
	- API/domain records and enums
- `src/main/java/com/bankofz/inqcust/api/mapper`
	- Legacy-to-API mapping logic
- `src/main/java/com/bankofz/inqcust/api/support`
	- Supporting Spring configuration
- `src/main/resources`
	- Runtime properties and OpenAPI used by this service
- `src/test/java/com/bankofz/inqcust/api`
	- Unit and MVC tests

## Generated Artifacts

- `target/` is build output and should not be edited.

