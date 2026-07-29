Feature: Account Inquiry API

	Background:
		Given the API is running at localhost:8080

	@FR001 @BR001 @P1
	Scenario Outline: Account lookup key behaviors
		# Covers: <testId>
		When I request the account with sort code "<sortCode>" and account number "<accountNumber>"
		Then the account inquiry response status code is <statusCode>

		Examples:
			| testId       | sortCode | accountNumber | statusCode |
			| TC-ACC01-027 | 123456   | 00000001      | 200        |
			| TC-ACC01-028 | 123456   | 00000999      | 404        |

	@BR002 @P1
	Scenario Outline: Sortcode length boundaries
		# Covers: <testId>
		When I request the account with sort code "<sortCode>" and account number "00000001"
		Then the account inquiry response status code is <statusCode>

		Examples:
			| testId       | sortCode | statusCode |
			| TC-ACC01-001 | 000000   | 200        |
			| TC-ACC01-002 | 999999   | 200        |
			| TC-ACC01-003 | 12345    | 400        |
			| TC-ACC01-004 | 1234567  | 400        |
			| TC-ACC01-005 |          | 400        |

	@BR003 @P1
	Scenario Outline: Account number length boundaries
		# Covers: <testId>
		When I request the account with sort code "123456" and account number "<accountNumber>"
		Then the account inquiry response status code is <statusCode>

		Examples:
			| testId       | accountNumber | statusCode |
			| TC-ACC01-006 | 00000000      | 200        |
			| TC-ACC01-007 | 99999999      | 200        |
			| TC-ACC01-008 | 0000001       | 400        |
			| TC-ACC01-009 | 000000001     | 400        |
			| TC-ACC01-010 |               | 400        |

	@FR001A @P1
	Scenario Outline: Reserved account number branch behavior
		# Covers: <testId>
		When I request the account with sort code "<sortCode>" and account number "<accountNumber>"
		Then the account inquiry response status code is <statusCode>

		Examples:
			| testId       | sortCode | accountNumber | statusCode |
			| TC-ACC01-011 | 123456   | 99999999      | 200        |
			| TC-ACC01-012 | 555555   | 99999998      | 200        |

	@BR002 @P2 @DBAgnostic
	Scenario Outline: Sortcode character validation
		# Covers: <testId>
		When I request the account with sort code "<sortCode>" and account number "00000001"
		Then the account inquiry response status code is <statusCode>

		Examples:
			| testId       | sortCode | statusCode |
			| TC-ACC01-013 | 123456   | 200        |
			| TC-ACC01-014 | 12AB56   | 400        |
			| TC-ACC01-015 | 12@#56   | 400        |
			| TC-ACC01-016 | 12AB34   | 400        |
			| TC-ACC01-017 | 12 456   | 400        |

	@BR003 @P2 @DBAgnostic
	Scenario Outline: Account number character validation
		# Covers: <testId>
		When I request the account with sort code "123456" and account number "<accountNumber>"
		Then the account inquiry response status code is <statusCode>

		Examples:
			| testId       | accountNumber | statusCode |
			| TC-ACC01-018 | 00000001      | 200        |
			| TC-ACC01-019 | 00AB0001      | 400        |
			| TC-ACC01-020 | 00@#0001      | 400        |
			| TC-ACC01-021 | 0 0000001     | 400        |
			| TC-ACC01-021 | +00000001     | 400        |
			| TC-ACC01-021 | %2000000001     | 400        |

	@BR004 @FR006 @P1 @DBAgnostic
	Scenario Outline: Authentication and authorization partitions
		# Covers: <testId>
		When I request the account with sort code "123456" and account number "00000001" using auth mode "<authMode>"
		Then the account inquiry response status code is <statusCode>

		Examples:
			| testId       | authMode      | statusCode |
			| TC-ACC01-022 | valid         | 200        |
			| TC-ACC01-023 | missing       | 401        |
			| TC-ACC01-024 | malformed     | 401        |

	@TCACC01025 @BR004 @FR006 @P3 @Blocked
	Scenario: Expired bearer token
		Given blocked precondition "expired token fixture is unavailable"
		When I request the account with sort code "123456" and account number "00000001" using auth mode "expired"
		Then the account inquiry response status code is 401

	@TCACC01026 @BR004 @FR006 @P3 @Blocked
	Scenario: Insufficient permissions token
		Given blocked precondition "insufficient-permission token fixture is unavailable"
		When I request the account with sort code "123456" and account number "00000001" using auth mode "forbidden"
		Then the account inquiry response status code is 403

	@FR004 @P1
	Scenario: Response contains required mapped account fields
		# Covers: TC-ACC01-029
		When I request the account with sort code "123456" and account number "00000001"
		Then the account inquiry response status code is 200
		And the account response contains all required account fields

	@FR004 @P1
	Scenario: Date fields are formatted as ISO yyyy-MM-dd
		# Covers: TC-ACC01-030
		When I request the account with sort code "123456" and account number "00000001"
		Then the account inquiry response status code is 200
		And the account date fields are ISO formatted

	@FR004 @P2
	Scenario: Numeric fields preserve numeric formatting
		# Covers: TC-ACC01-031
		When I request the account with sort code "123456" and account number "00000001"
		Then the account inquiry response status code is 200
		And the account numeric fields are numeric

	@FR004 @P2
	Scenario: String fields are trimmed
		# Covers: TC-ACC01-032
		When I request the account with sort code "123456" and account number "00000001"
		Then the account inquiry response status code is 200
		And the account string fields are trimmed

	@FR005 @BR005 @P1
	Scenario: 400 malformed input has standardized error payload
		# Covers: TC-ACC01-033
		When I request the account with sort code "12AB56" and account number "00000001"
		Then the account inquiry response status code is 400
		And the error response has standardized fields

	@BR004 @P1
	Scenario: 401 authentication failure has proper error payload
		# Covers: TC-ACC01-034
		When I request the account with sort code "123456" and account number "00000001" without authorization
		Then the account inquiry response status code is 401
		And the error response has standardized fields

	@BR004 @P1 @Blocked
	Scenario: 403 authorization failure has proper error payload
		# Covers: TC-ACC01-035
		Given blocked precondition "forbidden token fixture is unavailable"
		When I request the account with sort code "123456" and account number "00000001" using auth mode "forbidden"
		Then the account inquiry response status code is 403
		And the error response has standardized fields

	@BR005 @P1
	Scenario: 404 not found has proper error payload
		# Covers: TC-ACC01-036
		When I request the account with sort code "123456" and account number "00000999"
		Then the account inquiry response status code is 404
		And the error response has standardized fields

	@BR005 @P2 @Conditional
	Scenario: 500 internal server error has proper error payload
		# Covers: TC-ACC01-037
		Given optional precondition "enable.account.500.tests" is enabled
		When I request the account with sort code "500000" and account number "50000000"
		Then the account inquiry response status code is 500
		And the error response has standardized fields

	@BR005 @P2 @Conditional
	Scenario: 503 service unavailable has proper error payload
		# Covers: TC-ACC01-038
		Given optional precondition "enable.account.503.tests" is enabled
		When I request the account with sort code "503000" and account number "50300000"
		Then the account inquiry response status code is 503
		And the error response has standardized fields

	@FR007 @P2 @Conditional
	Scenario: Successful lookup creates traceable safe logs
		# Covers: TC-ACC01-039
		Given optional precondition "enable.account.log.tests" is enabled
		When I request the account with sort code "123456" and account number "00000001"
		Then the account inquiry response status code is 200

	@FR007 @P2 @Conditional
	Scenario: Failed lookup creates traceable safe logs
		# Covers: TC-ACC01-040
		Given optional precondition "enable.account.log.tests" is enabled
		When I request the account with sort code "123456" and account number "00000999"
		Then the account inquiry response status code is 404

	@FR005 @P1
	Scenario: Error response contains code message timestamp and correlationId
		# Covers: TC-ACC01-041
		When I request the account with sort code "12345" and account number "00000001"
		Then the account inquiry response status code is 400
		And the error response has standardized fields

	@FR005 @P2
	Scenario: Correlation ID is echoed when provided
		# Covers: TC-ACC01-042
		When I request the account with sort code "123456" and account number "00000001" with correlation id "2f2b8b1d-6854-4b5d-8bd1-730f8d4b98e0"
		Then the account inquiry response status code is one of "200,404"
		And the correlation id is echoed in response

	@FR005 @P2
	Scenario: Correlation ID is generated when not provided
		# Covers: TC-ACC01-043
		When I request the account with sort code "123456" and account number "00000001"
		Then the account inquiry response status code is one of "200,404"
		And the response contains a generated correlation id