# Encoder Domain - POSITAL/FRABA

## Overview

FRABA manufactures rotary encoders and inclinometers under the POSITAL brand.

## Product Types

### Absolute Encoders
- Know exact position at power-on
- Single-turn or multi-turn
- Interfaces: SSI, BiSS, CANopen, etc.

### Incremental Encoders
- Output pulses per revolution
- Require reference/homing
- A/B/Z signals

### Inclinometers
- Measure tilt angle
- Gravity-based sensing
- Single or dual axis

## Key Specifications

- **Resolution**: Bits or PPR (pulses per revolution)
- **Accuracy**: Angular error
- **Interface**: Communication protocol
- **Housing**: Mechanical form factor
- **Protection**: IP rating
- **Temperature**: Operating range

## Configuration Parameters

```yaml
encoder:
  type: absolute_multiturn
  resolution_singleturn: 16  # bits
  resolution_multiturn: 43   # bits
  interface: biss_c
  housing: 58mm_shaft
  protection: ip67
```

## Common Tasks

1. Configure encoder parameters
2. Generate product codes
3. Create technical documentation
4. Export to webshop
5. Integration with customer systems

*Note: FRABA-specific product codes and options to be added.*
