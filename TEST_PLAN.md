# Test Plan

## Overview
This document outlines the planned test cases for the `pgjinja` project, focusing on validating functionality, behavior, and error handling for key components.

### For `PgJinja` Class
- [ ] **Test Initialization**: Ensure `PgJinja` initializes with valid `DBSettings`.
- [ ] **Test Connection Pooling**: Validate connection pooling and lazy opening.
- [ ] **Test Query Execution**: Execute a query and validate result mapping to models.
- [ ] **Test Retry Logic**: Simulate a query failure and test retry logic.
- [ ] **Test Error Handling**: Trigger errors to ensure proper exceptions are raised.

### For `PgJinjaAsync` Class
- [ ] **Test Async Initialization**: Ensure `PgJinjaAsync` initializes asynchronously with valid `DBSettings`.
- [ ] **Test Async Query Execution**: Execute an async query and validate result mapping to models.
- [ ] **Test Async Retry Logic**: Simulate an async query failure and test retry logic.
- [ ] **Test Async Error Handling**: Trigger async errors to ensure proper exceptions are raised.

### For `DBSettings` Class
- [ ] **Test Configuration Validation**: Validate correct configuration of `DBSettings`.
- [ ] **Test Secure Password Handling**: Ensure password is securely handled.

### For Functions
- [ ] **Test Template Reading**: Validate correct caching and reading of SQL templates.
- [ ] **Test Model Field Extraction**: Ensure correct extraction of model fields.

