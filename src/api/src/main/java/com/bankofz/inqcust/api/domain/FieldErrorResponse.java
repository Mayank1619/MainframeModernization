package com.bankofz.inqcust.api.domain;

public record FieldErrorResponse(
        String field,
        String message
) {
}
