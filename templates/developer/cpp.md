{% extends "_base.md" %}

# C++ Developer

## Additional C++ Rules

- C++17 or later
- Use smart pointers (no raw new/delete)
- RAII for resource management
- Header guards or #pragma once
- Follow FRABA embedded coding standards

## For Embedded (NXP)

- Consider memory constraints
- No dynamic allocation in ISRs
- Use static buffers where possible
