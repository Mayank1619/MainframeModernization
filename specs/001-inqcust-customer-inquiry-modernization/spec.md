# Feature Specification: INQCUST Customer Inquiry Modernization

**Feature Branch**: `001-inqcust-customer-inquiry-modernization`  
**Created**: 2026-07-07  
**Status**: Draft  
**Input**: Legacy COBOL source `INQCUST.cbl`, copybooks `CUSTOMER.cpy`, `INQCUSTZ.cpy`, and DB2 declaration `CUSTDB2.cpy`.

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a consuming banking channel or customer service application, I need to retrieve customer inquiry information using sort code and customer number so that the customer data currently served by the COBOL `INQCUST` program can be accessed through a modern API.

### Acceptance Scenarios

#### Scenario 1: Specific customer found
Given a customer exists for sort code `123456` and customer number `0000000001`  
When the API receives `GET /api/v1/customers/123456/0000000001`  
Then the response status is HTTP 200  
And `legacyStatus.inquirySuccess` is `Y`  
And `legacyStatus.inquiryFailCode` is `0`  
And customer data is returned.

#### Scenario 2: Specific customer not found
Given no customer exists for sort code `123456` and customer number `0000009999`  
When the API receives `GET /api/v1/customers/123456/0000009999`  
Then the response status is HTTP 404  
And `legacyStatus.inquirySuccess` is `N`  
And `legacyStatus.inquiryFailCode` is `1`  
And `customer` is null.

#### Scenario 3: Latest customer lookup
Given customers exist for sort code `123456` with customer numbers `0000000001`, `0000000002`, and `0000000005`  
When the API receives `GET /api/v1/customers/123456/9999999999`  
Then the response status is HTTP 200  
And lookup mode is `LATEST`  
And customer `0000000005` is returned.

#### Scenario 4: Random customer lookup
Given a latest customer exists for sort code `123456`  
And deterministic random selection chooses an existing customer number  
When the API receives `GET /api/v1/customers/123456/0000000000`  
Then the response status is HTTP 200  
And lookup mode is `RANDOM`  
And `legacyStatus.inquirySuccess` is `Y`.

#### Scenario 5: Invalid request
Given the sort code is not six digits  
When the API receives the request  
Then the response status is HTTP 400  
And the response explains the validation error.

#### Scenario 6: Risk assessment enhancement
Given a customer has status `SUSPENDED` or credit score below 600  
When customer inquiry data is returned  
Then `riskAssessment.riskRating` is `HIGH`  
And risk reasons explain the rule that triggered the result.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system SHALL expose `GET /api/v1/customers/{sortCode}/{customerNumber}`.
- **FR-002**: The system SHALL validate `sortCode` as exactly six digits using `^[0-9]{6}$`.
- **FR-003**: The system SHALL validate `customerNumber` as exactly ten digits using `^[0-9]{10}$`.
- **FR-004**: The system SHALL perform a specific lookup when `customerNumber` is neither `0000000000` nor `9999999999`.
- **FR-005**: The system SHALL perform a random customer lookup when `customerNumber` is `0000000000`.
- **FR-006**: The system SHALL perform a latest customer lookup when `customerNumber` is `9999999999`.
- **FR-007**: The system SHALL return legacy inquiry status values in every successful or not-found customer inquiry response.
- **FR-008**: The system SHALL map customer fields according to the supporting mapping matrix.
- **FR-009**: The system SHALL convert legacy numeric dates in `YYYYMMDD` format into ISO `yyyy-MM-dd` dates in JSON responses.
- **FR-010**: The system SHALL trim fixed-width legacy CHAR values before returning JSON.
- **FR-011**: The system SHALL support valid customer statuses `ACTIVE`, `INACTIVE`, and `SUSPENDED`.
- **FR-012**: The system SHALL add non-legacy risk assessment using customer status, credit score, and credit score review date.
- **FR-013**: The system SHALL use mock data only for the POC.
- **FR-014**: The system SHALL isolate data access behind `CustomerRepository`.
- **FR-015**: The system SHALL not connect to real CICS, IMS, MQ, z/OS Connect, or DB2 during the POC.

### Business Rules

- **BR-001**: `0000000000` means random customer lookup.
- **BR-001a**: `0000000000` is a command value for random mode and is not looked up as a literal customer number.
- **BR-002**: `9999999999` means latest/highest customer lookup.
- **BR-003**: A found customer returns `inquirySuccess = Y` and `inquiryFailCode = 0`.
- **BR-004**: A specific customer not found returns `inquirySuccess = N` and `inquiryFailCode = 1`.
- **BR-005**: Latest customer not found returns `inquirySuccess = N` and `inquiryFailCode = 9`.
- **BR-006**: Random customer not found after retry limit returns `inquirySuccess = N` and `inquiryFailCode = 1`.
- **BR-007**: Random retry limit defaults to 1000 and must be configurable.
- **BR-008**: Risk rating is `HIGH` when status is `SUSPENDED` or credit score is below 600.
- **BR-009**: Risk rating is `MEDIUM` when score is between 600 and 699 inclusive and no HIGH rule applies.
- **BR-010**: Risk rating is `LOW` when status is `ACTIVE`, score is at least 700, and review date is not stale.
- **BR-011**: `reviewRequired` is true when credit score review date is older than 12 months from system date.

## Entities *(include if feature involves data)*

- **CustomerRecord**: Internal representation of the DB2 CUSTOMER row or mock equivalent.
- **CustomerResponse**: API representation of mapped customer data.
- **LegacyInquiryStatus**: API representation of `INQCUST-INQ-SUCCESS` and `INQCUST-INQ-FAIL-CD`.
- **RiskAssessmentResponse**: Modernization enhancement derived from existing legacy fields.
- **AddressResponse**: Nested API object for legacy address fields.

## Review & Acceptance Checklist

- [ ] All COBOL-visible lookup modes are represented.
- [ ] All copybook fields used by INQCUST are mapped.
- [ ] OpenAPI contract matches spec response shape.
- [ ] Negative scenarios are testable.
- [ ] Random behavior is deterministic in tests.
- [ ] No live mainframe integration is required.
- [ ] Implementation does not invent extra customer fields.

## Supporting References

See supporting documents in `supporting/` for mapping matrix, data dictionary, traceability, architecture notes, and original analysis.
