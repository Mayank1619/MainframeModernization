# traceability-matrix.md

| Requirement / Rule | Source | Code artifact | Test case |
|---|---|---|---|
| Lookup by sort code + customer number | INQCUST.cbl SELECT WHERE CUSTOMER_SORTCODE and CUSTOMER_NUMBER | CustomerRepository.findBySortCodeAndCustomerNumber | TC-001, TC-002, CT-001, CT-004 |
| Random lookup `0000000000` | INQCUST.cbl random customer branch | CustomerInquiryService.randomLookup | TC-005, TC-006 |
| Latest lookup `9999999999` | INQCUST.cbl latest customer branch and GET-LAST-CUSTOMER-DB2 | CustomerRepository.findLatestBySortCode | TC-003, TC-004, CT-005 |
| Success flag Y and fail code 0 | INQCUST-INQ-SUCCESS / INQCUST-INQ-FAIL-CD | LegacyStatusFactory.success | TC-001 |
| Specific not found fail code 1 | SQLCODE 100 handling | LegacyStatusFactory.specificNotFound | TC-002, CT-004 |
| Random not found fail code 1 | SQLCODE 100 handling | LegacyStatusFactory.randomNotFound | TC-006 |
| Latest lookup fail code 9 | GET-LAST-CUSTOMER-DB2 SQLCODE 100 handling | LegacyStatusFactory.latestNotFound | TC-004 |
| Date conversion | COMPUTE date year/month/day from YYYYMMDD | LegacyDateConverter | TC-007, TC-008 |
| Status values ACTIVE/INACTIVE/SUSPENDED | CUSTOMER.cpy 88-levels | CustomerStatus enum | TC-009 through TC-012 |
| Credit score | CUSTOMER-CREDIT-SCORE / CUSTOMER_CREDIT_SCORE | CustomerRecord.creditScore | TC-009 through TC-012 |
| Credit score review date | CUSTOMER-CS-REVIEW-DATE / CUSTOMER_CS_REVIEW_DATE | RiskAssessmentService.reviewRequired | TC-013 |
| HIGH risk by status or score | BR-008 risk rule | RiskAssessmentService.assess | TC-011, TC-012, CT-007, CT-008 |
