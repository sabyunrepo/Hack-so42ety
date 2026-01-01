# Apply @log_process Decorator Across Services

## Overview

Extend the usage of the existing @log_process decorator from TTSService to AuthService and StorybookService for consistent structured logging and performance tracing.

## Rationale

The @log_process decorator in core/utils/trace.py is already used in TTSService (generate_speech, create_voice_clone) to log step execution with timing and structured metadata. AuthService and StorybookService have similar critical operations (login, register, create_book) that would benefit from the same observability pattern.

---
*This spec was created from ideation and is pending detailed specification.*
