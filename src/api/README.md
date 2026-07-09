# INQCUST API Module

This module contains the Spring Boot implementation for customer inquiry modernization.

## Source Of Truth

- Application config source: `src/main/resources/application.properties`
- Java source code: `src/main/java`
- Test source code: `src/test/java`
- Build output only (generated, not source): `target/`

## Directory Layout

- `src/main/java/com/bankofz/inqcust/api/controller`
	- REST endpoints and global exception handling.
- `src/main/java/com/bankofz/inqcust/api/service`
	- Lookup mode logic, risk rules, and orchestration.
- `src/main/java/com/bankofz/inqcust/api/repository`
	- Data access behind `CustomerRepository`.
	- Supports both mock-data mode and DB mode.
- `src/main/java/com/bankofz/inqcust/api/domain`
	- API/domain records and enums.
- `src/main/java/com/bankofz/inqcust/api/mapper`
	- Legacy-to-API mapping logic.
- `src/main/java/com/bankofz/inqcust/api/support`
	- Supporting configuration beans.
- `src/main/resources`
	- Runtime properties and OpenAPI file used by this service.
- `src/test/java/com/bankofz/inqcust/api`
	- Unit and MVC tests for controller/service/repository behavior.

## Modes: Mock And DB

Switching mode is configuration-only.

- Mock mode (default):
	- `app.data.mode=mock`
	- `app.mock-data.path=mock-data/customer-records.json`
- DB mode:
	- `app.data.mode=db`
	- set `app.db.url`, `app.db.username`, `app.db.password`, `app.db.table-name`

The service/controller functionality remains the same in both modes because data access is isolated behind `CustomerRepository`.

## Build And Test

- Run tests: `mvn test`
- Run app: `mvn spring-boot:run`

## Notes To Keep Structure Clean

- Do not edit files under `target/`; they are generated.
- If `target/` appears in Git changes, clean/untrack artifacts and keep `.gitignore` entries intact.

