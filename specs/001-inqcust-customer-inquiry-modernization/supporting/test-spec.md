# test-spec.md - Test Specification

## Unit tests

### TC-001 Specific customer found
Given mock data contains sort code `123456` and customer number `0000000001`, when service inquiry is executed, then response has:
- lookupMode `SPECIFIC`
- inquirySuccess `Y`
- inquiryFailCode `0`
- customerNumber `0000000001`

### TC-002 Specific customer not found
Given no mock data exists for customer `0000009999`, when service inquiry is executed, then response has:
- lookupMode `SPECIFIC`
- inquirySuccess `N`
- inquiryFailCode `1`
- customer null

### TC-003 Latest customer found
Given customers `0000000001`, `0000000002`, and `0000000005` exist for sort code `123456`, when customer number `9999999999` is requested, then customer `0000000005` is returned.

### TC-004 Latest customer not found
Given no customers exist for sort code `999999`, when customer number `9999999999` is requested, then response has inquirySuccess `N` and fail code `9`.

### TC-005 Random customer found
Given `0000000000` triggers random command mode and random selector returns a customer number that exists, when customer number `0000000000` is requested, then the matching customer is returned with inquirySuccess `Y`.

### TC-006 Random customer retry failure
Given random selector never returns an existing customer within retry limit, when random lookup is requested, then response has inquirySuccess `N` and fail code `1`.

### TC-007 Date conversion success
Given legacy date integer `19750101`, when converted, then result is `1975-01-01`.

### TC-008 Date conversion failure
Given invalid legacy date integer `19751301`, when converted, then controlled exception is thrown.

### TC-009 LOW risk
Given customer status ACTIVE, credit score 742, and non-stale review date, then risk rating is LOW.

### TC-010 MEDIUM risk
Given customer status ACTIVE and credit score 650, then risk rating is MEDIUM.

### TC-011 HIGH risk by status
Given customer status SUSPENDED, then risk rating is HIGH.

### TC-012 HIGH risk by score
Given credit score 580, then risk rating is HIGH.

### TC-013 Review required
Given credit score review date older than 12 months, then reviewRequired is true and reasons includes `STALE_CREDIT_REVIEW`.

## Controller tests

### CT-001 Valid request returns HTTP 200
GET `/api/v1/customers/123456/0000000001` returns 200 and JSON body contains `legacyStatus.inquirySuccess = Y`.

### CT-002 Invalid sort code returns HTTP 400
GET `/api/v1/customers/ABCDEF/0000000001` returns 400.

### CT-003 Invalid customer number returns HTTP 400
GET `/api/v1/customers/123456/ABC` returns 400.

### CT-004 Not found returns HTTP 404
GET `/api/v1/customers/123456/0000009999` returns 404 and fail code `1`.

### CT-005 Latest request returns HTTP 200
GET `/api/v1/customers/123456/9999999999` returns latest customer.

### CT-006 Random request returns HTTP 200 or 404 based on deterministic selector setup
Test random behavior at service level to avoid flaky controller tests.

### CT-007 Suspended customer returns HIGH risk
GET `/api/v1/customers/123456/0000000003` returns 200 and `riskAssessment.riskRating = HIGH` with reason `STATUS_SUSPENDED`.

### CT-008 Low credit score returns HIGH risk
GET `/api/v1/customers/123456/0000000004` returns 200 and `riskAssessment.riskRating = HIGH` with reason `CREDIT_SCORE_LT_600`.
